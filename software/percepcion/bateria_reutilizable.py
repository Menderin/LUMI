"""Ejecuta D0/E1 con una sesion etiquetada o cache existente, sin camara ni GUI."""
import argparse
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from threadpoolctl import threadpool_limits

from .agregacion_galeria import PERFIL_AGREGACION
from .comparar_sesion import (PERFILES_MEJORA_PCA, calibrar, comprobar_cache, evaluar,
                             leer, preparar, sha256)
from .diagnosticar_sesion import diagnosticar
from .guiada import informe, validar_anotaciones
from .practica import REPO, guardar_json


def identificar(origen):
    origen = Path(origen).resolve()
    if (origen/"cache-completa/cache.json").is_file():
        return "cache", origen/"cache-completa"
    if (origen/"cache.json").is_file():
        return "cache", origen
    if (origen/"guia.json").is_file():
        return "sesion", origen
    raise ValueError("Indica una sesion guiada con guia.json o una bateria/cache con cache.json. "
                     "Los videos de servidor_movil sin clips etiquetados no son aun una bateria comparable.")


def validar_particiones(cache, permitir_sin_distractores):
    frames = cache.get("frames",[])
    partes = {}
    for split in ("calibracion","evaluacion"):
        filas = [r for r in frames if r["split"]==split]
        if not filas:
            raise ValueError(f"Faltan frames revisados de {split}")
        partes[split] = {r["secuencia"] for r in filas}
        claves = [(r["secuencia"],r["frame"]) for r in filas]
        if len(claves)!=len(set(claves)):
            raise ValueError("Frames duplicados en una particion")
    if partes["calibracion"] & partes["evaluacion"]:
        raise ValueError("Fuga: una secuencia aparece en calibracion y evaluacion")
    if cache.get("enrolamiento_sha256") in partes["calibracion"] | partes["evaluacion"]:
        raise ValueError("Fuga: video de enrolamiento usado como prueba")
    negativo = cache.get("negativa_origen",{}).get("video_sha256")
    if negativo and negativo in partes["calibracion"] | partes["evaluacion"]:
        raise ValueError("Fuga: galeria negativa usada como prueba")
    for split in partes:
        hay = any(p["id"]!=r["objetivo"] for r in frames if r["split"]==split for p in r["referencia"])
        if not hay and not permitir_sin_distractores:
            raise ValueError(f"{split} sin distractores: usa --permitir-sin-distractores solo para piloto exploratorio sin ganador")
    return partes


def preparar_sesion(origen, destino, *, cnn, mejorar_pca):
    guia = leer(origen/"guia.json")
    if not guia.get("terminada") or guia.get("cancelada"):
        raise ValueError("Sesion incompleta; termina primero captura/revision con guiada --continuar")
    videos = []
    for clip in guia["clips"]:
        video = (origen/clip["video"]).resolve()
        if not video.is_relative_to(origen):
            raise ValueError("Video fuera de la sesion")
        validar_anotaciones(video.with_suffix(".anotaciones.json"),clip["split"],clip["escenario"])
        if not video.is_file():
            raise ValueError(f"Falta el video original: {video}")
        videos.append(video)
    galeria = (origen/guia["galeria"]).resolve()
    if not galeria.is_relative_to(origen):
        raise ValueError("Galeria fuera de la sesion")
    preparar(galeria,destino,videos,cnn=cnn,comparar_galeria=True,
             perfiles_pca=PERFILES_MEJORA_PCA if mejorar_pca else None)
    return guia


def commit_actual():
    try:
        return subprocess.run(["git","rev-parse","HEAD"],cwd=REPO,capture_output=True,
                              text=True,timeout=5,check=True).stdout.strip()
    except (OSError,subprocess.SubprocessError):
        return None


def ejecutar(origen, salida=None, *, repeticiones=3, cnn=None, mejorar_pca=False,
             permitir_sin_distractores=False, datos_sinteticos=False):
    if repeticiones<1:
        raise ValueError("Repeticiones debe ser al menos1")
    tipo,fuente = identificar(origen)
    salida = Path(salida).resolve() if salida else REPO/"datos/procesados"/datetime.now().strftime("experimentos-D0-E1-%Y%m%d-%H%M%S-%f")
    if salida.exists() or salida.is_relative_to(fuente):
        raise ValueError("Usa una carpeta nueva fuera de la fuente para conservar los datos")
    salida.mkdir(parents=True)
    ficha = {"estado":"en_curso","fecha_utc":datetime.now(timezone.utc).isoformat(),
             "fuente":str(fuente),"tipo_fuente":tipo,"datos_sinteticos":datos_sinteticos,
             "repeticiones":repeticiones,"commit":commit_actual(),
             "sistema":platform.platform(),"cpu":platform.processor(),"python":platform.python_version(),
             "versiones":{"opencv":cv2.__version__,"numpy":np.__version__},
             "permitir_sin_distractores":permitir_sin_distractores,
             "camara_abierta":False,"movimiento_habilitado":False,
             "codigo_sha256":{name:sha256(Path(__file__).with_name(name)) for name in
                 ("bateria_reutilizable.py","diagnosticar_sesion.py","comparar_sesion.py",
                  "guiada.py","experimentos.py","agregacion_galeria.py","reid_openvino.py")}}
    guardar_json(salida/"ejecucion.json",ficha)
    cv2.setNumThreads(1)
    try:
        cache_dir = salida/"cache-completa"
        if tipo=="sesion":
            print("Preparando recortes desde videos y etiquetas existentes; sin abrir camara...",flush=True)
            ficha["fuente_sha256"] = sha256(fuente/"guia.json")
            preparar_sesion(fuente,cache_dir,cnn=cnn,mejorar_pca=mejorar_pca)
        else:
            print("Reutilizando cache; no necesita videos originales ni volver a etiquetar...",flush=True)
            ficha["fuente_sha256"] = sha256(fuente/"cache.json")
            shutil.copytree(fuente,cache_dir)
            cache = leer(cache_dir/"cache.json")
            cache["agregacion_galeria"] = PERFIL_AGREGACION
            if mejorar_pca:
                cache["perfiles_pca"] = {**cache.get("perfiles_pca",{}),**PERFILES_MEJORA_PCA}
            if cnn:
                cache["cnn"] = cnn
            guardar_json(cache_dir/"cache.json",cache)
        cache = leer(cache_dir/"cache.json")
        comprobar_cache(cache_dir,cache)
        validar_particiones(cache,permitir_sin_distractores)
        # Incluso en piloto autorizado se conserva aviso si falta distractor en cualquiera de las particiones.
        solo = permitir_sin_distractores or any(not any(p["id"]!=r["objetivo"] for r in cache["frames"]
            if r["split"]==split for p in r["referencia"]) for split in ("calibracion","evaluacion"))
        cfg = salida/"umbrales.json"
        corridas = []
        with threadpool_limits(limits=2):
            print("Calibrando umbral y margen propios con SOLO calibracion...",flush=True)
            calibrar(cache_dir,cfg,permitir_sin_distractores=solo)
            firma = sha256(cfg)
            for i in range(repeticiones):
                corrida = salida/f"repeticion-{i+1:02}"
                print(f"Evaluando D0/E1: repeticion{i+1}/{repeticiones}",flush=True)
                evaluar(cache_dir,cfg,corrida)
                if sha256(cfg)!=firma:
                    raise ValueError("Los umbrales cambiaron durante evaluacion")
                corridas.append(corrida)
            informe(salida,corridas,solo)
        if datos_sinteticos:
            for carpeta in [salida]+corridas:
                ruta = carpeta/"recomendacion.json"
                rec = leer(ruta)
                rec.update(candidato=None,datos_sinteticos=True,
                           alcance="Validacion de software con imagenes artificiales, no identidad humana")
                guardar_json(ruta,rec)
            ruta_informe = salida/"informe.md"
            texto = ruta_informe.read_text(encoding="utf-8")
            texto = "\n".join("Candidata humana: no seleccionada (datos sinteticos)." if l.startswith("Candidata del piloto:") else l
                              for l in texto.splitlines())
            ruta_informe.write_text("**VALIDACION CON DATOS SINTETICOS; NO SON RESULTADOS DEL LABORATORIO.**\n\n"+texto+"\n",encoding="utf-8")
        diagnosticar(corridas[0],salida/"diagnostico-D0")
        ficha.update(estado="completa",cache_sha256=sha256(cache_dir/"cache.json"),
                     umbrales_sha256=firma,piloto_sin_distractores=solo,
                     metodos=list(leer(cfg)["metodos"]),pendientes=leer(cfg).get("pendientes",{}))
        guardar_json(salida/"ejecucion.json",ficha)
        with (salida/"informe.md").open("a",encoding="utf-8") as f:
            f.write("\n## D0 y trazabilidad\n\nVer diagnostico-D0/informe.md, frames.csv y por-escenario.csv. "
                    "ejecucion.json identifica entorno, commit y datos de entrada. No se modificaron los originales.\n")
            if datos_sinteticos:
                f.write("\n**DATOS SINTETICOS: valida software; no mide reconocimiento de personas reales.**\n")
        print(f"INFORME: {salida/'informe.md'}\nE1: {salida/'comparacion-galeria.csv'}\nD0: {salida/'diagnostico-D0/informe.md'}",flush=True)
        return salida
    except BaseException as error:
        ficha.update(estado="interrumpida" if isinstance(error,KeyboardInterrupt) else "fallida",error=str(error))
        guardar_json(salida/"ejecucion.json",ficha)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("origen",type=Path,help="Sesion guiada etiquetada, bateria anterior o cache-completa")
    parser.add_argument("--repeticiones",type=int,default=3)
    parser.add_argument("--cnn",action="store_true",help="Incluir CNN0288 con pesos locales verificados")
    parser.add_argument("--modelo-cnn",type=Path)
    parser.add_argument("--descargar-cnn",action="store_true")
    parser.add_argument("--mejorar-pca",action="store_true",help="Conservar tambien las variantes ecualizadas")
    parser.add_argument("--permitir-sin-distractores",action="store_true",help="Piloto exploratorio; no elige ganador de identidad")
    parser.add_argument("--datos-sinteticos",action="store_true",help="Marcar explicitamente una prueba de software sin personas reales")
    args = parser.parse_args()
    try:
        cnn = None
        if args.cnn or args.modelo_cnn or args.descargar_cnn:
            from .reid_openvino import configuracion, descargar
            ruta = args.modelo_cnn
            if args.descargar_cnn:
                ruta = descargar(ruta.parent) if ruta else descargar()
            cnn = configuracion(ruta)
        ejecutar(args.origen,repeticiones=args.repeticiones,cnn=cnn,mejorar_pca=args.mejorar_pca,
                 permitir_sin_distractores=args.permitir_sin_distractores,datos_sinteticos=args.datos_sinteticos)
    except (ValueError,OSError,KeyError,RuntimeError,ImportError,cv2.error) as error:
        parser.exit(1,f"Error: {error}\nNo se abrio camara ni se modificaron las capturas originales.\n")


if __name__ == "__main__":
    main()
