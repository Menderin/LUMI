"""Validación de secuencias y particiones, sin acceso a cámaras."""
import argparse
import json
from pathlib import Path


def cargar(path):
    path = Path(path)
    filas = json.loads(path.read_text(encoding="utf-8"))["secuencias"]
    grupos = {}
    ids = set()
    for fila in filas:
        identificador = fila["id"]
        split = fila["split"]
        if identificador in ids or split not in {"enrolamiento", "calibracion", "evaluacion"}:
            raise ValueError(f"ID duplicado o partición inválida: {identificador}")
        ids.add(identificador)
        for clave, valor in (
            ("sesion", fila["sesion"]),
            ("original", fila["origen"]),
            ("video", str((path.parent / fila["video"]).resolve())),
            ("par", fila.get("par_estereo")),
        ):
            if valor is None:
                continue
            grupo = clave, valor
            if grupos.setdefault(grupo, split) != split:
                raise ValueError(f"Fuga entre particiones: {grupo}")
    return filas


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifiesto")
    args = parser.parse_args()
    print(f"{len(cargar(args.manifiesto))} secuencias válidas")

