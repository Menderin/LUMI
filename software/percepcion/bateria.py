"""Ejecutar configuraciones de percepción en procesos independientes."""
import argparse
import csv
import json
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifiesto", type=Path)
    parser.add_argument("matriz", type=Path, help="JSON con lista de corridas")
    parser.add_argument("--split", choices=("calibracion", "evaluacion"), required=True)
    parser.add_argument("--equipo", required=True)
    parser.add_argument("--repeticiones", type=int, default=3)
    parser.add_argument("--vista-previa", action="store_true", help="Mostrar vídeo durante cada corrida")
    args = parser.parse_args()
    if args.repeticiones < 1 or not re.fullmatch(r"[A-Za-z0-9_-]+", args.equipo):
        parser.error("Indica un equipo alfanumérico y al menos una repetición")
    root = Path(__file__).resolve().parents[2]
    manifiesto = args.manifiesto.resolve(strict=True)
    matriz = args.matriz.resolve(strict=True)
    casos = json.loads(matriz.read_text(encoding="utf-8"))["corridas"]
    if not casos:
        parser.error("La matriz está vacía")
    configs = {}
    for caso in casos:
        nombre = caso["id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", nombre) or nombre in configs:
            parser.error(f"ID inválido o duplicado: {nombre}")
        config = (matriz.parent / caso["config"]).resolve(strict=True)
        configs[nombre] = json.loads(config.read_text(encoding="utf-8"))

    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    salida = root / "datos" / "procesados" / "baterias" / f"{marca}_{args.equipo}_{args.split}"
    salida.mkdir(parents=True, exist_ok=False)
    (salida / "bateria.json").write_text(json.dumps({
        "equipo": args.equipo, "split": args.split, "repeticiones": args.repeticiones,
        "vista_previa": args.vista_previa,
        "manifiesto": str(manifiesto), "configuraciones": configs,
    }, indent=2), encoding="utf-8")
    print(salida, flush=True)
    metricas = ("p50_ms", "p95_ms", "fps", "cpu_pct_proceso", "rss_max_muestreada_bytes")
    fallos = 0
    with (salida / "indice.csv").open("w", newline="", encoding="utf-8") as archivo:
        indice = csv.writer(archivo)
        indice.writerow(("configuracion", "repeticion", "estado", "corrida", "log", *metricas))
        archivo.flush()
        for nombre, config in configs.items():
            config_local = salida / f"{nombre}.json"
            config_local.write_text(json.dumps(config, indent=2), encoding="utf-8")
            for numero in range(1, args.repeticiones + 1):
                corrida = f"{nombre}-{numero:02d}"
                log = f"{corrida}.log"
                with (salida / log).open("w", encoding="utf-8") as registro:
                    resultado = subprocess.run([
                        sys.executable, "-m", "software.percepcion.experimentos",
                        str(manifiesto), str(config_local), str(salida / corrida),
                        "--split", args.split,
                    ] + (["--vista-previa"] if args.vista_previa else []),
                        cwd=root, stdout=registro, stderr=subprocess.STDOUT)
                resumen = {}
                ok = resultado.returncode == 0
                if ok:
                    try:
                        resumen = json.loads((salida / corrida / "resumen.json").read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        ok = False
                fallos += not ok
                estado = "ok" if ok else "fallo"
                indice.writerow((nombre, numero, estado, corrida, log, *(resumen.get(m, "") for m in metricas)))
                archivo.flush()
                print(f"{corrida}: {estado}", flush=True)
    return int(fallos > 0)


if __name__ == "__main__":
    raise SystemExit(main())
