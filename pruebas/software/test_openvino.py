import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch
import numpy as np
from software.percepcion.detector_openvino import DetectorOpenVINO, decodificar


class OpenVINOAdapter(unittest.TestCase):
    def test_coordenadas_clase_y_filtros(self):
        salida = np.zeros((1, 1, 200, 7), dtype=np.float32)
        salida[..., 0] = -1
        salida[0, 0, 0] = [0, 0, .9, .1, .2, .5, .8]
        salida[0, 0, 1] = [0, 1, .9, 0, 0, 1, 1]
        salida[0, 0, 2] = [0, 0, .2, 0, 0, 1, 1]
        salida[0, 0, 3] = [0, 0, .9, .8, .8, .2, .2]
        salida[0, 0, 4] = [0, 0, .9, np.nan, 0, 1, 1]
        self.assertEqual(decodificar(salida, 640, 480, .6), [(64, 96, 320, 384)])
        with self.assertRaises(RuntimeError):
            decodificar(np.zeros((1, 10, 6)), 640, 480, .6)

    def test_fallo_modelo_ausente(self):
        import importlib.util
        if importlib.util.find_spec("openvino") is None:
            self.skipTest("Runtime opcional no instalado")
        with self.assertRaisesRegex(RuntimeError, "Faltan pesos"):
            DetectorOpenVINO("ruta-inexistente.xml")


    def test_perfil_registra_recursos_y_libera_camara(self):
        from software.percepcion.practica import practica
        args = SimpleNamespace(detector="hog", hog_umbral=.5, fps=15,
                               fps_proceso=5, umbral=.45, margen=.08)
        camara = MagicMock()
        camara.get.return_value = 15
        camara.read.return_value = (True, np.zeros((480, 640, 3), np.uint8))
        with tempfile.TemporaryDirectory() as destino:
            with patch("software.percepcion.practica.abrir_camara", return_value=camara), \
                 patch("software.percepcion.practica.DetectorHOG") as hog, \
                 patch("cv2.namedWindow"), patch("cv2.imshow"), \
                 patch("cv2.destroyAllWindows"), patch("cv2.waitKey", return_value=27):
                hog.return_value.return_value = []
                hog.return_value.metadata = {}
                practica(args, Path(destino))
            self.assertEqual(len((Path(destino) / "recursos.csv").read_text().splitlines()), 2)
            self.assertTrue((Path(destino) / "resumen.json").is_file())
            camara.release.assert_called_once()


if __name__ == "__main__":
    unittest.main()
