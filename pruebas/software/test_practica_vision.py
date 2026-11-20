import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from software.percepcion.enrolamiento.estado import Enrolamiento
from software.percepcion.experimentos import Identificador
from software.percepcion.practica import Video, comparar_hog, recorte_enrolamiento, resolver


class PracticaVision(unittest.TestCase):
    def test_revision_y_recuperacion_manual(self):
        estado = Enrolamiento()
        frame = np.full((240, 320, 3), (0, 0, 255), dtype=np.uint8)
        caja = (100, 20, 220, 220)
        recorte = recorte_enrolamiento(frame, [caja])
        self.assertIsNone(recorte_enrolamiento(frame, [caja, caja]))
        self.assertIsNone(recorte_enrolamiento(frame, [(0, 20, 220, 220)]))
        estado.actualizar(0, pulsacion=True)
        for segundo in range(1, 9):
            estado.actualizar(segundo, personas=1, recorte=recorte)
        estado.actualizar(10, pedir_revision=True)
        self.assertEqual(estado.estado, "revision")
        self.assertEqual(len(estado.muestras), 8)
        self.assertFalse(estado.actualizar(11, pulsacion=True, objetivo=True))
        self.assertTrue(estado.confirmar_revision(12))
        reconocedor = Identificador(estado.galeria, {"metodo": "histograma"}, Path("."))
        distractor = np.full_like(recorte, (255, 0, 0))
        propia = reconocedor.distancia(recorte)
        ajena = reconocedor.distancia(distractor)
        self.assertEqual(resolver([ajena, propia], .45, .08), (1, "coincidencia"))
        self.assertEqual(resolver([propia, propia], .45, .08), (None, "ambiguedad"))
        self.assertEqual(resolver([ajena], .45, .08), (None, "rechazo"))
        self.assertEqual(resolver([], .45, .08), (None, "ausencia"))
        self.assertTrue(estado.actualizar(13, pulsacion=True, objetivo=True))
        self.assertFalse(estado.actualizar(14))
        self.assertFalse(estado.actualizar(15, objetivo=True))
        self.assertTrue(estado.actualizar(16, pulsacion=True, objetivo=True))
        estado.descartar()
        self.assertEqual(estado.galeria, ())
        self.assertEqual(estado.intentos, 1)

    def test_video_reproducible_y_benchmark_de_escena_vacia(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        with tempfile.TemporaryDirectory() as carpeta:
            carpeta = Path(carpeta)
            ruta = carpeta / "prueba.avi"
            video = Video(ruta, 15, frame)
            try:
                for _ in range(3):
                    video.escribir(frame)
            finally:
                video.cerrar()
            captura = cv2.VideoCapture(str(ruta))
            try:
                ok, leido = captura.read()
                self.assertTrue(ok)
                self.assertEqual(leido.shape, frame.shape)
            finally:
                captura.release()
            comparar_hog(str(ruta), carpeta)
            for tamano in ("640x480", "320x240"):
                filas = (carpeta / f"hog-{tamano}.csv").read_text().splitlines()
                self.assertEqual(len(filas), 4)
                self.assertTrue(all(",[]," in fila for fila in filas[1:]))


if __name__ == "__main__":
    unittest.main()
