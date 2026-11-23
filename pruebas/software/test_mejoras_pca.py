import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np
from software.percepcion.experimentos import gris, crear_identificadores, guardar_representacion
from software.percepcion.comparar_sesion import PERFILES_MEJORA_PCA

class MejorasPCA(unittest.TestCase):
    def test_ecualizar_conserva_padding_y_referencia(self):
        imagen=np.arange(20*20,dtype=np.uint8).reshape(20,20)
        imagen=cv2.cvtColor(imagen,cv2.COLOR_GRAY2BGR)
        original=gris(imagen,128).reshape(128,64)
        variante=gris(imagen,128,"eqhist").reshape(128,64)
        np.testing.assert_array_equal(original[:32],0)
        np.testing.assert_array_equal(variante[:32],0)
        esperado=cv2.equalizeHist(cv2.resize(imagen[:,:,0],(64,64)))/255
        np.testing.assert_allclose(variante[32:96],esperado,atol=1e-7)
        self.assertFalse(np.array_equal(original,variante))

    def test_perfiles_preservan_baseline_y_proyeccion_compartida(self):
        rng=np.random.default_rng(42)
        muestras=[rng.integers(30,180,(128,64,3),dtype=np.uint8) for _ in range(12)]
        with tempfile.TemporaryDirectory() as carpeta:
            base=crear_identificadores(muestras,Path(carpeta))
            ampliado=crear_identificadores(muestras,Path(carpeta),perfiles_pca=PERFILES_MEJORA_PCA)
            self.assertEqual(len(ampliado),5)
            for nombre in base:
                self.assertAlmostEqual(base[nombre].distancia(muestras[0]),ampliado[nombre].distancia(muestras[0]),places=5)
            a,b=ampliado["euclidea_eqhist"],ampliado["mahalanobis_eqhist"]
            np.testing.assert_array_equal(a.componentes,b.componentes)
            np.testing.assert_array_equal(a.media,b.media)
            guardar_representacion(a,Path(carpeta)/"eq.npz")
            with np.load(Path(carpeta)/"eq.npz") as archivo:
                self.assertEqual(str(archivo["preproceso"]),"eqhist")
