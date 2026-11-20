"""Práctica de visión local, sin interfaces de control del robot."""
import argparse
import csv
import json
import math
import platform
import subprocess
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from .enrolamiento.estado import Enrolamiento
from .experimentos import Identificador, recortar

VENTANA = "LUMI - Vision"
REVISION = "LUMI - Revision (Enter aprueba, R descarta)"
REPO = Path(__file__).resolve().parents[2]


class DetectorHOG:
    def __init__(self):
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
            frame, winStride=(8, 8), padding=(8, 8), scale=1.05, finalThreshold=2,
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


def revisar(ruta, muestras):
    """Reproduce el intento y deja los recortes visibles hasta decidir."""
    miniaturas = [cv2.resize(m, (64, 112)) for m in muestras]
    hoja = np.zeros((224, 384, 3), np.uint8)
    for i, imagen in enumerate(miniaturas):
        fila, col = divmod(i, 6)
        hoja[fila*112:(fila+1)*112, col*64:(col+1)*64] = imagen
    captura = cv2.VideoCapture(str(ruta))
    if not captura.isOpened():
        captura.release()
        raise RuntimeError(f"No se pudo revisar el video {ruta}")
    try:
        ok, frame = captura.read()
        if not ok:
            raise RuntimeError(f"El video de enrolamiento está vacío: {ruta}")
        cv2.imshow(REVISION, frame)
        cv2.imshow("Recortes - frente, espalda y perfiles", hoja)
        fps = captura.get(cv2.CAP_PROP_FPS)
        pausa = max(1, round(1000 / (fps if fps > 0 else 15)))
        while True:
            ok, frame = captura.read()
            if ok:
                cv2.imshow(REVISION, frame)
            else:
                captura.set(cv2.CAP_PROP_POS_FRAMES, 0)
            tecla = cv2.waitKey(pausa) & 0xff
            if tecla in (10, 13, ord("r"), 27):
                return tecla
            if cv2.getWindowProperty(REVISION, cv2.WND_PROP_VISIBLE) < 1:
                return ord("r")
    finally:
        captura.release()
        for ventana in (REVISION, "Recortes - frente, espalda y perfiles"):
            try:
                cv2.destroyWindow(ventana)
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
    detector = DetectorHOG()
    captura = abrir_camara(args)
    estado = Enrolamiento()
    identificador = None
    intento = None
    clip = None
    video_intento = None
    frames_clip = 0
    duracion = 0.0
    tiempos = []
    conteos = Counter()
    try:
        formato = foto_parametros(captura)
        print(f"Camara: {formato}. Datos locales: {carpeta}", flush=True)
        guardar_json(carpeta / "configuracion.json", {
            **vars(args), "captura": formato, "opencv": cv2.__version__,
            "commit": commit_local(), "sistema": platform.platform(),
            "detector": "HOG", "identificador": "HSV / Bhattacharyya",
        })
        fps = formato["fps_reportado"]
        fps = fps if math.isfinite(fps) and fps > 0 else args.fps
        cv2.namedWindow(VENTANA, cv2.WINDOW_NORMAL)
        with (carpeta / "decisiones.csv").open("w", newline="", encoding="utf-8") as archivo:
            log = csv.writer(archivo)
            log.writerow(["frame", "tiempo_monotonico_s", "estado", "motivo", "cajas",
                          "distancias", "objetivo", "latencia_local_ms", "clip", "frame_clip"])
            tecla = -1
            while True:
                inicio = time.monotonic()
                ok, frame = captura.read()
                if not ok:
                    raise RuntimeError("La cámara dejó de entregar imágenes")
                ahora = time.monotonic()
                cajas = detectar(frame, detector)
                distancias = []
                candidato = None
                motivo = "sin_galeria"
                if tecla == ord("r"):
                    if intento is not None:
                        intento.cerrar()
                        intento = None
                    if clip is not None:
                        clip.cerrar()
                        clip = None
                    estado.descartar()
                    identificador = None
                if (tecla == ord("e") and estado.estado in ("espera", "fallo")
                        and estado.intentos < 5 and len(cajas) == 1):
                    estado.actualizar(ahora, pulsacion=True)
                    video_intento = carpeta / f"enrolamiento-{estado.intentos}.avi"
                    intento = Video(video_intento, fps, frame)
                elif identificador is not None:
                    distancias = [identificador.distancia(recortar(frame, caja)) for caja in cajas]
                    candidato, motivo = resolver(distancias, args.umbral, args.margen)
                siguiendo = estado.actualizar(
                    ahora, pulsacion=tecla in (10, 13) and identificador is not None,
                    objetivo=candidato is not None, personas=len(cajas),
                    recorte=recorte_enrolamiento(frame, cajas), pedir_revision=True,
                )
                objetivo = candidato if siguiendo else None
                muestras = len(estado.muestras)
                mensaje = estado.estado if identificador is None or siguiendo else "Sin objetivo"
                if estado.estado == "enrolando":
                    mensaje = f"Enrolando: {muestras}/12 muestras"
                elif estado.estado in ("espera", "fallo") and estado.intentos == 5:
                    mensaje = "Limite de 5 intentos"
                elif identificador is not None and motivo == "coincidencia" and not siguiendo:
                    motivo = "esperando_confirmacion"
                imagen = dibujar(frame, cajas, distancias, objetivo, mensaje,
                                 f"E enrolar | R reiniciar | V video | Esc   {motivo}")
                latencia = (time.monotonic() - inicio) * 1000
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
                              clip.ruta.name if clip else "", frames_clip if clip else ""])
                if clip is not None:
                    clip.escribir(frame)
                    frames_clip += 1
                if intento is not None:
                    intento.escribir(imagen)
                    if estado.estado != "enrolando":
                        intento.cerrar()
                        intento = None
                cv2.imshow(VENTANA, imagen)
                tecla = cv2.waitKey(1) & 0xff
                duracion += time.monotonic() - inicio
                if tecla == 27 or cv2.getWindowProperty(VENTANA, cv2.WND_PROP_VISIBLE) < 1:
                    break
                if estado.estado == "revision":
                    log_decision = revisar(video_intento, estado.muestras)
                    if log_decision == 27:
                        break
                    if log_decision in (10, 13):
                        estado.confirmar_revision(time.monotonic())
                        identificador = Identificador(estado.galeria, {"metodo": "histograma"}, REPO)
                        destino = carpeta / f"galeria-{estado.intentos}"
                        destino.mkdir()
                        for i, muestra in enumerate(estado.galeria, 1):
                            if not cv2.imwrite(str(destino / f"{i:02}.png"), muestra):
                                raise RuntimeError("No se pudo guardar un recorte aprobado")
                        tecla = 13
                    else:
                        estado.descartar()
                        tecla = -1
    finally:
        captura.release()
        for video in (intento, clip):
            if video is not None:
                video.cerrar()
        cv2.destroyAllWindows()
        guardar_json(carpeta / "resumen.json", {
            **resumen(tiempos, duracion), "decisiones": conteos, "intentos": estado.intentos,
        })


def comparar_hog(video, carpeta):
    detector = DetectorHOG()
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
        "video": video, "commit": commit_local(), "opencv": cv2.__version__,
        "resultados": resultados,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    entrada = parser.add_mutually_exclusive_group()
    entrada.add_argument("--camara", type=int, default=0, help="Número V4L2 en Linux")
    entrada.add_argument("--video", help="Comparar HOG a dos resoluciones sobre este vídeo")
    parser.add_argument("--ancho", type=int, default=640)
    parser.add_argument("--alto", type=int, default=480)
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument("--umbral", type=float, default=.45, help="Valor provisional para piloto")
    parser.add_argument("--margen", type=float, default=.08, help="Valor provisional para piloto")
    args = parser.parse_args()
    if (args.camara < 0 or args.ancho < 64 or args.alto < 128 or args.fps < 1
            or not 0 <= args.umbral <= 1 or not 0 <= args.margen <= 1):
        parser.error("Cámara, resolución, FPS, umbral o margen fuera de rango")
    carpeta = REPO / "datos" / "enrolamientos" / datetime.now().strftime("practica-%Y%m%d-%H%M%S-%f")
    carpeta.mkdir(parents=True, exist_ok=False)
    try:
        if args.video:
            comparar_hog(args.video, carpeta)
        else:
            practica(args, carpeta)
    except (RuntimeError, cv2.error, OSError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"Resultados locales: {carpeta}")


if __name__ == "__main__":
    main()
