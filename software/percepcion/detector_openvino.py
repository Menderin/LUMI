"""Detector CPU para el modelo Intel person-detection-0202."""
import hashlib
from pathlib import Path
from urllib.request import urlopen

import cv2
import numpy as np

MODELO = "person-detection-0202"
URL = f"https://storage.openvinotoolkit.org/repositories/open_model_zoo/2023.0/models_bin/1/{MODELO}/FP16"


def descargar(destino):
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    for extension in ("xml", "bin"):
        final = destino / f"{MODELO}.{extension}"
        if final.exists():
            continue
        temporal = final.with_suffix(final.suffix + ".part")
        try:
            with urlopen(f"{URL}/{final.name}", timeout=60) as entrada, temporal.open("wb") as salida:
                while bloque := entrada.read(1024 * 1024):
                    salida.write(bloque)
            if temporal.stat().st_size == 0:
                raise RuntimeError(f"Descarga vacia: {final.name}")
            temporal.replace(final)
        finally:
            temporal.unlink(missing_ok=True)
    return destino / f"{MODELO}.xml"


def decodificar(salida, ancho, alto, confianza):
    if salida.shape != (1, 1, 200, 7):
        raise RuntimeError(f"Salida incompatible con {MODELO}: {salida.shape}")
    cajas = []
    for imagen, clase, score, x, y, r, b in salida.reshape(-1, 7):
        if not np.isfinite([imagen, clase, score, x, y, r, b]).all():
            continue
        if imagen != 0 or clase != 0 or score < confianza:
            continue
        caja = tuple(round(float(np.clip(v, 0, 1)) * limite)
                     for v, limite in zip((x, y, r, b), (ancho, alto, ancho, alto)))
        if caja[0] < caja[2] and caja[1] < caja[3]:
            cajas.append(caja)
    return cajas


class DetectorOpenVINO:
    def __init__(self, ruta, confianza=.6, hilos=2):
        try:
            import openvino as ov
        except ImportError as error:
            raise RuntimeError("Instala software/percepcion/requirements-openvino.txt") from error
        ruta = Path(ruta)
        if not ruta.is_file() or not ruta.with_suffix(".bin").is_file():
            raise RuntimeError("Faltan pesos. Ejecuta primero con --descargar-modelo")
        core = ov.Core()
        modelo = core.read_model(str(ruta))
        if tuple(modelo.input().shape) != (1, 3, 512, 512):
            raise RuntimeError("Se requiere person-detection-0202 con entrada 1x3x512x512")
        self.modelo = core.compile_model(modelo, "CPU", {
            "INFERENCE_NUM_THREADS": hilos, "NUM_STREAMS": 1,
            "PERFORMANCE_HINT": "LATENCY", "ENABLE_CPU_PINNING": False,
        })
        self.peticion = self.modelo.create_infer_request()
        self.confianza = confianza
        self.metadata = {
            "openvino": ov.__version__, "modelo": MODELO, "dispositivo": "CPU",
            "hilos": self.modelo.get_property("INFERENCE_NUM_THREADS"),
            "streams": self.modelo.get_property("NUM_STREAMS"),
            "sha256": {ext: hashlib.sha256(ruta.with_suffix(ext).read_bytes()).hexdigest()
                       for ext in (".xml", ".bin")},
        }

    def __call__(self, frame):
        alto, ancho = frame.shape[:2]
        # El IR Intel espera BGR 0..255 NCHW. Sin normalizacion RGB adicional.
        entrada = cv2.resize(frame, (512, 512)).transpose(2, 0, 1)[None]
        entrada = np.ascontiguousarray(entrada, dtype=np.float32)
        self.peticion.infer({self.modelo.input(): entrada})
        salida = self.peticion.get_output_tensor().data
        return decodificar(salida, ancho, alto, self.confianza)
