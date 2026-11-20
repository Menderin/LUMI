import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from software.percepcion.anotar_practica import anotar, pedir_revision
from software.percepcion.guiada import validar_anotaciones
from software.percepcion.practica import Video


class RevisionVacia(unittest.TestCase):
    def test_omitir_todo_guarda_estado_sin_etiquetar(self):
        with tempfile.TemporaryDirectory() as carpeta:
            video=Path(carpeta)/"clip.avi"
            imagen=np.zeros((240,320,3),np.uint8)
            writer=Video(video,10,imagen)
            writer.escribir(imagen)
            writer.escribir(imagen)
            writer.cerrar()
            with patch("cv2.namedWindow"),patch("cv2.setMouseCallback"),patch("cv2.imshow"), \
                 patch("cv2.destroyAllWindows"),patch("cv2.waitKey",return_value=ord("n")):
                self.assertFalse(anotar(video,"calibracion","frente-perfiles",1))
            ficha=json.loads(video.with_suffix(".anotaciones.json").read_text())
            self.assertEqual(ficha["frames"],{})
            with self.assertRaisesRegex(ValueError,"Faltan"):
                validar_anotaciones(video.with_suffix(".anotaciones.json"),"calibracion","frente-perfiles")

    def test_tecla_desconocida_no_omite_y_enter_revisa(self):
        imagen=np.zeros((240,320,3),np.uint8)
        with patch("cv2.setMouseCallback"),patch("cv2.imshow"), \
             patch("cv2.getWindowProperty",return_value=1), \
             patch("cv2.waitKey",side_effect=[ord("x"),-1,13]) as espera:
            self.assertEqual(pedir_revision("revision",imagen,0),ord("s"))
            self.assertEqual(espera.call_count,3)

    def test_archivo_ausente_da_mensaje_de_revision(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with self.assertRaisesRegex(ValueError,"N solo omite"):
                validar_anotaciones(Path(carpeta)/"no-existe.json","calibracion","frente-perfiles")


if __name__=="__main__":
    unittest.main()
