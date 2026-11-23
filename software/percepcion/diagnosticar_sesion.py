"""D0: diagnostico offline de decisiones revisadas, sin inferencia ni captura."""
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from .comparar_sesion import clasificar, leer, sha256
from .experimentos import iou
from .practica import guardar_json


def guardar_csv(ruta, filas, campos=None):
    filas = list(filas)
    with ruta.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos or list(filas[0]))
        writer.writeheader()
        writer.writerows(filas)


def asociar(caja, referencia):
    mejor = max(referencia, key=lambda p: iou(caja, p["bbox"]), default=None)
    valor = iou(caja, mejor["bbox"]) if mejor else 0.
    return (mejor["id"] if valor >= .5 else None), valor


def describir(r):
    indice = r["seleccion"]
    if indice is not None and (isinstance(indice,bool) or not isinstance(indice,int)
                               or not 0 <= indice < len(r["candidatos"])):
        raise ValueError("Indice de seleccion invalido en decisiones")
    m = clasificar(r, indice)
    identidad, seleccion_iou = (None,0.) if indice is None else asociar(
        r["candidatos"][indice]["bbox"],r["referencia"])
    objetivos = [p["bbox"] for p in r["referencia"] if p["id"] == r["objetivo"]]
    max_iou = max((iou(c["bbox"],b) for c in r["candidatos"] for b in objetivos),default=0.)
    if indice is not None:
        if identidad == r["objetivo"]:
            categoria = "acierto_objetivo"
        elif identidad is not None:
            categoria = "otra_persona_seleccionada"
        else:
            categoria = "seleccion_sin_referencia_compatible"
    elif not m["visibles"]:
        categoria = "rechazo_correcto_sin_objetivo"
    elif not m["objetivo_detectado"]:
        categoria = "objetivo_sin_deteccion_compatible"
    elif r["motivo"] == "ambiguedad":
        categoria = "ambiguedad_con_objetivo_detectado"
    else:
        categoria = "rechazo_con_objetivo_detectado"
    return {**m,"categoria":categoria,"identidad_seleccionada":identidad,
            "iou_seleccion_referencia":seleccion_iou,"iou_max_objetivo":max_iou,
            "ambiguos_detectados":int(m["objetivo_detectado"] and indice is None and r["motivo"]=="ambiguedad"),
            "aceptados_sin_referencia":int(indice is not None and identidad is None)}


def diagnosticar(corrida, salida):
    corrida, salida = Path(corrida).resolve(), Path(salida).resolve()
    archivos = sorted(corrida.glob("*-frames.jsonl"))
    if not archivos:
        raise ValueError("No hay decisiones *-frames.jsonl; indica una repeticion evaluada")
    if salida.exists():
        raise ValueError("Usa una carpeta D0 nueva para conservar diagnosticos")
    registros, candidatos, resumen, fuentes, identidades = [], [], {}, [], []
    claves_ref = None
    for archivo in archivos:
        metodo = archivo.name[:-len("-frames.jsonl")]
        ficha = leer(corrida/f"{metodo}.json")
        parametros = ficha["parametros"]
        fuentes.append({"archivo":str(archivo),"sha256":sha256(archivo),
                        "resumen_sha256":sha256(corrida/f"{metodo}.json")})
        grupos = defaultdict(Counter)
        claves = []
        with archivo.open(encoding="utf-8") as f:
            for linea in f:
                if not linea.strip():
                    continue
                r = json.loads(linea)
                if r.get("split") != "evaluacion":
                    raise ValueError("D0 espera decisiones de evaluacion, no calibracion")
                clave = (r["secuencia"],r["frame"])
                claves.append((clave,r["objetivo"],r["referencia"],r["candidatos"]))
                if len(r["candidatos"]) != len(r["distancias"]) or not all(math.isfinite(d) for d in r["distancias"]):
                    raise ValueError("Distancias invalidas o distintas del numero de candidatos")
                d = describir(r)
                grupo = grupos[r["escenario"]]
                for k in ("revisados","visibles","ausentes","objetivo_detectado","perdidas_detector",
                          "rechazos_identificador","correctos","sustituciones_frames","falsas_aceptaciones",
                          "selecciones_incorrectas_visibles","ambiguos_detectados","aceptados_sin_referencia"):
                    grupo[k] += d[k]
                base = {"metodo":metodo,"secuencia":r["secuencia"],"frame":r["frame"],
                        "escenario":r["escenario"],"tiempo_s":r["tiempo_s"]}
                registros.append({**base,"categoria":d["categoria"],"objetivo_visible":d["visibles"],
                    "objetivo_detectado":d["objetivo_detectado"],"iou_max_objetivo":d["iou_max_objetivo"],
                    "seleccion":r["seleccion"],"identidad_seleccionada":d["identidad_seleccionada"],
                    "iou_seleccion_referencia":d["iou_seleccion_referencia"],"motivo":r["motivo"],
                    "umbral":parametros["umbral"],"margen":parametros["margen"],
                    "distancias":json.dumps(r["distancias"])})
                for i,c in enumerate(r["candidatos"]):
                    identidad,valor = asociar(c["bbox"],r["referencia"])
                    rol = "objetivo" if identidad==r["objetivo"] else "distractor" if identidad else "sin_asociar"
                    candidatos.append({**base,"candidato":i,"rol_anotado":rol,"iou_referencia":valor,
                        "distancia":r["distancias"][i],"umbral":parametros["umbral"],
                        "seleccionado":int(i==r["seleccion"]),"recorte_cache":c.get("imagen","")})
                identidades.extend(p["id"] != r["objetivo"] for p in r["referencia"])
        if not claves:
            raise ValueError(f"Archivo sin decisiones: {archivo}")
        if len({x[0] for x in claves}) != len(claves):
            raise ValueError("Fotogramas duplicados en decisiones")
        if claves_ref is not None and claves != claves_ref:
            raise ValueError("Los metodos no usan los mismos frames, cajas y referencias")
        claves_ref = claves
        resumen[metodo] = dict(grupos)
    salida.mkdir(parents=True)
    guardar_csv(salida/"frames.csv",registros)
    campos = ["metodo","secuencia","frame","escenario","tiempo_s","candidato","rol_anotado",
              "iou_referencia","distancia","umbral","seleccionado","recorte_cache"]
    guardar_csv(salida/"distancias-candidatos.csv",candidatos,campos)
    filas = [{"metodo":metodo,"escenario":escenario,**contadores}
             for metodo,grupos in resumen.items() for escenario,contadores in grupos.items()]
    guardar_csv(salida/"por-escenario.csv",filas)
    guardar_json(salida/"diagnostico.json",{"fuentes":fuentes,"escenarios":resumen,
                 "distractores_revisados":any(identidades),"iou_minimo":.5})
    lineas = ["# D0: origen de errores en frames revisados","",
        "No modifica etiquetas ni umbrales. Usa la primera repeticion; no triplica las muestras.","",
        "| Metodo / escenario | Aciertos / visibles | Sin caja objetivo / visibles | Rechazos / detectados | Ambiguos* | Falsas acept. / ausentes | Sustituciones / revisados | Aceptados sin referencia / revisados |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in filas:
        lineas.append(f"| {r['metodo']} / {r['escenario']} | {r['correctos']}/{r['visibles']} | "
            f"{r['perdidas_detector']}/{r['visibles']} | {r['rechazos_identificador']}/{r['objetivo_detectado']} | "
            f"{r['ambiguos_detectados']} | {r['falsas_aceptaciones']}/{r['ausentes']} | "
            f"{r['sustituciones_frames']}/{r['revisados']} | {r['aceptados_sin_referencia']}/{r['revisados']} |")
    lineas += ["","*Ambiguos es subconjunto de rechazos con objetivo detectado; no sumar ambas columnas.",
        "Una caja sin IoU >=0.5 puede ser una perdida del detector o desacuerdo de anotacion/encuadre. Revisar manualmente; D0 no determina por si solo la causa fisica.",
        "Sustituciones, falsas aceptaciones y selecciones sin referencia pueden solaparse. Son conteos por frame, no eventos temporales.",
        "frames.csv asigna una categoria por decision. distancias-candidatos.csv permite inspeccionar puntuaciones; no usar la evaluacion para ajustar umbrales.",
        "0 en el denominador significa caso no observado, no tasa de error cero."]
    if not any(identidades):
        lineas += ["","**No hay distractores anotados en evaluacion: no permite elegir ganador de identidad.**"]
    (salida/"informe.md").write_text("\n".join(lineas)+"\n",encoding="utf-8")
    return salida


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corrida",type=Path,help="Carpeta repeticion-01 con decisiones JSONL")
    parser.add_argument("salida",type=Path,help="Carpeta nueva para D0")
    args = parser.parse_args()
    try:
        print(f"D0: {diagnosticar(args.corrida,args.salida)/'informe.md'}")
    except (ValueError,OSError,KeyError,TypeError) as error:
        parser.exit(1,f"Error: {error}\n")


if __name__ == "__main__":
    main()
