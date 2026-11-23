"""Banco de vision NUC para Android. No importa ni transmite control de motores."""
import argparse
import base64
import json
import math
import queue
import socket
import threading
import time
import uuid
from collections import deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

from .enrolamiento.sesion import SesionEnrolamiento
from .enrolamiento.video import extraer
from .experimentos import recortar, guardar_representacion
from .practica import (REPO, Video, abrir_camara, detectar, foto_parametros, guardar_json,
                      modelos_en_vivo, resolver, cargar_parametros, commit_local)
from .seleccion_persona import SeleccionPersona

CONTRATO = "lumi-vision-nuc-v1"


def jpeg(imagen):
    ok, codificado = cv2.imencode(".jpg", imagen, [cv2.IMWRITE_JPEG_QUALITY, 75])
    if not ok:
        raise RuntimeError("No se pudo codificar imagen")
    return base64.b64encode(codificado).decode("ascii")


class BancoVision:
    def __init__(self, args, carpeta):
        self.args, self.carpeta = args, Path(carpeta)
        self.sesion = SesionEnrolamiento(desde_video=True, recuperacion_simulada=True)
        self.sesion.mensaje = "Pulsa Enrolar para seleccionar una persona"
        self.seleccion = SeleccionPersona()
        self.seleccionando = False
        self.indice = None
        self.identificador = None
        self.video = None
        self.ruta_video = None
        self.registros = []
        self.extraccion = {}
        self.revision = None
        self.ultimo = None
        self.historial = deque(maxlen=25)
        self.secuencia = 0
        self.prefijo = uuid.uuid4().hex
        self.snapshot = None
        self.lock = threading.Lock()
        self.cola = queue.Queue(maxsize=8)
        self.stop = threading.Event()
        self.error = None
        self.latencia_ms = 0
        self.fps = 0
        self.tempos = deque(maxlen=30)
        self.eventos = []
        self.objetivo_valido = False
        self.ultimo_frame_t = 0
        self.webrtc = None

    def estado(self, ahora=None):
        ahora = time.monotonic() if ahora is None else ahora
        e = self.sesion.estado(ahora)
        fase = e["estado"]
        if fase in ("espera","fallo") and self.seleccionando:
            fase = "seleccionado" if self.seleccion.caja is not None else "seleccionando"
        return {**e, "estado":fase,"servidor":CONTRATO,"movimiento_habilitado":False,
                "metodo":self.args.metodo,"umbral":self.args.umbral,"margen":self.args.margen,
                "fps":round(self.fps,1),"procesamiento_ms":round(self.latencia_ms,1),
                "error":self.error,"mensaje":self.error or e["mensaje"],
                "revision_disponible":self.revision is not None,
                "camara_activa":self.ultimo is not None and ahora-self.ultimo_frame_t < 2,
                "webrtc":self.webrtc is not None}

    def _limpiar(self):
        if self.video:
            self.video.cerrar()
            guardar_json(self.ruta_video.with_suffix(".captura.json"),self.registros)
            self.video = None
        self.seleccion.limpiar()
        self.indice = None
        self.identificador = None
        self.objetivo_valido = False
        self.revision = None

    def accion(self, datos, ahora):
        accion = datos.get("accion")
        r = self.sesion.registro
        if accion == "seleccionar":
            if not self.seleccionando or r.estado not in ("espera","fallo"):
                raise ValueError("Pulsa Enrolar antes de seleccionar; no cambiar durante captura")
            ficha = next((x for x in self.historial if x["frame_id"] == datos.get("frame_id")),None)
            indice = datos.get("candidato")
            if ficha is None or ahora-ficha["tiempo"] > 1.5:
                raise ValueError("Imagen antigua; toca de nuevo sobre el video actualizado")
            if type(indice) is not int or not 0 <= indice < len(ficha["cajas"]):
                raise ValueError("Candidato invalido")
            self.seleccion.caja = tuple(ficha["cajas"][indice])
            self.indice, mensaje = self.seleccion.actualizar(self.ultimo[1])
            self.sesion.mensaje = mensaje
            if self.indice is None:
                raise ValueError(mensaje)
        elif accion in ("iniciar","repetir"):
            if accion == "iniciar" and r.estado not in ("espera","fallo"):
                raise ValueError("Cancela o inicia un nuevo enrolamiento")
            if r.intentos >= 5:
                raise ValueError("Limite de cinco intentos; reinicia el servidor para otra sesion")
            self._limpiar()
            self.sesion.accion("cancelar",ahora)
            self.seleccionando = True
            self.sesion.mensaje = "Toca el recuadro de la persona que quieres enrolar"
        elif accion == "capturar":
            if not self.seleccionando or self.seleccion.caja is None or self.ultimo is None:
                raise ValueError("Selecciona primero a una persona")
            self.indice,mensaje = self.seleccion.actualizar(self.ultimo[1])
            if self.indice is None:
                raise ValueError(mensaje)
            if not self.sesion.accion("iniciar",ahora,personas=1):
                raise ValueError(self.sesion.mensaje)
            self.seleccionando = False
        elif accion == "cancelar":
            self._limpiar()
            self.seleccionando = False
            self.sesion.accion("cancelar",ahora)
            self.sesion.mensaje = "Enrolamiento cancelado. Pulsa Enrolar para comenzar"
        elif accion == "confirmar":
            if r.estado != "revision":
                raise ValueError("No hay recortes pendientes de revision")
            modelos = modelos_en_vivo(r.muestras,self.args)
            destino = self.carpeta/f"galeria-{r.intentos}"
            destino.mkdir()
            for i, muestra in enumerate(r.muestras,1):
                if not cv2.imwrite(str(destino/f"{i:02}.png"),muestra):
                    raise RuntimeError("No se pudo guardar galeria")
            for nombre, modelo in modelos.items():
                guardar_representacion(modelo,destino/f"{nombre}.npz")
            guardar_json(destino/"galeria.json",{
                "aprobada":True,"sesion":self.carpeta.name,"intento":r.intentos,
                "imagenes":[f"{i:02}.png" for i in range(1,len(r.muestras)+1)],
                "metodos":list(modelos),"duracion_captura_s":12,
                "origen_recortes":self.extraccion.get("seleccion",[]),
                "seleccion":"toque Android + asociacion IoU + revision humana",
                "representaciones":{n:getattr(m,"metadata",{}) for n,m in modelos.items()}})
            self.sesion.accion("confirmar",ahora)
            self.sesion.mensaje = "Galeria aprobada. Pulsa Iniciar seguimiento visual cuando estes listo"
            self.identificador = modelos[self.args.metodo]
            self.seleccion.limpiar()
            self.indice = None
            self.objetivo_valido = False
        elif accion in ("iniciar_seguimiento","reanudar"):
            if not self.sesion.accion(accion,ahora,objetivo=self.objetivo_valido):
                raise ValueError(self.sesion.mensaje)
        else:
            raise ValueError("Accion no admitida; movimiento restringido")
        self.eventos.append({"tiempo":ahora,"accion":accion,"estado":r.estado})
        guardar_json(self.carpeta/"acciones-movil.json",self.eventos)

    def procesar(self, frame, cajas, ahora):
        self.ultimo = (frame,cajas)
        self.ultimo_frame_t = ahora
        # Solo el hilo de vision cambia el estado. Las peticiones caducadas no se ejecutan.
        while True:
            try:
                solicitud = self.cola.get_nowait()
            except queue.Empty:
                break
            datos,limite,evento,respuesta = solicitud
            try:
                if ahora > limite:
                    raise ValueError("Solicitud caducada; vuelve a intentar")
                self.accion(datos,ahora)
                respuesta.update(ok=True)
            except (ValueError,RuntimeError,OSError) as error:
                respuesta.update(ok=False,error=str(error))
                self.sesion.mensaje = str(error)
            finally:
                evento.set()
        r = self.sesion.registro
        if self.seleccion.caja is not None and r.estado in ("espera","fallo","preparando","enrolando"):
            self.indice,mensaje = self.seleccion.actualizar(cajas)
            if self.indice is None:
                if r.estado in ("preparando","enrolando"):
                    self.sesion.fallar(mensaje)
                    self._limpiar()
                self.sesion.mensaje = mensaje
                self.seleccionando = True
        distancias = []
        candidato = None
        motivo = "sin_galeria"
        if self.identificador is not None:
            distancias = [self.identificador.distancia(recortar(frame,caja)) for caja in cajas]
            candidato,motivo = resolver(distancias,self.args.umbral,self.args.margen)
        self.objetivo_valido = candidato is not None
        siguiendo = self.sesion.actualizar(ahora,personas=1 if self.indice is not None else 0,
                                          objetivo=self.objetivo_valido)
        if r.estado == "enrolando":
            if self.video is None:
                self.ruta_video = self.carpeta/f"enrolamiento-{r.intentos}.avi"
                self.video = Video(self.ruta_video,self.args.fps_proceso,frame)
                self.registros = []
            self.video.escribir(frame)
            # La extraccion solo recibe el recuadro seleccionado; el video conserva la escena.
            self.registros.append({"frame":len(self.registros),"tiempo_s":ahora,
                "cajas":[cajas[self.indice]] if self.indice is not None else [],
                "cajas_escena":cajas,"indice_seleccionado":self.indice,
                "ancho":frame.shape[1],"alto":frame.shape[0]})
        elif self.video is not None:
            self.video.cerrar()
            self.video = None
            guardar_json(self.ruta_video.with_suffix(".captura.json"),self.registros)
            if r.estado == "procesando":
                muestras,self.extraccion = extraer(self.ruta_video,self.registros)
                self.sesion.completar_video(muestras)
                guardar_json(self.ruta_video.with_suffix(".extraccion.json"),self.extraccion)
                if r.estado == "revision":
                    hoja = np.zeros((448,384,3),np.uint8)
                    for i,m in enumerate(r.muestras):
                        y,x = divmod(i,6)
                        hoja[y*112:(y+1)*112,x*64:(x+1)*64] = cv2.resize(m,(64,112))
                        cv2.rectangle(hoja,(x*64,y*112),((x+1)*64-1,(y+1)*112-1),(210,210,210),1)
                        cv2.rectangle(hoja,(x*64+1,y*112+1),(x*64+20,y*112+15),(0,0,0),-1)
                        cv2.putText(hoja,str(i+1),(x*64+3,y*112+12),cv2.FONT_HERSHEY_SIMPLEX,.32,(255,255,255),1)
                    self.revision = {"jpeg":jpeg(hoja),"ancho":384,"alto":448,"recortes":len(r.muestras)}
        self.secuencia += 1
        frame_id = f"{self.prefijo}:{self.secuencia}"
        self.historial.append({"frame_id":frame_id,"tiempo":ahora,"cajas":list(cajas)})
        seleccionado = self.indice if self.seleccion.caja is not None else None
        self.snapshot = {"frame_id":frame_id,"jpeg":jpeg(frame),"ancho":frame.shape[1],
            "alto":frame.shape[0],"cajas":cajas,"seleccionado":seleccionado,
            "objetivo":candidato if siguiendo else None,"distancias":distancias,"motivo":motivo,
            "estado":self.estado(ahora)}
        if self.webrtc is not None:
            self.webrtc.publish(frame,cajas,seleccionado,candidato if siguiendo else None)
        return self.snapshot

    def ejecutar(self):
        captura = None
        log = None
        try:
            from .detector_openvino import DetectorOpenVINO, descargar
            ruta = REPO/"modelos/pesos/person-detection-0202/person-detection-0202.xml"
            if self.args.descargar_modelo:
                descargar(ruta.parent)
            detector = DetectorOpenVINO(ruta,self.args.confianza,self.args.hilos)
            captura = abrir_camara(self.args)
            guardar_json(self.carpeta/"configuracion.json",{**vars(self.args),"captura":foto_parametros(captura),
                "runtime":detector.metadata,"commit":commit_local(),"movimiento_habilitado":False})
            log = (self.carpeta/"decisiones-movil.jsonl").open("w",encoding="utf-8")
            while not self.stop.is_set():
                inicio = time.monotonic()
                ok,frame = captura.read()
                if not ok:
                    raise RuntimeError("La camara dejo de entregar imagenes")
                cajas = detectar(frame,detector)
                with self.lock:
                    snap = self.procesar(frame,cajas,time.monotonic())
                    log.write(json.dumps({k:v for k,v in snap.items() if k!="jpeg"})+"\n")
                    log.flush()
                    self.latencia_ms = (time.monotonic()-inicio)*1000
                self.stop.wait(max(0,1/self.args.fps_proceso-(time.monotonic()-inicio)))
                self.tempos.append(time.monotonic()-inicio)
                self.fps = len(self.tempos)/sum(self.tempos)
        except Exception as error:
            with self.lock:
                self.error = str(error)
                guardar_json(self.carpeta/"error.json",{"error":str(error)})
        finally:
            if captura is not None:
                captura.release()
            if log:
                log.close()
            self._limpiar()
            guardar_json(self.carpeta/"acciones.json",self.sesion.eventos)


def manejador(banco):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def setup(self):
            super().setup()
            self.connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
            self.connection.settimeout(10)

        def log_message(self, formato, *args):
            pass

        def responder(self,codigo,datos):
            self.enviar(codigo,json.dumps(datos).encode(),"application/json; charset=utf-8")

        def enviar(self,codigo,contenido,tipo,metadata=None):
            self.send_response(codigo)
            self.send_header("Content-Type",tipo)
            if metadata is not None:
                self.send_header("X-Lumi-Metadata",json.dumps(metadata,ensure_ascii=True,separators=(",",":")))
            self.send_header("Content-Length",str(len(contenido)))
            self.send_header("Cache-Control","no-store")
            self.end_headers()
            try:
                self.wfile.write(contenido)
            except (BrokenPipeError,ConnectionResetError):
                pass

        def do_GET(self):
            with banco.lock:
                if self.path == "/api/webrtc/estado":
                    datos = banco.webrtc.status() if banco.webrtc else {"habilitado":False}
                elif self.path == "/api/estado":
                    datos = banco.estado()
                elif self.path in ("/api/vision/frame","/api/vision/frame.jpg"):
                    datos = banco.snapshot if banco.estado()["camara_activa"] else None
                    if datos:
                        datos = {**datos,"estado":banco.estado()}
                elif self.path == "/api/vision/revision":
                    datos = banco.revision
                else:
                    return self.responder(404,{"error":"Ruta no disponible"})
            if self.path == "/api/vision/frame.jpg" and datos:
                metadata={k:v for k,v in datos.items() if k!="jpeg"}
                self.enviar(200,base64.b64decode(datos["jpeg"]),"image/jpeg",metadata)
            else:
                self.responder(200 if datos else 503,datos or {"error":banco.error or "Preparando camara o revision"})

        def do_POST(self):
            if self.path not in ("/api/enrolamiento","/api/vision/seleccionar","/api/webrtc/offer","/api/webrtc/cerrar"):
                self.close_connection = True
                return self.responder(403,{"error":"Movimiento restringido; este servidor es solo de vision"})
            try:
                longitud = int(self.headers.get("Content-Length","0"))
                limite = 131072 if self.path=="/api/webrtc/offer" else 4096
                if not 0 < longitud <= limite:
                    raise ValueError("Solicitud invalida")
                datos = json.loads(self.rfile.read(longitud))
                if not isinstance(datos,dict):
                    raise ValueError("Se requiere objeto JSON")
                if self.path.startswith("/api/webrtc/"):
                    if banco.webrtc is None:
                        return self.responder(503,{"error":"Reinicia servidor con --webrtc e instala requirements-webrtc.txt"})
                    if self.path.endswith("offer"):
                        return self.responder(200,banco.webrtc.offer(datos))
                    banco.webrtc.close_peer(datos.get("sesion",""))
                    return self.responder(200,{"ok":True})
                if self.path.endswith("seleccionar"):
                    datos["accion"] = "seleccionar"
                evento,respuesta = threading.Event(),{}
                banco.cola.put_nowait((datos,time.monotonic()+1.5,evento,respuesta))
                if not evento.wait(4):
                    return self.responder(503,{"error":"Vision ocupada; revisa estado antes de reintentar"})
                self.responder(200 if respuesta["ok"] else 409,respuesta)
            except (ValueError,RuntimeError,queue.Full) as error:
                self.close_connection = True
                self.responder(400,{"error":str(error)})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host",default="0.0.0.0")
    parser.add_argument("--puerto",type=int,default=8080)
    parser.add_argument("--camara",type=int,default=0)
    parser.add_argument("--metodo",choices=("histograma","cnn_reid"),default="histograma")
    parser.add_argument("--parametros",help="umbrales.json o auto")
    parser.add_argument("--umbral",type=float)
    parser.add_argument("--margen",type=float)
    parser.add_argument("--webrtc",action="store_true",help="Video local VP8 por WebRTC/UDP50000-50009")
    parser.add_argument("--descargar-modelo",action="store_true")
    parser.add_argument("--descargar-cnn",action="store_true")
    args = parser.parse_args()
    args.hilos,args.ancho,args.alto,args.fps,args.fps_proceso,args.confianza = 2,640,480,15,10,.6
    try:
        if not 1<=args.puerto<=65535 or args.camara<0:
            raise ValueError("Puerto o camara fuera de rango")
        if args.metodo=="cnn_reid":
            from .reid_openvino import configuracion, descargar
            args.cnn = configuracion(descargar() if args.descargar_cnn else None)
        cargar_parametros(args)
        if args.umbral is None:
            if args.metodo=="cnn_reid":
                raise ValueError("CNN necesita --parametros auto o --umbral calibrado")
            args.umbral = .45
        if args.margen is None:
            args.margen = .08
        limite = 2 if args.metodo=="cnn_reid" else 1
        if not math.isfinite(args.umbral) or not 0<=args.umbral<=limite or not math.isfinite(args.margen) or args.margen<0:
            raise ValueError("Umbral o margen fuera de rango")
        cv2.setNumThreads(1)
        carpeta = REPO/"datos/enrolamientos"/datetime.now().strftime("movil-%Y%m%d-%H%M%S-%f")
        carpeta.mkdir(parents=True)
        banco = BancoVision(args,carpeta)
        if args.webrtc:
            try:
                from .video_webrtc import WebRTCService
            except ImportError as error:
                raise RuntimeError("Instala software/percepcion/requirements-webrtc.txt") from error
            banco.webrtc = WebRTCService()
        try:
            server = ThreadingHTTPServer((args.host,args.puerto),manejador(banco))
        except OSError:
            if banco.webrtc is not None:
                banco.webrtc.close()
            raise
        server.daemon_threads = True
        hilo = threading.Thread(target=banco.ejecutar,daemon=True)
        hilo.start()
        print(f"NUC vision :{args.puerto}. Movimiento restringido. Datos: {carpeta}",flush=True)
        try:
            server.serve_forever(poll_interval=.2)
        except KeyboardInterrupt:
            pass
        finally:
            banco.stop.set()
            server.server_close()
            hilo.join(timeout=10)
            if banco.webrtc is not None:
                banco.webrtc.close()
    except (ValueError,OSError,RuntimeError) as error:
        parser.exit(1,f"Error: {error}\n")


if __name__=="__main__":
    main()
