import json
import tempfile
import unittest
from pathlib import Path

from software.percepcion.dataset.manifiesto import cargar


class Particiones(unittest.TestCase):
    def test_par_estereo_no_cruza_particiones(self):
        with tempfile.TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / "piloto.json"
            secuencias = [
                {"id": "a", "sesion": "s1", "split": "calibracion",
                 "video": "a.avi", "origen": "a", "par_estereo": "p1"},
                {"id": "b", "sesion": "s2", "split": "evaluacion",
                 "video": "b.avi", "origen": "b", "par_estereo": "p1"},
            ]
            archivo.write_text(json.dumps({"secuencias": secuencias}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Fuga entre particiones"):
                cargar(archivo)
            secuencias[1]["split"] = "calibracion"
            archivo.write_text(json.dumps({"secuencias": secuencias}), encoding="utf-8")
            self.assertEqual(cargar(archivo), secuencias)
