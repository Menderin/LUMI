"""Práctica de visión local, sin interfaces de control del robot."""
import argparse
import csv
import json
import math
import platform
import subprocess
import time
import traceback
from collections import Counter, deque
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import psutil

from .enrolamiento.sesion import SesionEnrolamiento
from .enrolamiento.video import extraer
from software.control.direccion_simulada import DireccionSimulada
from .experimentos import Identificador, recortar, crear_identificadores, guardar_representacion

VENTANA = "LUMI - Vision"
REVISION = "LUMI - Revision (Enter aprueba, R descarta)"
REPO = Path(__file__).resolve().parents[2]


def ventana_visible(nombre):
    try:
        return cv2.getWindowProperty(nombre, cv2.WND_PROP_VISIBLE) >= 1
    except cv2.error:
        # Qt elimina el receptor al cerrar la ultima ventana.
        return False


class DetectorHOG:
    def __init__(self, umbral=.5):
        self.umbral = umbral
        if not hasattr(cv2, "HOGDescriptor"):
            raise RuntimeError(
                f"OpenCV {cv2.__version__} no incluye HOGDescriptor. "
                "Reinstala opencv-python>=4.10,<5 en el entorno de la practica."
            )
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def __call__(self, frame):
        alto, ancho = frame.shape[:2]
        if ancho < 64 or alto < 128:
            return []
        rects, pesos = self.hog.detectMultiScale(
            frame, self.umbral, (8, 8), (8, 8), 1.05, 2,
        )
        if len(rects) == 0:
            return []
        indices = cv2.dnn.NMSBoxes(rects.tolist(), np.ravel(pesos).tolist(), 0.0, 0.4)
        return [
            (max(0, x), max(0, y), min(ancho, x + w), min(alto, y + h))
            for x, y, w, h in (map(int, rects[i]) for i in np.ravel(indices).astype(int))
        ]


def detectar(frame, detector):
    alto, ancho = frame.shape[:2]
    return [
        caja for caja in detector(frame)
        if caja[0] < caja[2] <= ancho and caja[1] < caja[3] <= alto
    ]


def recorte_enrolamiento(frame, cajas):
    if len(cajas) != 1:
        return None
    x, y, r, b = cajas[0]
    alto, ancho = frame.shape[:2]
    if x <= 1 or y <= 1 or r >= ancho - 1 or b >= alto - 1:
        return None
    return recortar(frame, cajas[0])


def resolver(distancias, umbral, margen):
    if not distancias:
        return None, "ausencia"
    orden = sorted(range(len(distancias)), key=distancias.__getitem__)
    primero = orden[0]
    if distancias[primero] > umbral:
        return None, "rechazo"
    if len(orden) > 1 and distancias[orden[1]] - distancias[primero] <= margen:
        return None, "ambiguedad"
    return primero, "coincidencia"


def dibujar(frame, cajas, distancias, objetivo, mensaje, detalle):
    imagen = frame.copy()
    for i, (x, y, r, b) in enumerate(cajas):
        color = (0, 230, 0) if i == objetivo else (0, 185, 255)
        cv2.rectangle(imagen, (x, y), (r - 1, b - 1), color, 2)
        if distancias:
            cv2.putText(imagen, f"d={distancias[i]:.3f}", (x, max(16, y - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1, cv2.LINE_AA)
    for y, texto in ((20, mensaje), (40, detalle)):
        cv2.putText(imagen, texto, (6, y), cv2.FONT_HERSHEY_SIMPLEX, .48, (0, 0, 0), 3)
        cv2.putText(imagen, texto, (6, y), cv2.FONT_HERSHEY_SIMPLEX, .48, (255, 255, 255), 1)
    return imagen


def mostrar_rendimiento(imagen, procesamiento_ms, iteraciones, cpu_sistema, cpu_proceso):
    """Panel inferior. Iteraciones incluye espera; procesamiento termina antes del panel."""
    alto, ancho = imagen.shape[:2]
    fps = len(iteraciones) / sum(iteraciones) if iteraciones else None
    ciclo = iteraciones[-1] * 1000 if iteraciones else None
    fps_texto = f"{fps:.1f}" if fps is not None else "--"
    ciclo_texto = f"{ciclo:.0f}" if ciclo is not None else "--"
    textos = [
        f"Proc: {procesamiento_ms:.0f} ms | Ciclo: {ciclo_texto} ms | FPS: {fps_texto}",
        f"CPU PC: {cpu_sistema:.0f}% | CPU LUMI: {cpu_proceso:.0f}%",
    ]
    escala = min(.7, max(.3, (ancho - 16) / 650))
    altura_linea = max(22, round(34 * escala / .7))
    inicio = max(0, alto - altura_linea * 2 - 12)
    cv2.rectangle(imagen, (0, inicio), (ancho - 1, alto - 1), (20, 20, 20), -1)
    for i, texto in enumerate(textos):
        cv2.putText(imagen, texto, (8, inicio + altura_linea * (i + 1)),
                    cv2.FONT_HERSHEY_SIMPLEX, escala, (255, 255, 255), 2, cv2.LINE_AA)


class Video:
    def __init__(self, ruta, fps, frame):
        self.ruta = ruta
        self.tamano = frame.shape[1], frame.shape[0]
        self.writer = cv2.VideoWriter(str(ruta), cv2.VideoWriter_fourcc(*"MJPG"),
                                      fps, self.tamano)
        if not self.writer.isOpened():
            self.writer.release()
            raise RuntimeError(f"No se pudo grabar {ruta}")

    def escribir(self, frame):
        if (frame.shape[1], frame.shape[0]) != self.tamano:
            raise RuntimeError("La cámara cambió de resolución durante la grabación")
        self.writer.write(frame)

    def cerrar(self):
        self.writer.release()



def normalizar_tecla(codigo):
    if codigo < 0:
        return -1
    codigo &= 0xff
    return codigo + 32 if ord("A") <= codigo <= ord("Z") else codigo


def botones(imagen, opciones, y):
    ancho = imagen.shape[1]
    paso = ancho // len(opciones)
    zonas = []
    for i, (etiqueta, tecla) in enumerate(opciones):
        x = i * paso
        derecha = ancho - 1 if i == len(opciones)-1 else (i+1)*paso-2
        cv2.rectangle(imagen, (x+1, y), (derecha, y+36), (65,65,65), -1)
        escala = min(.5, (paso-12)/max(1, cv2.getTextSize(etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 1, 1)[0][0]))
        cv2.putText(imagen, etiqueta, (x+6, y+23), cv2.FONT_HERSHEY_SIMPLEX,
                    escala, (255,255,255), 1, cv2.LINE_AA)
        zonas.append((x, y, derecha, y+36, tecla))
    return zonas


def callback_botones(zonas, cola):
    def pulsar(evento, x, y, flags, parametro):
        if evento == cv2.EVENT_LBUTTONDOWN:
            for izquierda, arriba, derecha, abajo, tecla in zonas:
                if izquierda <= x <= derecha and arriba <= y <= abajo:
                    cola.append(tecla)
                    break
    return pulsar


def revisar(ruta, muestras, registros=None):
    """Una sola ventana de revision con video, 24 miniaturas y botones."""
    hoja = np.zeros((448, 384, 3), np.uint8)
    for i, muestra in enumerate(muestras):
        fila, col = divmod(i, 6)
        imagen = cv2.resize(muestra, (64,112))
        hoja[fila*112:(fila+1)*112, col*64:(col+1)*64] = imagen
    captura = cv2.VideoCapture(str(ruta))
    if not captura.isOpened():
        raise RuntimeError(f"No se pudo revisar {ruta}")
    registros = registros or []
    cola = deque()
    cv2.namedWindow(REVISION, cv2.WINDOW_NORMAL)
    aviso = "Enter aprueba | R repite | C cancela. Clic en botones tambien."
    try:
        fps = captura.get(cv2.CAP_PROP_FPS)
        pausa = max(1, round(1000/(fps if fps > 0 else 10)))
        while True:
            indice = int(captura.get(cv2.CAP_PROP_POS_FRAMES))
            ok, frame = captura.read()
            if not ok:
                if indice == 0:
                    raise RuntimeError("El video de revision esta vacio")
                captura.set(cv2.CAP_PROP_POS_FRAMES,0)
                continue
            if indice < len(registros):
                for x,y,r,b in registros[indice]["cajas"]:
                    cv2.rectangle(frame,(x,y),(r,b),(0,200,255),2)
            lienzo = np.zeros((560,1024,3), np.uint8)
            lienzo[:480,:640] = cv2.resize(frame,(640,480))
            lienzo[:448,640:] = hoja
            cv2.putText(lienzo,aviso,(8,500),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),1)
            zonas = botones(lienzo,[("Aprobar [Enter]",13),("Repetir [R]",ord("r")),
                                     ("Cancelar [C]",ord("c")),("Salir [Esc]",27)],514)
            cv2.setMouseCallback(REVISION,callback_botones(zonas,cola))
            cv2.imshow(REVISION,lienzo)
            tecla = normalizar_tecla(cv2.waitKey(pausa))
            if cola:
                tecla = cola.popleft()
            if tecla in (10,13,ord("r"),ord("c"),27):
                return tecla
            if tecla == ord("s"):
                aviso = "Primero aprueba con Enter. Luego S inicia en la ventana principal."
            if not ventana_visible(REVISION):
                return ord("c")
    finally:
        captura.release()
        try:
            cv2.destroyWindow(REVISION)
        except cv2.error:
            pass


def commit_local():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def guardar_json(ruta, datos):
    ruta.write_text(json.dumps(datos, indent=2) + "\n", encoding="utf-8")


def foto_parametros(captura):
    return {
        "ancho": int(captura.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "alto": int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps_reportado": captura.get(cv2.CAP_PROP_FPS),
    }


def abrir_camara(args):
    backend = cv2.CAP_V4L2 if platform.system() == "Linux" else cv2.CAP_ANY
    captura = cv2.VideoCapture(args.camara, backend)
    if not captura.isOpened():
        captura.release()
        raise RuntimeError(f"No se pudo abrir la cámara {args.camara}")
    captura.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    for propiedad, valor in ((cv2.CAP_PROP_FRAME_WIDTH, args.ancho),
                             (cv2.CAP_PROP_FRAME_HEIGHT, args.alto),
                             (cv2.CAP_PROP_FPS, args.fps)):
        captura.set(propiedad, valor)
    return captura


def resumen(tiempos, segundos):
    return {
        "frames": len(tiempos),
        "fps_efectivos": round(len(tiempos) / segundos, 2) if segundos > 0 else None,
        "latencia_local_p50_ms": float(np.percentile(tiempos, 50)) if tiempos else None,
        "latencia_local_p95_ms": float(np.percentile(tiempos, 95)) if tiempos else None,
    }


def practica(args, carpeta):
    cv2.setNumThreads(1)
    if args.detector == "openvino":
        from .detector_openvino import DetectorOpenVINO, descargar
        ruta = REPO / "modelos/pesos/person-detection-0202/person-detection-0202.xml"
        if args.descargar_modelo:
            descargar(ruta.parent)
        detector = DetectorOpenVINO(ruta, args.confianza, args.hilos)
    else:
        detector = DetectorHOG(args.hog_umbral)
    captura = abrir_camara(args)
    sesion = SesionEnrolamiento(desde_video=True, recuperacion_simulada=True)
    estado = sesion.registro
    direccion = DireccionSimulada()
    identificador = None
    intento = None
    registros_intento = []
    informe_intento = {}
    cola_botones = deque()
    clip = None
    video_intento = None
    frames_clip = 0
    duracion = 0.0
    tiempos = []
    conteos = Counter()
    proceso = psutil.Process()
    proceso.cpu_percent()
    psutil.cpu_percent()
    recursos = (carpeta / "recursos.csv").open("w", newline="", encoding="utf-8")
    recursos_log = csv.writer(recursos)
    recursos_log.writerow(["tiempo_s", "cpu_sistema_pct", "cpu_proceso_pct_total",
                          "rss_mib", "disponible_mib", "swap_usada_mib", "temperatura_c"])
    ultimo_recurso = 0.0
    cpu_sistema = 0.0
    cpu_proceso = 0.0
    iteraciones = deque(maxlen=30)
    try:
        formato = foto_parametros(captura)
        print(f"Camara: {formato}. Datos locales: {carpeta}", flush=True)
        guardar_json(carpeta / "configuracion.json", {
            **vars(args), "captura": formato, "opencv": cv2.__version__,
            "commit": commit_local(), "sistema": platform.platform(),
             "detector": args.detector, "identificador": getattr(args, "metodo", "histograma"),
            "runtime": getattr(detector, "metadata", {}),
            "recuperacion_simulada": sesion.recuperacion_simulada,
            "coincidencias_para_reanudar": 3,
        })
        fps = formato["fps_reportado"]
        fps = min(fps if math.isfinite(fps) and fps > 0 else args.fps, args.fps_proceso)
        cv2.namedWindow(VENTANA, cv2.WINDOW_NORMAL)
        with (carpeta / "decisiones.csv").open("w", newline="", encoding="utf-8") as archivo:
            log = csv.writer(archivo)
            log.writerow(["frame", "tiempo_monotonico_s", "estado", "motivo", "cajas",
                          "distancias", "objetivo", "latencia_local_ms", "clip", "frame_clip", "zona", "x_normalizada", "intencion", "detector_ms"])
            tecla = -1
            while True:
                inicio = time.monotonic()
                if cola_botones:
                    tecla = cola_botones.popleft()
                if inicio - ultimo_recurso >= 1:
                    memoria = psutil.virtual_memory()
                    temperaturas = []
                    try:
                        swap_usada = psutil.swap_memory().used / 2**20
                    except (OSError, RuntimeError):
                        swap_usada = ""
                    if hasattr(psutil, "sensors_temperatures"):
                        temperaturas = [t.current for grupo in psutil.sensors_temperatures().values()
                                        for t in grupo if t.current is not None]
                    cpu_sistema = psutil.cpu_percent()
                    cpu_proceso = proceso.cpu_percent() / (psutil.cpu_count() or 1)
                    recursos_log.writerow([
                        inicio, cpu_sistema, cpu_proceso,
                        proceso.memory_info().rss / 2**20, memoria.available / 2**20,
                        swap_usada,
                        max(temperaturas) if temperaturas else "",
                    ])
                    recursos.flush()
                    ultimo_recurso = inicio
                ok, frame = captura.read()
                if not ok:
                    raise RuntimeError("La cámara dejó de entregar imágenes")
                ahora = time.monotonic()
                inicio_detector = time.monotonic()
                cajas = detectar(frame, detector)
                detector_ms = (time.monotonic() - inicio_detector) * 1000
                distancias = []
                candidato = None
                motivo = "sin_galeria"
                if tecla in (ord("r"), ord("c")):
                    if intento is not None:
                        intento.cerrar()
                        intento = None
                        guardar_json(video_intento.with_suffix(".captura.json"), registros_intento)
                    if clip is not None:
                        clip.cerrar()
                        clip = None
                    accion = "repetir" if tecla == ord("r") else "cancelar"
                    if sesion.accion(accion, ahora, personas=len(cajas)):
                        identificador = None
                if tecla == ord("e"):
                    sesion.accion("iniciar", ahora, personas=len(cajas))
                if identificador is not None:
                    distancias = [identificador.distancia(recortar(frame, caja)) for caja in cajas]
                    candidato, motivo = resolver(distancias, args.umbral, args.margen)
                if tecla == ord("s"):
                    accion = "reanudar" if estado.estado == "perdido" else "iniciar_seguimiento"
                    sesion.accion(accion, ahora, objetivo=candidato is not None)
                siguiendo = sesion.actualizar(
                    ahora, objetivo=candidato is not None, personas=len(cajas),
                    recorte=recorte_enrolamiento(frame, cajas) if not sesion.desde_video else None,
                )
                if estado.estado == "enrolando" and intento is None:
                    video_intento = carpeta / f"enrolamiento-{estado.intentos}.avi"
                    intento = Video(video_intento, fps, frame)
                    registros_intento = []
                    informe_intento = {}
                objetivo = candidato if siguiendo else None
                muestras = len(estado.muestras)
                mensaje = estado.estado if identificador is None or siguiendo else "Sin objetivo"
                if estado.estado == "preparando":
                    mensaje = f"Preparate: {math.ceil(sesion.estado(ahora)['segundos_restantes'])}"
                elif estado.estado == "enrolando":
                    restante = math.ceil(sesion.estado(ahora)["segundos_restantes"])
                    mensaje = f"Grabando video: {restante}s restantes ({len(registros_intento)} frames)"
                elif estado.estado == "procesando":
                    mensaje = "Extrayendo hasta 24 recortes del video..."
                elif estado.estado == "perdido" and sesion.recuperacion_simulada:
                    mensaje = "Buscando objetivo..."
                elif estado.estado == "listo":
                    mensaje = "Listo - S inicia seguimiento"
                elif estado.estado in ("espera", "fallo") and estado.intentos == 5:
                    mensaje = "Limite de 5 intentos"
                elif identificador is not None and motivo == "coincidencia" and not siguiendo:
                    motivo = ("confirmando_reencuentro" if estado.estado == "perdido"
                              and sesion.recuperacion_simulada else "esperando_confirmacion")
                imagen = dibujar(frame, cajas, distancias, objetivo, mensaje,
                                 f"E enrolar | R repetir | C cancelar | S seguir | V video | Esc")
                orden = direccion.actualizar(
                    cajas[objetivo] if objetivo is not None else None, frame.shape[1],
                    buscando=estado.estado == "perdido" and sesion.recuperacion_simulada)
                for limite in (.4, .6):
                    x = round(frame.shape[1] * limite)
                    cv2.line(imagen, (x, 55), (x, max(55, frame.shape[0] - 85)), (255, 200, 0), 1)
                cv2.putText(imagen, sesion.mensaje[:84], (8, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, .43, (255,255,255), 1)
                zonas = botones(imagen, [("Enrolar [E]",ord("e")),("Repetir [R]",ord("r")),
                                       ("Cancelar [C]",ord("c")),("Seguir [S]",ord("s")),
                                       ("Grabar [V]",ord("v"))], max(96,imagen.shape[0]-126))
                cv2.setMouseCallback(VENTANA,callback_botones(zonas,cola_botones))
                cv2.putText(imagen, "SIMULACION: " + orden["intencion"], (8, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, .65, (255, 255, 255), 2)
                latencia = (time.monotonic() - inicio) * 1000
                mostrar_rendimiento(imagen, latencia, iteraciones, cpu_sistema, cpu_proceso)
                tiempos.append(latencia)
                conteos[motivo] += 1
                if tecla == ord("v"):
                    if clip is not None:
                        clip.cerrar()
                        clip = None
                    else:
                        clip = Video(carpeta / f"prueba-{len(tiempos)}.avi", fps, frame)
                        frames_clip = 0
                log.writerow([len(tiempos), ahora, estado.estado, motivo, json.dumps(cajas),
                              json.dumps(distancias), objetivo, latencia,
                              clip.ruta.name if clip else "", frames_clip if clip else "",
                              orden["zona"], orden["x_normalizada"], orden["intencion"], detector_ms])
                if clip is not None:
                    clip.escribir(frame)
                    frames_clip += 1
                if intento is not None:
                    if estado.estado == "enrolando":
                        intento.escribir(frame)
                        registros_intento.append({
                            "frame": len(registros_intento), "tiempo_s": ahora,
                            "cajas": cajas, "ancho": frame.shape[1], "alto": frame.shape[0],
                        })
                    else:
                        intento.cerrar()
                        intento = None
                        guardar_json(video_intento.with_suffix(".captura.json"), registros_intento)
                        if estado.estado == "procesando":
                            cv2.imshow(VENTANA, imagen)
                            cv2.waitKey(1)
                            try:
                                muestras_video, informe_intento = extraer(video_intento, registros_intento)
                                if not sesion.completar_video(muestras_video):
                                    descartes = informe_intento["descartes"]
                                    sesion.mensaje += f"; sin persona {descartes['sin_persona']}, varias {descartes['varias_personas']}, borde {descartes['borde']}"
                            except (ValueError, OSError, RuntimeError, cv2.error) as error:
                                sesion.fallar(f"Extraccion fallida: {error}")
                                informe_intento = {"error": str(error)}
                            guardar_json(video_intento.with_suffix(".extraccion.json"), informe_intento)
                            print(sesion.mensaje, flush=True)
                cv2.imshow(VENTANA, imagen)
                espera_ms = max(1, round((1 / args.fps_proceso - (time.monotonic() - inicio)) * 1000))
                tecla = normalizar_tecla(cv2.waitKey(espera_ms))
                ciclo = time.monotonic() - inicio
                iteraciones.append(ciclo)
                duracion += ciclo
                if tecla == 27 or not ventana_visible(VENTANA):
                    break
                if estado.estado == "revision":
                    log_decision = revisar(video_intento, estado.muestras, registros_intento)
                    cola_botones.clear()
                    if log_decision == 27:
                        break
                    if log_decision in (10, 13):
                        try:
                            modelos = crear_identificadores(estado.muestras, REPO)
                        except ValueError as error:
                            print(f"Enrolamiento fallido: {error}", flush=True)
                            sesion.fallar(f"Codificacion fallida: {error}")
                            tecla = -1
                            continue
                        sesion.accion("confirmar", time.monotonic())
                        destino = carpeta / f"galeria-{estado.intentos}"
                        destino.mkdir()
                        for i, muestra in enumerate(estado.galeria, 1):
                            if not cv2.imwrite(str(destino / f"{i:02}.png"), muestra):
                                raise RuntimeError("No se pudo guardar un recorte aprobado")
                        for nombre, modelo in modelos.items():
                            guardar_representacion(modelo, destino / f"{nombre}.npz")
                        guardar_json(destino / "galeria.json", {
                            "aprobada": True, "sesion": carpeta.name, "intento": estado.intentos,
                            "imagenes": [f"{i:02}.png" for i in range(1, len(estado.galeria) + 1)],
                            "metodos": list(modelos), "duracion_captura_s": sesion.duracion,
                            "origen_recortes": informe_intento.get("seleccion", []),
                        })
                        print(f"Galeria aprobada: {destino}. Pulsa S para iniciar.", flush=True)
                        identificador = modelos[getattr(args, "metodo", "histograma")]
                        tecla = -1
                    else:
                        sesion.accion("cancelar", time.monotonic())
                        tecla = ord("r") if log_decision == ord("r") else -1
    except Exception:
        guardar_json(carpeta / "error.json", {"error": traceback.format_exc(),
                     "estado": estado.estado, "intento": estado.intentos})
        raise
    finally:
        captura.release()
        recursos.close()
        guardar_json(carpeta / "acciones.json", sesion.eventos)
        if video_intento is not None:
            guardar_json(video_intento.with_suffix(".captura.json"), registros_intento)
        for video in (intento, clip):
            if video is not None:
                video.cerrar()
        cv2.destroyAllWindows()
        guardar_json(carpeta / "resumen.json", {
            **resumen(tiempos, duracion), "decisiones": conteos, "intentos": estado.intentos,
        })


def comparar_hog(video, carpeta, hog_umbral=.5):
    detector = DetectorHOG(hog_umbral)
    resultados = {}
    for ancho, alto in ((640, 480), (320, 240)):
        captura = cv2.VideoCapture(video)
        tiempos = []
        detecciones = Counter()
        inicio = time.monotonic()
        try:
            if not captura.isOpened():
                raise RuntimeError(f"No se pudo abrir {video}")
            with (carpeta / f"hog-{ancho}x{alto}.csv").open("w", newline="", encoding="utf-8") as archivo:
                log = csv.writer(archivo)
                log.writerow(["frame", "cajas", "latencia_local_ms"])
                while True:
                    t0 = time.monotonic()
                    ok, frame = captura.read()
                    if not ok:
                        break
                    h, w = frame.shape[:2]
                    escala = min(ancho / w, alto / h)
                    ajustado = cv2.resize(frame, (max(1, round(w * escala)), max(1, round(h * escala))))
                    cajas = detectar(ajustado, detector)
                    tiempos.append((time.monotonic() - t0) * 1000)
                    detecciones[str(len(cajas))] += 1
                    log.writerow([len(tiempos), json.dumps(cajas), tiempos[-1]])
            if not tiempos:
                raise RuntimeError(f"El vídeo no contiene fotogramas decodificables: {video}")
        finally:
            captura.release()
        resultados[f"{ancho}x{alto}"] = {
            **resumen(tiempos, time.monotonic() - inicio), "frames_por_numero_de_cajas": detecciones,
        }
    guardar_json(carpeta / "comparacion-hog.json", {
        "video": video, "commit": commit_local(), "opencv": cv2.__version__, "hog_umbral": hog_umbral,
        "resultados": resultados,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    entrada = parser.add_mutually_exclusive_group()
    entrada.add_argument("--camara", type=int, default=0, help="Número V4L2 en Linux")
    entrada.add_argument("--video", help="Comparar HOG a dos resoluciones sobre este vídeo")
    parser.add_argument("--detector", choices=["hog", "openvino"], default="openvino")
    parser.add_argument("--descargar-modelo", action="store_true")
    parser.add_argument("--hilos", type=int, default=2)
    parser.add_argument("--fps-proceso", type=float, default=10)
    parser.add_argument("--confianza", type=float, default=.6)
    parser.add_argument("--ancho", type=int, default=640)
    parser.add_argument("--alto", type=int, default=480)
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument("--metodo", choices=["histograma", "euclidea", "mahalanobis"], default="histograma")
    parser.add_argument("--umbral", type=float, help="Provisional en vivo; PCA requiere especificarlo")
    parser.add_argument("--hog-umbral", type=float, default=.5, help="Umbral SVM HOG, provisional")
    parser.add_argument("--margen", type=float, default=.08, help="Valor provisional para piloto")
    args = parser.parse_args()
    if args.umbral is None:
        if args.metodo != "histograma":
            parser.error("Indica --umbral calibrado para PCA; las escalas son distintas")
        args.umbral = .45
    if args.video and args.detector != "hog":
        parser.error("--video conserva la comparacion HOG; OpenVINO se prueba con --camara")
    if args.descargar_modelo and args.detector != "openvino":
        parser.error("--descargar-modelo requiere --detector openvino")
    if (args.hilos < 1 or not math.isfinite(args.fps_proceso) or not 0 < args.fps_proceso <= 60
            or not 0 <= args.confianza <= 1
            or not math.isfinite(args.hog_umbral) or args.hog_umbral < 0
            or args.camara < 0 or args.ancho < 64 or args.alto < 128 or args.fps < 1
            or not math.isfinite(args.umbral) or args.umbral < 0
            or (args.metodo == "histograma" and args.umbral > 1)
            or not math.isfinite(args.margen) or args.margen < 0):
        parser.error("Cámara, resolución, FPS, umbral o margen fuera de rango")
    carpeta = REPO / "datos" / "enrolamientos" / datetime.now().strftime("practica-%Y%m%d-%H%M%S-%f")
    carpeta.mkdir(parents=True, exist_ok=False)
    try:
        if args.video:
            comparar_hog(args.video, carpeta, args.hog_umbral)
        else:
            practica(args, carpeta)
    except (RuntimeError, ValueError, ImportError, cv2.error, OSError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"Resultados locales: {carpeta}")


if __name__ == "__main__":
    main()
