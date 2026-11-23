"""Comparacion de identificadores con detecciones compartidas y etiquetas humanas."""
import argparse
import csv
import hashlib
import json
import shutil
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import psutil

from .experimentos import crear_identificadores, guardar_representacion, iou, recortar
from .practica import guardar_json, resolver

PERFILES_MEJORA_PCA = {"eqhist":{"alto":128,"preproceso":"eqhist","componentes":8}}


def sha256(ruta):
    h = hashlib.sha256()
    with Path(ruta).open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def leer(ruta):
    return json.loads(Path(ruta).read_text(encoding="utf-8-sig"))


def firma_calibracion(cache):
    contenido = {"galeria_sha256": cache["galeria_sha256"],
                 "frames": [r for r in cache["frames"] if r["split"] == "calibracion"]}
    if cache.get("perfiles_pca"):
        contenido["perfiles_pca"] = cache["perfiles_pca"]
    if cache.get("negativa_sha256"):
        contenido["negativa_sha256"] = cache["negativa_sha256"]
    return hashlib.sha256(json.dumps(contenido, sort_keys=True).encode()).hexdigest()


def agregar_negativa(cache_dir, cache, galeria):
    ficha = leer(galeria / "galeria.json")
    if not ficha.get("aprobada") or not 8 <= len(ficha["imagenes"]) <= 24:
        raise ValueError("La galeria negativa debe estar aprobada y tener 8-24 recortes de OTRA persona")
    origen_video = galeria.parent / f"enrolamiento-{ficha['intento']}.avi"
    marca_video = sha256(origen_video)
    if marca_video == cache.get("enrolamiento_sha256"):
        raise ValueError("La galeria negativa usa el mismo video de enrolamiento del objetivo")
    if marca_video in {v["sha256"] for v in cache["videos"]}:
        raise ValueError("La galeria negativa proviene de calibracion/evaluacion")
    archivos = []
    for nombre in ficha["imagenes"]:
        ruta = (galeria / nombre).resolve()
        if ruta.parent != galeria.resolve():
            raise ValueError("Recorte negativo fuera de su galeria")
        marca = sha256(ruta)
        if marca in cache["galeria_sha256"]:
            raise ValueError("La clase negativa contiene un recorte del objetivo")
        archivos.append((ruta,marca))
    destino=cache_dir/"galeria-negativa"
    destino.mkdir()
    for i,(ruta,_) in enumerate(archivos):
        shutil.copyfile(ruta,destino/f"{i:02}.png")
    cache["negativa_sha256"] = [marca for _,marca in archivos]
    cache["negativa_origen"] = {"galeria":str(galeria),"video_sha256":marca_video,
                               "rol":"otra persona declarada por el operador"}


def clonar_con_negativa(cache_dir, galeria_negativa, salida):
    if salida.exists():
        raise ValueError("Usa una carpeta de cache nueva")
    cache=leer(cache_dir/"cache.json")
    comprobar_cache(cache_dir,cache)
    if cache.get("negativa_sha256"):
        raise ValueError("La cache ya tiene clase negativa")
    shutil.copytree(cache_dir,salida)
    agregar_negativa(salida,cache,galeria_negativa)
    guardar_json(salida/"cache.json",cache)


def clonar_con_mejoras(cache_dir, salida):
    if salida.exists():
        raise ValueError("Usa una cache de salida nueva")
    cache=leer(cache_dir/"cache.json")
    comprobar_cache(cache_dir,cache)
    shutil.copytree(cache_dir,salida)
    cache["perfiles_pca"]=PERFILES_MEJORA_PCA
    guardar_json(salida/"cache.json",cache)


def preparar(galeria, salida, videos, *, galeria_negativa=None, perfiles_pca=None):
    if salida.exists():
        raise ValueError("La salida debe ser nueva para conservar corridas anteriores")
    ficha = leer(galeria / "galeria.json")
    if not ficha.get("aprobada") or not 8 <= len(ficha["imagenes"]) <= 24:
        raise ValueError("Se requiere galeria revisada de 8 a 24 recortes (galerias anteriores compatibles)")
    # Validar particiones por contenido, no solo por nombre de archivo.
    videos_info = []
    vistos = set()
    enrolamiento = galeria.parent / f"enrolamiento-{ficha['intento']}.avi"
    marca_enrolamiento=sha256(enrolamiento)
    vistos.add(marca_enrolamiento)
    for video in videos:
        marca = sha256(video)
        if marca in vistos:
            raise ValueError("Video repetido o de enrolamiento en calibracion/evaluacion")
        vistos.add(marca)
        anotaciones = leer(video.with_suffix(".anotaciones.json"))
        if anotaciones["split"] not in ("calibracion", "evaluacion"):
            raise ValueError("Particion invalida")
        if not anotaciones["frames"]:
            raise ValueError(f"Sin frames revisados: {video}")
        videos_info.append((video, marca, anotaciones))
    salida.mkdir(parents=True)
    destino_galeria = salida / "galeria"
    destino_galeria.mkdir()
    hashes = []
    for i, nombre in enumerate(ficha["imagenes"]):
        original = galeria / nombre
        if original.parent.resolve() != galeria.resolve():
            raise ValueError("Ruta de recorte fuera de la galeria")
        hashes.append(sha256(original))
        shutil.copyfile(original, destino_galeria / f"{i:02}.png")
    cache = {"galeria_sha256": hashes, "enrolamiento_sha256":marca_enrolamiento,
             "frames": [], "videos": [],
             "versiones": {"opencv": cv2.__version__, "numpy": np.__version__}}
    for video, marca, anotaciones in videos_info:
        with (video.parent / "decisiones.csv").open(encoding="utf-8-sig", newline="") as archivo:
            decisiones = {int(r["frame_clip"]): r for r in csv.DictReader(archivo)
                          if r["clip"] == video.name and r["frame_clip"] != ""}
        captura = cv2.VideoCapture(str(video))
        if not captura.isOpened():
            raise ValueError(f"No se puede abrir {video}")
        pendientes = set(anotaciones["frames"])
        try:
            indice = 0
            while True:
                ok, frame = captura.read()
                if not ok:
                    break
                if str(indice) in pendientes:
                    pendientes.remove(str(indice))
                    if indice not in decisiones or "detector_ms" not in decisiones[indice]:
                        raise ValueError("Faltan tiempos/detecciones; graba el clip con la practica actualizada")
                    r = decisiones[indice]
                    referencia = anotaciones["frames"][str(indice)]
                    if not isinstance(referencia, list):
                        raise ValueError("Referencia debe listar personas revisadas; [] significa escena vacia")
                    for persona in referencia:
                        recortar(frame, persona["bbox"])
                        if not isinstance(persona["id"], str) or not persona["id"]:
                            raise ValueError("Identidad de referencia invalida")
                    if sum(p["id"] == anotaciones["objetivo"] for p in referencia) > 1:
                        raise ValueError("Objetivo duplicado en referencia")
                    cajas = json.loads(r["cajas"])
                    candidatos = []
                    for caja in cajas:
                        imagen = recortar(frame, caja)
                        nombre = f"recortes/{len(cache['frames']):08}-{len(candidatos):03}.png"
                        destino = salida / nombre
                        destino.parent.mkdir(exist_ok=True)
                        if not cv2.imwrite(str(destino), imagen):
                            raise OSError("No se pudo guardar recorte")
                        candidatos.append({"bbox": caja, "imagen": nombre, "sha256": sha256(destino)})
                    cache["frames"].append({
                        "secuencia": marca, "frame": indice, "split": anotaciones["split"],
                        "escenario": anotaciones["escenario"], "objetivo": anotaciones["objetivo"],
                        "referencia": referencia, "candidatos": candidatos,
                        "tiempo_s": float(r["tiempo_monotonico_s"]), "detector_ms": float(r["detector_ms"]),
                    })
                indice += 1
            if pendientes:
                raise ValueError("Anotaciones fuera del video")
        finally:
            captura.release()
        config_origen = video.parent / "configuracion.json"
        cache["videos"].append({
            "sha256": marca, "origen": str(video), "split": anotaciones["split"],
            "configuracion_captura": leer(config_origen) if config_origen.exists() else None,
        })
    if perfiles_pca:
        cache["perfiles_pca"]=perfiles_pca
    if galeria_negativa is not None:
        agregar_negativa(salida,cache,galeria_negativa)
    guardar_json(salida / "cache.json", cache)



def comprobar_cache(cache_dir, cache):
    for i, esperado in enumerate(cache["galeria_sha256"]):
        if sha256(cache_dir / "galeria" / f"{i:02}.png") != esperado:
            raise ValueError("La galeria cambio despues de preparar")
    for i,esperado in enumerate(cache.get("negativa_sha256",[])):
        if sha256(cache_dir/"galeria-negativa"/f"{i:02}.png") != esperado:
            raise ValueError("La galeria negativa cambio despues de preparar")
    for r in cache["frames"]:
        for candidato in r["candidatos"]:
            ruta = (cache_dir / candidato["imagen"]).resolve()
            if not ruta.is_relative_to(cache_dir.resolve()) or sha256(ruta) != candidato["sha256"]:
                raise ValueError("Un recorte cambio despues de preparar")


def modelos(cache_dir, *, incidencias=None):
    muestras = [cv2.imread(str(ruta)) for ruta in sorted((cache_dir / "galeria").glob("*.png"))]
    if any(m is None for m in muestras):
        raise ValueError("Recorte de galeria ilegible")
    cache=leer(cache_dir/"cache.json")
    resultado = crear_identificadores(muestras,cache_dir,perfiles_pca=cache.get("perfiles_pca"))
    motivo = "Falta galeria aprobada de otra persona para la segunda clase"
    if cache.get("negativa_sha256"):
        from .cc_ppca import CCPPCA
        negativos=[cv2.imread(str(cache_dir/"galeria-negativa"/f"{i:02}.png"))
                   for i in range(len(cache["negativa_sha256"]))]
        if any(m is None for m in negativos):
            raise ValueError("Recorte de clase negativa ilegible")
        try:
            resultado["cc_ppca"]=CCPPCA(muestras,negativos)
            motivo=None
        except ValueError as error:
            motivo=str(error)
    if incidencias is not None and motivo:
        incidencias["cc_ppca"]=motivo
    return resultado


def puntuar(cache_dir, frames, modelo):
    proceso = psutil.Process()
    inicio_cpu = sum(proceso.cpu_times()[:2])
    inicio = time.perf_counter()
    salida = []
    rss = proceso.memory_info().rss
    for r in frames:
        t = time.perf_counter()
        distancias = []
        for candidato in r["candidatos"]:
            imagen = cv2.imread(str(cache_dir / candidato["imagen"]))
            if imagen is None:
                raise ValueError("Recorte de cache ilegible")
            distancias.append(float(modelo.distancia(imagen)))
        ms = (time.perf_counter() - t) * 1000
        salida.append({**r, "distancias": distancias, "identificacion_ms": ms})
        rss = max(rss, proceso.memory_info().rss)
    duracion = time.perf_counter() - inicio
    return salida, {
        "cpu_proceso_pct_total": 100 * (sum(proceso.cpu_times()[:2])-inicio_cpu)
                                 / max(duracion, 1e-9) / (psutil.cpu_count() or 1),
        "rss_max_bytes": rss, "duracion_s": duracion,
    }


def clasificar(r, indice):
    referencias = r["referencia"]
    blancos = [p["bbox"] for p in referencias if p["id"] == r["objetivo"]]
    visible = bool(blancos)
    detectado = any(iou(c["bbox"], b) >= .5 for c in r["candidatos"] for b in blancos)
    identidad = None
    if indice is not None:
        caja = r["candidatos"][indice]["bbox"]
        mejor = max(referencias, key=lambda p: iou(p["bbox"], caja), default=None)
        if mejor is not None and iou(mejor["bbox"], caja) >= .5:
            identidad = mejor["id"]
    correcto = indice is not None and visible and identidad == r["objetivo"]
    return {
        "visibles": int(visible), "ausentes": int(not visible), "revisados": 1,
        "objetivo_detectado": int(detectado),
        "perdidas_detector": int(visible and not detectado),
        "rechazos_identificador": int(visible and detectado and indice is None),
        "rechazos_totales": int(visible and indice is None),
        "correctos": int(correcto),
        "sustituciones_frames": int(indice is not None and identidad is not None and identidad != r["objetivo"]),
        "falsas_aceptaciones": int(indice is not None and not visible),
        "selecciones_incorrectas_visibles": int(indice is not None and visible and not correcto),
    }


def evaluar_puntuaciones(filas, umbral, margen):
    grupos = defaultdict(lambda: defaultdict(int))
    decisiones = []
    recuperaciones = []
    pendientes = {}
    for r in filas:
        indice, motivo = resolver(r["distancias"], umbral, margen)
        m = clasificar(r, indice)
        for clave, valor in m.items():
            grupos[r["escenario"]][clave] += valor
        seq = r["secuencia"]
        if m["correctos"] and seq in pendientes:
            recuperaciones.append(r["tiempo_s"] - pendientes.pop(seq))
        elif not m["correctos"]:
            pendientes.setdefault(seq, r["tiempo_s"])
        decisiones.append({**r, "seleccion": indice, "motivo": motivo, "metricas": m})
    peor = min((g["correctos"]/g["visibles"] for g in grupos.values() if g["visibles"]), default=0)
    return {"escenarios": dict(grupos), "peor_acierto_visible": peor,
            "recuperacion_muestreada_s": recuperaciones,
            "perdidas_sin_recuperacion": len(pendientes)}, decisiones


def elegir_parametros(filas, *, exigir_distractor=True):
    observados = [d for r in filas for d in r["distancias"] if np.isfinite(d)]
    rechazo_total = min(-1.,float(np.nextafter(min(observados),-np.inf))) if observados else -1.
    valores = [rechazo_total] + observados
    umbrales = np.unique(np.quantile(valores, np.linspace(0, 1, min(24, len(valores)))))
    diferencias = [sorted(r["distancias"])[1]-sorted(r["distancias"])[0]
                   for r in filas if len(r["distancias"]) >= 2]
    margenes = np.unique([0.] + (np.quantile(diferencias, np.linspace(0, 1, min(12, len(diferencias)))).tolist()
                                if diferencias else []))
    if not any(clasificar(r, None)["visibles"] for r in filas):
        raise ValueError("Calibracion sin objetivo visible")
    if not any(clasificar(r, None)["ausentes"] for r in filas):
        raise ValueError("Calibracion necesita escena vacia o distractor sin objetivo")
    if exigir_distractor and not any(p["id"] != r["objetivo"] for r in filas for p in r["referencia"]):
        raise ValueError("Calibracion necesita distractores anotados")
    mejor = None
    for umbral in umbrales:
        for margen in margenes:
            informe, _ = evaluar_puntuaciones(filas, float(umbral), float(margen))
            grupos = informe["escenarios"].values()
            errores = sum(g["sustituciones_frames"] + g["falsas_aceptaciones"]
                          + g["selecciones_incorrectas_visibles"] for g in grupos)
            if errores:
                continue
            correctos = sum(g["correctos"] for g in grupos)
            orden = (informe["peor_acierto_visible"], correctos, -float(umbral), -float(margen))
            if mejor is None or orden > mejor[0]:
                mejor = orden, float(umbral), float(margen)
    if mejor is None:
        raise ValueError("No se encontraron parametros sin falsas aceptaciones en calibracion")
    return {"umbral": mejor[1], "margen": mejor[2],
            "util": mejor[0][1] > 0, "peor_acierto_calibracion": mejor[0][0]}


def calibrar(cache_dir, destino, *, permitir_sin_distractores=False):
    cache = leer(cache_dir / "cache.json")
    comprobar_cache(cache_dir, cache)
    if destino.exists():
        raise ValueError("Usa un archivo nuevo para conservar la calibracion")
    frames = [r for r in cache["frames"] if r["split"] == "calibracion"]
    configuracion = {"piloto_sin_distractores": permitir_sin_distractores, "calibracion_sha256": firma_calibracion(cache),
                     "galeria_sha256": cache["galeria_sha256"], "metodos": {}}
    incidencias={}
    disponibles=modelos(cache_dir,incidencias=incidencias)
    configuracion["pendientes"]=incidencias
    configuracion["modelos"]={}
    for nombre, modelo in disponibles.items():
        configuracion["modelos"][nombre]=getattr(modelo,"metadata",{})
        filas, _ = puntuar(cache_dir, frames, modelo)
        configuracion["metodos"][nombre] = elegir_parametros(filas, exigir_distractor=not permitir_sin_distractores)
        guardar_representacion(modelo, cache_dir / f"{nombre}.npz")
    guardar_json(destino, configuracion)


def evaluar(cache_dir, configuracion, salida):
    cache = leer(cache_dir / "cache.json")
    comprobar_cache(cache_dir, cache)
    cfg = leer(configuracion)
    if cfg["calibracion_sha256"] != firma_calibracion(cache) or cfg["galeria_sha256"] != cache["galeria_sha256"]:
        raise ValueError("La calibracion no corresponde a los mismos datos y galeria")
    for i, esperado in enumerate(cache["galeria_sha256"]):
        if sha256(cache_dir / "galeria" / f"{i:02}.png") != esperado:
            raise ValueError("La galeria cambio despues de calibrar")
    frames = [r for r in cache["frames"] if r["split"] == "evaluacion"]
    if not frames:
        raise ValueError("Faltan frames de evaluacion")
    if salida.exists():
        raise ValueError("La salida debe ser nueva")
    salida.mkdir(parents=True)
    totales = []
    for nombre, motivo in cfg.get("pendientes",{}).items():
        guardar_json(salida/f"{nombre}.json",{"estado":"pendiente","motivo":motivo})
    disponibles=modelos(cache_dir)
    for nombre in cfg["metodos"]:
        if nombre not in disponibles:
            raise ValueError(f"Modelo calibrado no disponible: {nombre}")
        modelo=disponibles[nombre]
        filas, recursos = puntuar(cache_dir, frames, modelo)
        parametros = cfg["metodos"][nombre]
        informe, decisiones = evaluar_puntuaciones(filas, parametros["umbral"], parametros["margen"])
        total_ms = [r["identificacion_ms"]+r["detector_ms"] for r in filas]
        fallos = sum(g["sustituciones_frames"] for g in informe["escenarios"].values())
        for escenario, grupo in informe["escenarios"].items():
            ms_escenario = [r["identificacion_ms"] + r["detector_ms"] for r in filas if r["escenario"] == escenario]
            grupo["p95_detector_mas_identificacion_ms"] = float(np.percentile(ms_escenario, 95))
        informe.update(recursos)
        informe.update({
            "cache_sha256": sha256(cache_dir / "cache.json"),
            "versiones": {"opencv": cv2.__version__, "numpy": np.__version__},
            "modelo": getattr(modelo,"metadata",{}),
            "parametros": parametros, "configuracion_sha256": sha256(configuracion),
            "p50_detector_mas_identificacion_ms": float(np.percentile(total_ms, 50)),
            "p95_identificacion_ms": float(np.percentile([r["identificacion_ms"] for r in filas], 95)),
            "p95_detector_mas_identificacion_ms": float(np.percentile(total_ms, 95)),
            "descartado_integracion": fallos > 0 or not parametros["util"]
                or any(g["falsas_aceptaciones"] + g["selecciones_incorrectas_visibles"] > 0
                       for g in informe["escenarios"].values()),
        })
        guardar_json(salida / f"{nombre}.json", informe)
        with (salida / f"{nombre}-frames.jsonl").open("w", encoding="utf-8") as archivo:
            for r in decisiones:
                archivo.write(json.dumps(r) + "\n")
        contadores = {clave: sum(g[clave] for g in informe["escenarios"].values())
                      for clave in ("revisados", "visibles", "ausentes", "objetivo_detectado",
                                    "perdidas_detector", "rechazos_identificador", "rechazos_totales",
                                    "correctos", "sustituciones_frames", "falsas_aceptaciones",
                                    "selecciones_incorrectas_visibles")}
        totales.append({**contadores, "metodo": nombre, "descartado_integracion": informe["descartado_integracion"],
                        "peor_acierto_visible": informe["peor_acierto_visible"],
                        "p95_ms": informe["p95_detector_mas_identificacion_ms"], **recursos})
    totales.sort(key=lambda r: (r["descartado_integracion"], -r["peor_acierto_visible"],
                               r["p95_ms"], r["cpu_proceso_pct_total"], r["rss_max_bytes"]))
    with (salida / "comparacion.csv").open("w", newline="", encoding="utf-8") as archivo:
        tabla = csv.DictWriter(archivo, fieldnames=list(totales[0]))
        tabla.writeheader()
        tabla.writerows(totales)
    guardar_json(salida / "recomendacion.json", {
        "candidato": next((r["metodo"] for r in totales if not r["descartado_integracion"]
                           and r["peor_acierto_visible"] > 0), None)
                           if not cfg.get("piloto_sin_distractores") else None,
        "alcance": "Solo videos y frames revisados del piloto; requiere validacion fisica",
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="accion", required=True)
    preparar_cmd = comandos.add_parser("preparar")
    preparar_cmd.add_argument("galeria", type=Path)
    preparar_cmd.add_argument("salida", type=Path)
    preparar_cmd.add_argument("videos", type=Path, nargs="+")
    preparar_cmd.add_argument("--galeria-negativa",type=Path)
    preparar_cmd.add_argument("--mejorar-pca",action="store_true")
    mejorar_cmd=comandos.add_parser("con-mejoras-pca",help="Comparar originales y PCA ecualizados reutilizando cache")
    mejorar_cmd.add_argument("cache",type=Path)
    mejorar_cmd.add_argument("salida",type=Path)
    clonar_cmd=comandos.add_parser("con-negativos",help="Reutilizar cache existente sin volver a abrir videos")
    clonar_cmd.add_argument("cache",type=Path)
    clonar_cmd.add_argument("galeria_negativa",type=Path)
    clonar_cmd.add_argument("salida",type=Path)
    for nombre in ("calibrar", "evaluar"):
        comando = comandos.add_parser(nombre)
        comando.add_argument("cache", type=Path)
        comando.add_argument("configuracion", type=Path)
        if nombre == "calibrar":
            comando.add_argument("--permitir-sin-distractores",action="store_true",help="Piloto exploratorio sin ganador de identidad")
        if nombre == "evaluar":
            comando.add_argument("salida", type=Path)
    args = parser.parse_args()
    cv2.setNumThreads(1)
    from threadpoolctl import threadpool_limits
    limites = threadpool_limits(limits=2)
    try:
        if args.accion == "preparar":
            preparar(args.galeria.resolve(), args.salida.resolve(), [v.resolve() for v in args.videos],
                     galeria_negativa=args.galeria_negativa.resolve() if args.galeria_negativa else None,
                     perfiles_pca=PERFILES_MEJORA_PCA if args.mejorar_pca else None)
        elif args.accion == "con-mejoras-pca":
            clonar_con_mejoras(args.cache.resolve(),args.salida.resolve())
        elif args.accion == "con-negativos":
            clonar_con_negativa(args.cache.resolve(),args.galeria_negativa.resolve(),args.salida.resolve())
        elif args.accion == "calibrar":
            calibrar(args.cache.resolve(), args.configuracion.resolve(),
                     permitir_sin_distractores=args.permitir_sin_distractores)
        else:
            evaluar(args.cache.resolve(), args.configuracion.resolve(), args.salida.resolve())
    except (ValueError, OSError, KeyError, ImportError, cv2.error) as error:
        parser.exit(1, f"Error: {error}\n")
    finally:
        limites.restore_original_limits()


if __name__ == "__main__":
    main()
