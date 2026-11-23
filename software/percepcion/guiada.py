"""Una captura guiada, anotacion humana y comparacion de tres identificadores."""
import argparse
import csv
import json
import math
import statistics
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import cv2
from threadpoolctl import threadpool_limits

from .anotar_practica import anotar
from .comparar_sesion import preparar, calibrar, evaluar, leer
from .practica import REPO, practica, guardar_json

ESCENAS = [
    ("frente-perfiles", "Camina y gira: frente, espalda y perfiles", 10),
    ("oclusion", "Ocultate tras la silla y vuelve a aparecer", 10),
    ("ausente", "Sal del encuadre y deja la escena vacia", 6),
    ("distractor", "Solo el acompanante en escena; objetivo fuera", 8),
    ("cruce", "Ambos visibles: cruzarse y separarse", 10),
]


class Guia:
    def __init__(self, carpeta, solo=False):
        self.carpeta = carpeta
        self.solo = solo
        self.pasos = [
            {"split": split, "escenario": nombre, "instruccion": texto, "duracion_s": duracion}
            for split in ("calibracion", "evaluacion")
            for nombre, texto, duracion in ESCENAS
            if not solo or nombre not in ("distractor", "cruce")
        ]
        self.indice = 0
        self.fase = "espera"
        self.inicio = None
        self.video = None
        self.galeria = None
        self.clips = []
        self.terminada = False
        self.cancelada = False
        self.enrolada = False

    def guardar(self):
        guardar_json(self.carpeta / "guia.json", {
            "solo": self.solo, "galeria": self.galeria, "clips": self.clips,
            "terminada": self.terminada, "cancelada": self.cancelada,
        })

    def actualizar(self, ahora, estado, intentos, clip, tecla):
        self.enrolada = estado in ("listo","siguiendo","perdido")
        if tecla == 27:
            self.cancelada = True
            self.guardar()
            return tecla
        if self.indice == 0 and self.fase == "espera" and self.galeria is None:
            if estado not in ("listo", "siguiendo", "perdido"):
                return tecla
        elif self.galeria and (f"galeria-{intentos}" != self.galeria or tecla in (ord("c"),ord("r"))):
            self.cancelada = True
            self.guardar()
            return 27
        paso = self.pasos[self.indice]
        if self.fase == "espera" and tecla == ord("n") and estado in ("listo","siguiendo","perdido"):
            self.galeria = f"galeria-{intentos}"
            self.fase = "cuenta"
            self.inicio = ahora + 3
            self.guardar()
        elif self.fase == "cuenta" and ahora >= self.inicio:
            self.fase = "abriendo"
            return ord("v")
        elif self.fase == "abriendo" and clip is not None:
            self.video = clip.ruta.name
            self.inicio = ahora
            self.fase = "grabando"
        elif self.fase == "grabando" and ahora - self.inicio >= paso["duracion_s"]:
            self.fase = "cerrando"
            return ord("v")
        elif self.fase == "cerrando" and clip is None:
            self.clips.append({**paso, "video": self.video})
            self.indice += 1
            self.fase = "espera"
            self.video = None
            if self.indice == len(self.pasos):
                self.terminada = True
                self.guardar()
                return 27
            self.guardar()
        # V esta reservado al guion para que el clip dure lo programado.
        return -1 if tecla in (ord("n"),ord("v")) else tecla

    def textos(self, ahora):
        if self.terminada:
            return ["Captura completa. Continua la revision humana."]
        if not self.enrolada and self.galeria is None and self.fase == "espera":
            return ["BATERIA GUIADA: pulsa E, gira 12 s y aprueba el enrolamiento",
                    "Luego N / Paso comienza cada escena. Esc cancela."]
        paso = self.pasos[self.indice]
        prefijo = f"{self.indice+1}/{len(self.pasos)} {paso['split']} - {paso['escenario']}"
        if self.fase == "cuenta":
            prefijo += f" | PREPARATE {math.ceil(max(0,self.inicio-ahora))}"
        elif self.fase in ("grabando","abriendo"):
            restante = max(0, paso["duracion_s"] - (ahora-self.inicio)) if self.fase == "grabando" else paso["duracion_s"]
            prefijo += f" | GRABANDO {math.ceil(restante)}s"
        else:
            prefijo += " | N / Paso para comenzar"
        return [prefijo, paso["instruccion"]]


def validar_anotaciones(ruta, split, escenario):
    if not ruta.exists():
        raise ValueError("No se guardaron etiquetas. Usa S o Revisar; N solo omite. Retoma con --continuar")
    datos = leer(ruta)
    if datos["split"] != split or datos["escenario"] != escenario or not datos["frames"]:
        raise ValueError(f"Faltan anotaciones revisadas: {ruta}")
    refs = list(datos["frames"].values())
    visible = any(any(p["id"] == "objetivo" for p in personas) for personas in refs)
    otro = any(any(p["id"] != "objetivo" for p in personas) for personas in refs)
    if escenario in ("frente-perfiles","oclusion") and not visible:
        raise ValueError(f"No se reviso al objetivo en {ruta}")
    if escenario == "ausente" and not any(not personas for personas in refs):
        raise ValueError(f"No se reviso una escena vacia en {ruta}")
    if escenario == "distractor" and not any(
        personas and all(p["id"] != "objetivo" for p in personas) for personas in refs
    ):
        raise ValueError(f"Falta distractor sin objetivo en {ruta}")
    if escenario == "cruce" and not any(
        any(p["id"] == "objetivo" for p in personas)
        and any(p["id"] != "objetivo" for p in personas) for personas in refs
    ):
        raise ValueError(f"Falta un frame revisado con ambas personas en {ruta}")


VENTAJAS = {
    "histograma": (
        "Descriptor de color sencillo; permite inspeccionar que colores se comparan.",
        "Ropa similar, fondo e iluminacion pueden producir confusiones.",
    ),
    "euclidea": (
        "Comparacion sencilla en un espacio PCA reducido; referencia util de bajo coste.",
        "PCA representa variacion visual; pose, luz y fondo pueden dominar sobre identidad.",
    ),
    "mahalanobis": (
        "Pondera diferencias segun la covarianza regularizada de la galeria.",
        "La covarianza de una sola sesion puede representar mal otras luces y poses.",
    ),
}


def informe(salida, corridas, solo):
    por_metodo = {}
    selecciones = {}
    equivalentes = True
    for corrida in corridas:
        with (corrida / "comparacion.csv").open(encoding="utf-8",newline="") as archivo:
            for fila in csv.DictReader(archivo):
                por_metodo.setdefault(fila["metodo"],[]).append(fila)
        for nombre in VENTAJAS:
            with (corrida / f"{nombre}-frames.jsonl").open(encoding="utf-8") as archivo:
                decisiones = [(r["secuencia"],r["frame"],r["seleccion"]) for r in map(json.loads,archivo)]
            if nombre in selecciones and selecciones[nombre] != decisiones:
                equivalentes = False
            selecciones[nombre] = decisiones
    agregados = []
    for nombre, filas in por_metodo.items():
        fila = dict(filas[0])
        for clave in ("p95_ms","cpu_proceso_pct_total","duracion_s"):
            fila[clave] = statistics.median(float(r[clave]) for r in filas)
        fila["rss_max_bytes"] = max(int(r["rss_max_bytes"]) for r in filas)
        fila["repeticiones"] = len(filas)
        fila["ventaja_teorica"], fila["limitacion_teorica"] = VENTAJAS[nombre]
        agregados.append(fila)
    agregados.sort(key=lambda r: (
        r["descartado_integracion"] == "True",
        -float(r["peor_acierto_visible"]),float(r["p95_ms"]),
        float(r["cpu_proceso_pct_total"]),int(r["rss_max_bytes"]),
    ))
    with (salida / "comparacion.csv").open("w",encoding="utf-8",newline="") as archivo:
        writer=csv.DictWriter(archivo,fieldnames=list(agregados[0]))
        writer.writeheader()
        writer.writerows(agregados)
    candidato = next((r["metodo"] for r in agregados if r["descartado_integracion"] == "False"
                      and float(r["peor_acierto_visible"]) > 0),None) if not solo and equivalentes else None
    guardar_json(salida/"recomendacion.json",{
        "candidato":candidato,"solo":solo,"decisiones_equivalentes":equivalentes,
        "alcance":"Piloto de apariencia en la iluminacion capturada; faltan otras luces y validacion fisica",
    })
    lineas = ["# Resultados de la bateria guiada", "",
              f"Repeticiones por metodo: {len(corridas)}. Decisiones equivalentes: {equivalentes}.",
              "", "**Piloto sin distractores: no permite elegir ganador de identidad.**" if solo
              else "Se incluyeron escenas con distractores revisadas por el operador.", "",
              f"Candidata del piloto: {candidato or 'ninguna seleccionada'}.", "",
              "| Metodo | Aciertos / visibles | Falsas acept. / ausentes | Sustituciones (frames) | Peor acierto | p95 ms* | CPU identificador % | RSS MiB |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in agregados:
        lineas.append(
            f"| {r['metodo']} | {r['correctos']}/{r['visibles']} | {r['falsas_aceptaciones']}/{r['ausentes']} | "
            f"{r['sustituciones_frames']} | {float(r['peor_acierto_visible']):.1%} | "
            f"{float(r['p95_ms']):.1f} | {float(r['cpu_proceso_pct_total']):.1f} | {int(r['rss_max_bytes'])/2**20:.1f} |"
        )
    lineas += ["", "*p95 suma el tiempo de deteccion guardado y la identificacion offline. No mide camara-pantalla.",
               "CPU/RSS corresponden al proceso offline. El consumo completo de captura esta en recursos.csv.",
               "Los fotogramas omitidos no entran en los denominadores. Revisar cada JSON por escenario.",
               "Repetir el mismo video verifica estabilidad, sin aumentar el numero de participantes ni tomas.",
               "Las ventajas y limitaciones siguientes son teoricas; comprobarlas con estos resultados.", ""]
    for nombre,(ventaja,limitacion) in VENTAJAS.items():
        lineas += [f"## {nombre}", "", f"Ventaja: {ventaja}", "", f"Limitacion: {limitacion}", ""]
    lineas += ["## Pendientes", "",
               "Validar transiciones interior/exterior, participantes adicionales y funcionamiento fisico.",
               "Las intenciones de direccion del piloto son simuladas.",
               "Si las tres alternativas fallan, comparar un encoder Re-ID con los mismos datos."]
    (salida/"informe.md").write_text("\n".join(lineas)+"\n",encoding="utf-8")


def analizar(carpeta, repeticiones=3, paso=5, anotador=anotar):
    guia = leer(carpeta/"guia.json")
    if not guia["terminada"] or guia["cancelada"]:
        raise ValueError("Captura incompleta. Los archivos se conservaron; falta completar la bateria")
    solo = guia["solo"]
    galeria = carpeta/guia["galeria"]
    marca = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    salida = REPO/"datos/procesados"/f"bateria-guiada-{marca}"
    salida.mkdir(parents=True)
    guardar_json(salida/"sesion.json", {"origen":str(carpeta),"guia":guia,"repeticiones":repeticiones,"paso_revision":paso})
    videos = {}
    with threadpool_limits(limits=2):
        # No se usa la evaluacion para elegir umbrales.
        for split in ("calibracion","evaluacion"):
            videos[split] = []
            for clip in guia["clips"]:
                if clip["split"] != split:
                    continue
                video = carpeta/clip["video"]
                print(f"REVISAR {split}: {clip['instruccion']}",flush=True)
                paso_clip = paso
                completa = anotador(video,split,clip["escenario"],paso_clip)
                if completa is False:
                    raise ValueError("Revision incompleta o sin etiquetas. Usa S / Enter / Revisar para etiquetar; N omite. Retoma con --continuar")
                validar_anotaciones(video.with_suffix(".anotaciones.json"),split,clip["escenario"])
                videos[split].append(video)
            if not videos[split]:
                raise ValueError(f"Faltan clips de {split}")
            if split == "calibracion":
                preparar(galeria,salida/"cache-calibracion",videos[split])
                calibrar(salida/"cache-calibracion",salida/"umbrales.json",
                         permitir_sin_distractores=solo)
                print("Parametros congelados. Ahora revisaremos la evaluacion.",flush=True)
        preparar(galeria,salida/"cache-completa",videos["calibracion"]+videos["evaluacion"])
        corridas = []
        for i in range(repeticiones):
            corrida = salida/f"repeticion-{i+1:02}"
            print(f"Comparando los tres metodos: repeticion {i+1}/{repeticiones}",flush=True)
            evaluar(salida/"cache-completa",salida/"umbrales.json",corrida)
            corridas.append(corrida)
        informe(salida,corridas,solo)
    print(f"INFORME: {salida/'informe.md'}",flush=True)
    return salida


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camara",type=int,default=0)
    parser.add_argument("--solo",action="store_true",help="Piloto sin distractor; informe sin ganador de identidad")
    parser.add_argument("--continuar",type=Path,help="Reanudar anotacion/analisis de una captura guiada completa")
    parser.add_argument("--descargar-modelo",action="store_true")
    parser.add_argument("--repeticiones",type=int,default=3)
    parser.add_argument("--paso-revision",type=int,default=5,
                        help="Revisar uno de cada N frames; 5 para piloto, 1 para exhaustiva")
    args=parser.parse_args()
    if args.camara < 0 or args.repeticiones < 1 or args.paso_revision < 1:
        parser.error("Camara, repeticiones o paso de revision fuera de rango")
    cv2.setNumThreads(1)
    carpeta = args.continuar.resolve() if args.continuar else REPO/"datos/enrolamientos"/datetime.now().strftime("guiada-%Y%m%d-%H%M%S-%f")
    try:
        if args.continuar is None:
            carpeta.mkdir(parents=True)
            guia=Guia(carpeta,args.solo)
            guia.guardar()
            print("Primero enrolate con E y aprueba. Luego N o Paso inicia cada escena con 3 s de preparacion.",flush=True)
            if not args.solo:
                print("Necesitas un acompanante para distractor y cruces. Usa --solo si estas solo.",flush=True)
            configuracion=SimpleNamespace(
                camara=args.camara, detector="openvino", descargar_modelo=args.descargar_modelo,
                confianza=.6,hilos=2,fps_proceso=10,ancho=640,alto=480,fps=15,
                metodo="histograma",umbral=.45,margen=.08,hog_umbral=.5,
            )
            practica(configuracion,carpeta,guia=guia)
            if not guia.terminada or guia.cancelada:
                print(f"Captura interrumpida. Datos conservados en {carpeta}",flush=True)
                return
        analizar(carpeta,repeticiones=args.repeticiones,paso=args.paso_revision)
    except (ValueError,OSError,KeyError,RuntimeError,cv2.error) as error:
        parser.exit(1,f"Error: {error}\nDatos: {carpeta}\nPara reanudar revision: --continuar {carpeta}\n")


if __name__=="__main__":
    main()
