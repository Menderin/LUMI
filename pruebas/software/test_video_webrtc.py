"""Integracion opcional: instalar requirements-webrtc.txt para ejecutar estos casos."""
import asyncio
import threading
import time
import unittest
import numpy as np
try:
    from aiortc import RTCPeerConnection, RTCConfiguration, RTCSessionDescription
    from software.percepcion.video_webrtc import WebRTCService, LatestVideo, LatestTrack
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, "Dependencias WebRTC opcionales no instaladas")
class WebRTCTests(unittest.IsolatedAsyncioTestCase):
    async def test_solo_ultimo_cuadro_y_no_repite_uno_antiguo(self):
        source = LatestVideo()
        for value in (10, 80, 170):
            source.publish(np.full((64,96,3),value,np.uint8),[],None,None)
        track = LatestTrack(source)
        frame = await track.recv()
        self.assertEqual(int(frame.to_ndarray(format="bgr24").mean()),170)
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(track.recv(),.15)
        source.publish(np.full((64,96,3),200,np.uint8),[],None,None)
        self.assertEqual(int((await track.recv()).to_ndarray(format="bgr24").mean()),200)
        track.stop()

    async def test_video_vp8_real_puertos_y_cierre(self):
        service = WebRTCService()
        stop = threading.Event()
        def produce():
            while not stop.is_set():
                service.publish(np.full((480,640,3),100,np.uint8),[(30,30,90,200)],None,0)
                stop.wait(.1)
        producer = threading.Thread(target=produce)
        producer.start()
        peer = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        received = asyncio.get_running_loop().create_future()
        tasks = []
        @peer.on("track")
        def track_received(track):
            async def receive():
                frames = [await track.recv() for _ in range(3)]
                received.set_result(frames)
            tasks.append(asyncio.create_task(receive()))
        try:
            with self.assertRaisesRegex(ValueError,"oferta|Oferta"):
                await asyncio.to_thread(service.offer,{"type":"offer","sdp":"invalid"})
            peer.addTransceiver("video",direction="recvonly")
            await peer.setLocalDescription(await peer.createOffer())
            answer = await asyncio.to_thread(service.offer,{"type":"offer","sdp":peer.localDescription.sdp})
            self.assertTrue(answer["puertos"])
            self.assertTrue(all(50000 <= x["puerto"] <= 50009 for x in answer["puertos"]))
            self.assertEqual(answer["codec"],"VP8")
            await peer.setRemoteDescription(RTCSessionDescription(sdp=answer["sdp"],type="answer"))
            frames = await asyncio.wait_for(received,15)
            self.assertTrue(all((x.width,x.height)==(640,480) for x in frames))
            self.assertLess(frames[0].pts,frames[-1].pts)
            self.assertEqual(service.status()["clientes"][0]["estado"],"connected")
            await asyncio.to_thread(service.close_peer,answer["sesion"])
            self.assertEqual(service.status()["clientes"],[])
        finally:
            await peer.close()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
            stop.set();producer.join(timeout=2)
            await asyncio.to_thread(service.close)
            self.assertFalse(service.thread.is_alive())

if __name__ == "__main__":
    unittest.main()
