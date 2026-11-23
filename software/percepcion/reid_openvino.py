"""Encoder corporal congelado: Intel person-reidentification-retail-0288."""
import argparse
import hashlib
import time
from pathlib import Path
from urllib.request import urlopen

import cv2
import numpy as np

MODELO = "person-reidentification-retail-0288"
DESTINO = Path(__file__).resolve().parents[2] / "modelos/pesos" / MODELO
URL = f"https://storage.openvinotoolkit.org/repositories/open_model_zoo/2023.0/models_bin/1/{MODELO}/FP16"
# SHA-384 del manifiesto oficial Open Model Zoo, FP16 (2023.0/models_bin/1).
ARCHIVOS = {
    "xml": (614533,"18814c6445b35224987bc44bcbdb47da6c3826e5da0b6aa00a88c06bf71491a8c4f42e1f62424c077cce46e76a41f7a2"),
    "bin": (364098,"0a5ca9d000ce63b078149a3aa3993cd6e92d52fdecf1ff58fbe717481c2043db348938c32fed964846817dc321825a4c"),
}


def validar_pesos(ruta):
    ruta=Path(ruta)
    hashes={}
    for extension,(tamano,esperado) in ARCHIVOS.items():
        archivo=ruta.with_suffix("."+extension)
        if not archivo.is_file():
            raise ValueError("Faltan pesos CNN. Usa --descargar-cnn o python -m software.percepcion.reid_openvino --descargar")
        contenido=archivo.read_bytes()
        if len(contenido)!=tamano or hashlib.sha384(contenido).hexdigest()!=esperado:
            raise ValueError(f"Peso CNN incompatible o incompleto: {archivo}")
        hashes[extension]=hashlib.sha256(contenido).hexdigest()
    return hashes


def descargar(destino=DESTINO):
    destino=Path(destino)
    destino.mkdir(parents=True,exist_ok=True)
    for extension,(tamano,esperado) in ARCHIVOS.items():
        final=destino/f"{MODELO}.{extension}"
        if final.exists():
            datos=final.read_bytes()
            if len(datos)==tamano and hashlib.sha384(datos).hexdigest()==esperado:
                continue
        temporal=final.with_suffix(final.suffix+".part")
        try:
            with urlopen(f"{URL}/{final.name}",timeout=30) as entrada, temporal.open("wb") as salida:
                while bloque:=entrada.read(1024*1024):
                    salida.write(bloque)
            datos=temporal.read_bytes()
            if len(datos)!=tamano or hashlib.sha384(datos).hexdigest()!=esperado:
                raise ValueError(f"Descarga CNN no coincide con manifiesto oficial: {final.name}")
            temporal.replace(final)
        finally:
            temporal.unlink(missing_ok=True)
    ruta=destino/f"{MODELO}.xml"
    validar_pesos(ruta)
    return ruta


def configuracion(ruta=None, hilos=2):
    ruta=Path(ruta) if ruta else DESTINO/f"{MODELO}.xml"
    if hilos not in (1,2):
        raise ValueError("CNN: usar uno o dos hilos para este piloto")
    return {"ruta":str(ruta.resolve()),"modelo":MODELO,"sha256":validar_pesos(ruta),
            "hilos":hilos,"dispositivo":"CPU","streams":1,
            "preproceso":"BGR float32 0..255, resize directo 256x128, NCHW",
            "distancia":"minima coseno contra embeddings L2 de galeria fija"}


def entrada(imagen):
    if imagen is None or imagen.ndim!=3 or imagen.shape[2]!=3 or imagen.size==0:
        raise ValueError("Recorte CNN invalido; se requiere imagen BGR")
    return np.ascontiguousarray(cv2.resize(imagen,(128,256)).transpose(2,0,1)[None],dtype=np.float32)


def normalizar(vector):
    vector=np.asarray(vector,dtype=np.float32).ravel().copy()
    norma=np.linalg.norm(vector)
    if vector.shape!=(256,) or not np.isfinite(vector).all() or not np.isfinite(norma) or norma<=0:
        raise ValueError("Embedding CNN invalido")
    return vector/norma


class ReIDOpenVINO:
    metodo="cnn_reid"

    def __init__(self,muestras,cfg):
        if not 8<=len(muestras)<=24:
            raise ValueError("CNN requiere galeria aprobada de 8 a 24 recortes")
        actual=configuracion(cfg["ruta"],cfg["hilos"])
        if actual!=cfg:
            raise ValueError("Configuracion o pesos CNN cambiaron despues de preparar")
        try:
            import openvino as ov
        except ImportError as error:
            raise RuntimeError("Instala software/percepcion/requirements-openvino.txt") from error
        core=ov.Core()
        modelo=core.read_model(cfg["ruta"])
        if tuple(modelo.input().shape)!=(1,3,256,128) or tuple(modelo.output().shape)!=(1,256):
            raise ValueError("Contrato de entrada/salida CNN incompatible")
        self.modelo=core.compile_model(modelo,"CPU",{
            "INFERENCE_NUM_THREADS":cfg["hilos"],"NUM_STREAMS":1,
            "PERFORMANCE_HINT":"LATENCY","ENABLE_CPU_PINNING":False})
        self.peticion=self.modelo.create_infer_request()
        # Calentamiento explicito antes de medir consultas; no entra en p95 offline.
        inicio=time.perf_counter()
        for _ in range(3):
            self.vector(muestras[0])
        calentamiento=(time.perf_counter()-inicio)*1000
        inicio=time.perf_counter()
        self.galeria=np.stack([self.vector(x) for x in muestras])
        self.metadata={**cfg,"openvino":ov.__version__,"dimension":256,"agregacion":"minimo",
                       "galeria_recortes":len(muestras),"entrenamiento":"externo preentrenado; encoder congelado",
                       "calentamiento_iteraciones":3,"calentamiento_ms":calentamiento,
                       "codificacion_galeria_ms":(time.perf_counter()-inicio)*1000}

    def vector(self,imagen):
        self.peticion.infer({self.modelo.input():entrada(imagen)})
        return normalizar(self.peticion.get_output_tensor().data)

    def distancias_galeria(self,imagen):
        vector=self.vector(imagen)
        return 1-np.clip(self.galeria@vector,-1,1)

    def distancia(self,imagen):
        return float(np.min(self.distancias_galeria(imagen)))

    def guardar(self,ruta):
        np.savez_compressed(ruta,metodo=np.array(self.metodo),galeria=self.galeria,
                            modelo=np.array(MODELO),sha256_xml=np.array(self.metadata["sha256"]["xml"]),
                            sha256_bin=np.array(self.metadata["sha256"]["bin"]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--descargar",action="store_true")
    parser.add_argument("--destino",type=Path,default=DESTINO)
    args=parser.parse_args()
    try:
        ruta=descargar(args.destino) if args.descargar else args.destino/f"{MODELO}.xml"
        print(configuracion(ruta))
    except (ValueError,OSError) as error:
        parser.exit(1,f"Error: {error}\n")


if __name__=="__main__":
    main()
