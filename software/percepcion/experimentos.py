"""Banco offline. Ejecutar como módulo desde la raíz."""
import argparse
import hashlib
import json
import platform
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import psutil

from .dataset.manifiesto import cargar


def iou(a, b):
    x = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    y = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return x * y / max(1, (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - x*y)


def recortar(frame, caja):
    x, y, r, b = map(int, caja)
    h, w = frame.shape[:2]
    if not (0 <= x < r <= w and 0 <= y < b <= h):
        raise ValueError(f"Recuadro fuera de imagen: {caja}")
    return frame[y:b, x:r]


def gris(imagen, alto):
    h, w = imagen.shape[:2]
    ancho = alto // 2
    escala = min(alto / h, ancho / w)
    ajuste = cv2.resize(cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY),
                        (max(1, round(w*escala)), max(1, round(h*escala))))
    lienzo = np.zeros((alto, ancho), np.float32)
    y, x = (alto-ajuste.shape[0])//2, (ancho-ajuste.shape[1])//2
    lienzo[y:y+ajuste.shape[0], x:x+ajuste.shape[1]] = ajuste / 255
    return lienzo.ravel()


def histograma(imagen):
    hsv = cv2.cvtColor(imagen, cv2.COLOR_BGR2HSV)
    h, w = hsv.shape[:2]
    regiones = [hsv[int(h*a):max(int(h*a)+1, int(h*b)), w//4:max(w//4+1, 3*w//4)]
                for a, b in ((.2, .55), (.55, .95))]
    hist = [cv2.calcHist([r], [0, 1], None, [16, 8], [0, 180, 0, 256]).ravel()
            for r in regiones]
    return np.concatenate([x / x.sum() / 2 for x in hist])


def sesion_onnx(path, hilos):
    import onnxruntime as ort
    opciones = ort.SessionOptions()
    opciones.intra_op_num_threads = hilos
    return ort.InferenceSession(str(path), sess_options=opciones,
                                providers=["CPUExecutionProvider"])


class Identificador:
    def __init__(self, muestras, cfg, base):
        self.metodo = cfg["metodo"]
        self.alto = cfg.get("alto", 128)
        self.encoder = None
        if self.metodo == "reid":
            self.alto = cfg.get("alto", 256)
            self.encoder = sesion_onnx(base / cfg["encoder"], cfg.get("hilos", 1))
        if self.metodo not in {"histograma", "euclidea", "mahalanobis", "reid"}:
            raise ValueError("Método desconocido")
        if not 1 <= len(muestras) <= 12:
            raise ValueError("La galería debe contener entre 1 y 12 muestras")
        vectores = np.stack([self.vector(x) for x in muestras])
        if self.metodo in {"euclidea", "mahalanobis"}:
            self.media = vectores.mean(axis=0)
            centrado = vectores - self.media
            _, _, base_pca = np.linalg.svd(centrado, full_matrices=False)
            k = min(8, np.linalg.matrix_rank(centrado))
            if not k:
                raise ValueError("Galería sin variación suficiente para PCA")
            self.componentes = base_pca[:k]
            vectores = centrado @ self.componentes.T
            if self.metodo == "mahalanobis":
                from sklearn.covariance import LedoitWolf
                self.precision = LedoitWolf().fit(vectores).precision_
        self.galeria = vectores

    def vector(self, imagen):
        if self.metodo == "histograma":
            return histograma(imagen)
        if self.encoder:
            rgb = cv2.cvtColor(cv2.resize(imagen, (self.alto//2, self.alto)),
                               cv2.COLOR_BGR2RGB).astype(np.float32)/255
            rgb = (rgb - np.array([.485, .456, .406], np.float32)) / np.array(
                [.229, .224, .225], np.float32)
            valor = self.encoder.run(None, {
                self.encoder.get_inputs()[0].name: rgb.transpose(2, 0, 1)[None]
            })[0].ravel()
            norma = np.linalg.norm(valor)
            if not np.isfinite(norma) or norma == 0:
                raise ValueError("Embedding inválido")
            return valor / norma
        return gris(imagen, self.alto)

    def distancia(self, imagen):
        x = self.vector(imagen)
        if self.metodo == "histograma":
            return min(cv2.compareHist(x, g, cv2.HISTCMP_BHATTACHARYYA) for g in self.galeria)
        if self.encoder:
            return float(np.min(1 - self.galeria @ x))
        delta = (x - self.media) @ self.componentes.T - self.galeria
        if self.metodo == "mahalanobis":
            return float(np.sqrt(np.maximum(0, ((delta @ self.precision)*delta).sum(axis=1))).min())
        return float(np.linalg.norm(delta, axis=1).min())


class Detector:
    """Adaptador ONNX YOLO exportado con NMS: salida 1×N×6 xyxy, score, clase."""
    def __init__(self, cfg, base):
        self.cfg = cfg
        self.modelo = sesion_onnx(base / cfg["archivo"], cfg.get("hilos", 1))

    def __call__(self, frame):
        h, w = frame.shape[:2]
        lado = self.cfg["lado"]
        escala = min(lado/w, lado/h)
        imagen = cv2.resize(frame, (round(w*escala), round(h*escala)))
        ih, iw = imagen.shape[:2]
        fondo = np.full((lado, lado, 3), 114, np.uint8)
        fondo[:ih, :iw] = imagen
        entrada = np.ascontiguousarray(fondo[:, :, ::-1].transpose(2, 0, 1)[None],
                                       dtype=np.float32) / 255
        filas = self.modelo.run(None, {self.modelo.get_inputs()[0].name: entrada})[0]
        if filas.ndim != 3 or filas.shape[0] != 1 or filas.shape[2] != 6:
            raise ValueError("El detector requiere una salida ONNX 1×N×6 con NMS")
        cajas = []
        for x, y, r, b, confianza, clase in filas[0]:
            if clase != 0 or confianza < self.cfg["confianza"]:
                continue
            caja = [round(np.clip(v/s, 0, limite))
                    for v, s, limite in zip((x,y,r,b), (iw/w,ih/h,iw/w,ih/h), (w,h,w,h))]
            if caja[0] < caja[2] and caja[1] < caja[3]:
                cajas.append(caja)
        return cajas


def elegir(candidatos, umbral, margen, anterior=None):
    validos = sorted((d, i, caja) for i, (caja, d) in enumerate(candidatos) if d <= umbral)
    if not validos:
        return None
    if len(validos) > 1 and validos[1][0] - validos[0][0] <= margen:
        return None
    if anterior is not None:
        asociados = [item for item in validos if iou(item[2], anterior) >= .3]
        if len(asociados) == 1:
            return asociados[0][1]
    return validos[0][1]


def ejecutar(filas, split, base, cfg, identificador, detector, salida, vista_previa=False):
    proceso = psutil.Process()
    cpu_inicio = sum(proceso.cpu_times()[:2])
    inicio = time.perf_counter()
    rss = proceso.memory_info().rss
    resultados = []
    ventana = "LUMI - vista de camara"
    for fila in filas:
        if fila["split"] != split:
            continue
        captura = cv2.VideoCapture(str(base / fila["video"]))
        if not captura.isOpened():
            raise ValueError(f"No se pudo abrir {fila['video']}")
        anterior = None
        etiquetas = fila["frames"]
        try:
            for n in range(int(captura.get(cv2.CAP_PROP_FRAME_COUNT)) or 2**31):
                t = time.perf_counter()
                ok, imagen = captura.read()
                if not ok:
                    break
                ref = etiquetas.get(str(n))
                if detector is None and ref is None:
                    anterior = None
                    if vista_previa:
                        vista_previa = mostrar(ventana, imagen, [], None)
                    continue
                cajas = detector(imagen) if detector else [p["bbox"] for p in ref]
                candidatos = [(b, identificador.distancia(recortar(imagen,b))) for b in cajas]
                indice = elegir(candidatos, cfg["umbral"], cfg.get("margen", 0),
                               anterior if cfg.get("asociacion") else None)
                anterior = cajas[indice] if indice is not None else None
                ms = (time.perf_counter()-t)*1000
                rss = max(rss, proceso.memory_info().rss)
                resultados.append({"secuencia":fila["id"], "escenario":fila["escenario"],
                    "frame":n, "objetivo":fila["objetivo"], "referencia":ref,
                    "candidatos":candidatos, "seleccion":indice, "ms":ms})
                if vista_previa:
                    vista_previa = mostrar(ventana, imagen, cajas, indice)
        finally:
            captura.release()
            if vista_previa:
                cv2.destroyWindow(ventana)
    if not resultados:
        raise ValueError("La corrida no produjo fotogramas")
    grupos = defaultdict(lambda: defaultdict(int))
    for r in resultados:
        ref = r["referencia"]
        if ref is None:
            continue
        grupo = grupos[r["escenario"]]
        objetivo = r["objetivo"]
        presente = any(p["id"] == objetivo for p in ref)
        grupo["visibles" if presente else "ausentes"] += 1
        cajas = [c[0] for c in r["candidatos"]]
        blancos = [p["bbox"] for p in ref if p["id"] == objetivo]
        grupo["objetivo_detectado"] += int(any(iou(b, a) >= .5 for b in cajas for a in blancos))
        disponibles = list(ref)
        for b in cajas:
            mejor = max(disponibles, key=lambda p: iou(p["bbox"], b), default=None)
            if mejor is not None and iou(mejor["bbox"], b) >= .5:
                disponibles.remove(mejor)
            else:
                grupo["falsos_positivos_detector"] += 1
        seleccionado = r["seleccion"]
        if seleccionado is None:
            grupo["rechazos"] += int(presente)
            continue
        caja = r["candidatos"][seleccionado][0]
        coincidencia = max(ref, key=lambda p: iou(p["bbox"], caja), default=None)
        identidad = (coincidencia["id"] if coincidencia and
                     iou(coincidencia["bbox"], caja) >= .5 else None)
        grupo["correctos"] += int(presente and identidad == objetivo)
        grupo["sustituciones_frames"] += int(identidad is not None and identidad != objetivo)
        grupo["falsas_aceptaciones"] += int(not presente)
        grupo["selecciones_incorrectas_visibles"] += int(presente and identidad != objetivo)
    duracion = time.perf_counter()-inicio
    resumen = {"escenarios":grupos, "p50_ms":float(np.percentile([r["ms"] for r in resultados],50)),
        "p95_ms":float(np.percentile([r["ms"] for r in resultados],95)),
        "fps":len(resultados)/duracion,
        "cpu_pct_proceso":100*(sum(proceso.cpu_times()[:2])-cpu_inicio)/duracion,
        "rss_max_muestreada_bytes":rss, "so":platform.platform(), "cpu":platform.processor()}
    sensores = getattr(psutil, "sensors_temperatures", lambda: {})()
    resumen["temperaturas_finales_c"] = {k:[x.current for x in v] for k,v in sensores.items()}
    salida.mkdir(parents=True, exist_ok=False)
    (salida/"frames.jsonl").write_text("".join(json.dumps(r)+"\n" for r in resultados),encoding="utf-8")
    (salida/"resumen.json").write_text(json.dumps(resumen,indent=2)+"\n",encoding="utf-8")


def mostrar(ventana, imagen, cajas, indice):
    vista = imagen.copy()
    for i, (x, y, r, b) in enumerate(cajas):
        color = (0, 220, 0) if i == indice else (0, 180, 255)
        cv2.rectangle(vista, (x, y), (r - 1, b - 1), color, 2)
    estado = "Objetivo seleccionado" if indice is not None else "Sin objetivo"
    cv2.putText(vista, estado + " | Q: cerrar vista", (8, 24),
                cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 2)
    cv2.imshow(ventana, vista)
    tecla = cv2.waitKey(1) & 0xff
    visible = cv2.getWindowProperty(ventana, cv2.WND_PROP_VISIBLE) >= 1
    if tecla in (ord("q"), 27) and visible:
        cv2.destroyWindow(ventana)
        return False
    return visible


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifiesto", type=Path)
    parser.add_argument("configuracion", type=Path)
    parser.add_argument("salida", type=Path)
    parser.add_argument("--split", choices=["calibracion","evaluacion"], required=True)
    parser.add_argument("--vista-previa", action="store_true",
                        help="Mostrar el vídeo y las detecciones en una ventana local")
    args = parser.parse_args()
    if args.vista_previa:
        import os
        import sys
        if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            parser.error("La vista previa requiere una sesión gráfica")
        if not cv2.currentUIFramework():
            parser.error("Instala opencv-python en lugar de opencv-python-headless")
    filas = cargar(args.manifiesto)
    cfg = json.loads(args.configuracion.read_text(encoding="utf-8"))
    base = args.manifiesto.parent
    cv2.setNumThreads(cfg.get("hilos", 1))
    muestras = []
    for rel in cfg["galeria"]:
        imagen = cv2.imread(str(base / rel))
        if imagen is None:
            raise ValueError(f"No se pudo cargar el recorte: {rel}")
        muestras.append(imagen)
    destino = args.salida.resolve()
    local = Path("datos/procesados").resolve()
    if not destino.is_relative_to(local) or destino == local:
        parser.error("Usar un subdirectorio nuevo de datos/procesados para la salida")
    identificador = Identificador(muestras, cfg, base)
    detector = Detector(cfg["detector"], base) if cfg.get("detector") else None
    ejecutar(filas, args.split, base, cfg, identificador, detector, destino, args.vista_previa)
    (destino/"corrida.json").write_text(json.dumps({
        "config":cfg, "split":args.split, "vista_previa":args.vista_previa,
        "manifiesto_sha256":hashlib.sha256(args.manifiesto.read_bytes()).hexdigest(),
        "opencv":cv2.__version__, "numpy":np.__version__,
    },indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()

