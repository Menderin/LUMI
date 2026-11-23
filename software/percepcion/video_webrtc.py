"""Video WebRTC local compartiendo el capturador de LUMI. VP8, sin audio/STUN externo."""
import asyncio
import concurrent.futures
import errno
import fractions
import logging
import threading
import time
import uuid

import cv2
from aiortc import (MediaStreamTrack, RTCConfiguration, RTCBundlePolicy,
                    RTCPeerConnection, RTCRtpSender, RTCSessionDescription)
from aiortc.mediastreams import MediaStreamError
from av import VideoFrame

LOG = logging.getLogger(__name__)
UDP_MIN, UDP_MAX = 50000, 50009


class BoundedMediaLoop(asyncio.SelectorEventLoop):
    """Limita binds UDP efimeros de este loop dedicado, usando la API publica asyncio.

    No modifica aioice, el loop global ni puertos de otros procesos. Permite reglas
    firewall precisas para el banco en vez de abrir todos los puertos UDP.
    """
    async def create_datagram_endpoint(self, protocol_factory, *args, **kwargs):
        addr = kwargs.get("local_addr")
        if addr and addr[1] == 0:
            for port in range(UDP_MIN, UDP_MAX + 1):
                try:
                    return await super().create_datagram_endpoint(
                        protocol_factory, *args, **{**kwargs, "local_addr": (addr[0], port)})
                except OSError as error:
                    if error.errno != errno.EADDRINUSE and getattr(error,"winerror",0) != 10048:
                        raise
            raise OSError(errno.EADDRINUSE, "Sin puerto disponible para WebRTC 50000-50009")
        return await super().create_datagram_endpoint(protocol_factory, *args, **kwargs)


class LatestVideo:
    def __init__(self):
        self.lock = threading.Lock()
        self.value = None
        self.sequence = 0

    def publish(self, frame, cajas, seleccionado, objetivo):
        # El video lleva recuadros incrustados; la seleccion usa OTRO snapshot atomico.
        image = frame.copy()
        for i, (x,y,r,b) in enumerate(cajas):
            color = (0,230,0) if i == objetivo else (255,220,80) if i == seleccionado else (0,190,255)
            cv2.rectangle(image,(x,y),(r-1,b-1),color,2)
            cv2.putText(image,f"Persona {i+1}",(x,max(18,y-5)),cv2.FONT_HERSHEY_SIMPLEX,.5,color,1)
        with self.lock:
            self.sequence += 1
            self.value = (self.sequence,time.monotonic(),image)

    def latest(self):
        with self.lock:
            return self.value


class LatestTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, source):
        super().__init__()
        self.source = source
        self.last = 0
        self.origin = time.monotonic()
        self.last_sent = 0

    async def recv(self):
        while self.readyState == "live":
            sample = self.source.latest()
            now = time.monotonic()
            if sample and now - sample[1] < 2 and sample[0] != self.last:
                await asyncio.sleep(max(0,.1-(now-self.last_sent)))
                # Volver a consultar tras esperar: no codificar el cuadro antiguo.
                sample = self.source.latest()
                self.last = sample[0]
                self.last_sent = time.monotonic()
                frame = VideoFrame.from_ndarray(sample[2],format="bgr24")
                frame.pts = max(1,round((self.last_sent-self.origin)*90000))
                frame.time_base = fractions.Fraction(1,90000)
                return frame
            if sample and now-sample[1] >= 3:
                raise MediaStreamError
            await asyncio.sleep(.01)
        raise MediaStreamError


def candidate_ports(sdp):
    ports = []
    for line in sdp.splitlines():
        if line.startswith("a=candidate:"):
            fields = line.split()
            if len(fields) >= 6 and fields[2].lower() == "udp":
                pair = {"ip":fields[4],"puerto":int(fields[5])}
                if pair not in ports:
                    ports.append(pair)
    return ports


class WebRTCService:
    def __init__(self):
        self.source = LatestVideo()
        self.loop = BoundedMediaLoop()
        self.peers = {}
        self.offer_lock = None
        self.info_lock = threading.Lock()
        self.info = {"habilitado":True,"codec":"VP8","clientes":[],"puertos_udp":[UDP_MIN,UDP_MAX]}
        self.thread = threading.Thread(target=self._run,name="lumi-webrtc",daemon=True)
        self.thread.start()

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def publish(self,*args):
        self.source.publish(*args)

    def status(self):
        with self.info_lock:
            return {**self.info,"clientes":[dict(x) for x in self.info["clientes"]]}

    def _refresh(self):
        with self.info_lock:
            self.info["clientes"] = [{"sesion":sid,"estado":peer.connectionState,
                "ice":peer.iceConnectionState,"candidatos":candidate_ports(peer.localDescription.sdp)
                if peer.localDescription else []} for sid,peer in self.peers.items()]

    async def _offer(self,data):
        if self.offer_lock is None:
            self.offer_lock = asyncio.Lock()
        async with self.offer_lock:
            return await self._create_answer(data)

    async def _create_answer(self,data):
        sample = self.source.latest()
        if sample is None or time.monotonic()-sample[1] > 2:
            raise ValueError("Camara aun no disponible para WebRTC")
        if data.get("type") != "offer" or not isinstance(data.get("sdp"),str) or len(data["sdp"]) > 120000:
            raise ValueError("Oferta SDP invalida")
        if not data["sdp"].startswith("v=0") or "m=video " not in data["sdp"]:
            raise ValueError("La oferta debe contener video WebRTC")
        # Un movil de laboratorio a la vez: evitar encoders y sesiones abandonadas.
        for sid in list(self.peers):
            await self._close(sid)
        peer = RTCPeerConnection(RTCConfiguration(iceServers=[],bundlePolicy=RTCBundlePolicy.MAX_BUNDLE))
        sid = uuid.uuid4().hex
        self.peers[sid] = peer
        track = LatestTrack(self.source)

        @peer.on("connectionstatechange")
        async def state_changed():
            self._refresh()
            if peer.connectionState in ("failed","closed") and self.peers.get(sid) is peer:
                await self._close(sid)

        try:
            await peer.setRemoteDescription(RTCSessionDescription(sdp=data["sdp"],type="offer"))
            peer.addTrack(track)
            codecs = [x for x in RTCRtpSender.getCapabilities("video").codecs if x.mimeType.lower()=="video/vp8"]
            for transceiver in peer.getTransceivers():
                if transceiver.kind == "video":
                    transceiver.setCodecPreferences(codecs)
            await peer.setLocalDescription(await peer.createAnswer())
            self._refresh()
            LOG.info("WebRTC %s candidatos UDP: %s",sid,candidate_ports(peer.localDescription.sdp))
            return {"sdp":peer.localDescription.sdp,"type":"answer","sesion":sid,
                    "codec":"VP8","puertos":candidate_ports(peer.localDescription.sdp)}
        except BaseException:
            track.stop()
            await self._close(sid)
            raise

    async def _close(self,sid):
        peer = self.peers.pop(sid,None)
        if peer:
            await peer.close()
        self._refresh()

    def offer(self,data):
        future = asyncio.run_coroutine_threadsafe(self._offer(data),self.loop)
        try:
            return future.result(timeout=12)
        except concurrent.futures.TimeoutError as error:
            future.cancel()
            raise RuntimeError("Tiempo agotado al negociar WebRTC") from error

    def close_peer(self,sid):
        if not isinstance(sid,str) or len(sid)>64:
            raise ValueError("Sesion WebRTC invalida")
        asyncio.run_coroutine_threadsafe(self._close(sid),self.loop).result(timeout=5)

    def close(self):
        async def all_closed():
            for sid in list(self.peers):
                await self._close(sid)
        try:
            asyncio.run_coroutine_threadsafe(all_closed(),self.loop).result(timeout=8)
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(timeout=5)
            if not self.thread.is_alive():
                self.loop.close()
