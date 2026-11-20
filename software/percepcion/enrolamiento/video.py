"""Extraer hasta 24 recortes despues de finalizar el video de enrolamiento."""
import cv2
import numpy as np


def extraer(ruta, registros, maximo=24):
    validos = []
    motivos = {"sin_persona": 0, "varias_personas": 0, "borde": 0}
    for registro in registros:
        cajas = registro["cajas"]
        if not cajas:
            motivos["sin_persona"] += 1
        elif len(cajas) != 1:
            motivos["varias_personas"] += 1
        else:
            x, y, r, b = cajas[0]
            if x <= 1 or y <= 1 or r >= registro["ancho"] - 1 or b >= registro["alto"] - 1:
                motivos["borde"] += 1
            else:
                validos.append(registro)
    seleccionados = [validos[i] for i in np.linspace(
        0, len(validos)-1, min(maximo, len(validos)), dtype=int)] if validos else []
    elegidos = {r["frame"]: r for r in seleccionados}
    muestras, origenes = [], []
    captura = cv2.VideoCapture(str(ruta))
    if not captura.isOpened():
        raise RuntimeError("No se pudo reabrir el video grabado")
    try:
        indice = 0
        while True:
            ok, imagen = captura.read()
            if not ok:
                break
            if indice in elegidos:
                r = elegidos[indice]
                x, y, derecha, abajo = r["cajas"][0]
                if not (0 <= x < derecha <= imagen.shape[1] and 0 <= y < abajo <= imagen.shape[0]):
                    raise ValueError("Resolucion del video incompatible con los recuadros")
                muestras.append(imagen[y:abajo, x:derecha].copy())
                origenes.append({"frame": indice, "tiempo_s": r["tiempo_s"], "bbox": r["cajas"][0]})
            indice += 1
    finally:
        captura.release()
    if indice != len(registros):
        raise RuntimeError(f"Video incompleto: {indice} frames leidos / {len(registros)} registrados")
    return muestras, {"frames_video": indice, "validos": len(validos), "descartes": motivos,
                      "recortes": len(muestras), "seleccion": origenes}
