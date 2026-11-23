import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from software.percepcion.agregacion_galeria import MedianaGaleria
from software.percepcion.experimentos import Identificador, guardar_representacion
from software.percepcion.practica import resolver


class AgregacionGaleria(unittest.TestCase):
    def test_una_sola_coincidencia_no_basta_como_en_minimo(self):
        base=SimpleNamespace(metodo="histograma",galeria=np.zeros((4,2)),metadata={},
                             distancias_galeria=lambda x:np.array([.8,.01,.75,.9]))
        variante=MedianaGaleria(base)
        self.assertEqual(resolver([.01],.3,0)[0],0)
        self.assertIsNone(resolver([variante.distancia(None)],.3,0)[0])
        self.assertAlmostEqual(variante.distancia(None),.75)
        base.distancias_galeria=lambda x:np.array([.8,.01,.02,.9])
        self.assertEqual(resolver([variante.distancia(None)],.3,0)[0],0)

    def test_no_modifica_galeria_y_guarda_regla(self):
        rng=np.random.default_rng(71)
        muestras=[rng.integers(0,256,(128,64,3),dtype=np.uint8) for _ in range(24)]
        with tempfile.TemporaryDirectory() as carpeta:
            base=Identificador(muestras,{"metodo":"histograma"},Path(carpeta))
            distancia=base.distancia(muestras[0])
            galeria=base.galeria.copy()
            variante=MedianaGaleria(base)
            variante.distancia(muestras[0])
            self.assertAlmostEqual(base.distancia(muestras[0]),distancia)
            np.testing.assert_array_equal(base.galeria,galeria)
            guardar_representacion(variante,Path(carpeta)/"modelo.npz")
            with np.load(Path(carpeta)/"modelo.npz") as datos:
                self.assertEqual(str(datos["agregacion"]),"mediana3")
                self.assertEqual(int(datos["k"]),3)
                np.testing.assert_array_equal(datos["galeria"],galeria)

    def test_rechaza_galeria_insuficiente_y_distancias_invalidas(self):
        base=SimpleNamespace(metodo="histograma",galeria=np.zeros((2,2)))
        with self.assertRaises(ValueError):
            MedianaGaleria(base)
        base.galeria=np.zeros((3,2))
        base.distancias_galeria=lambda _:np.array([0,.1,np.nan])
        with self.assertRaises(ValueError):
            MedianaGaleria(base).distancia(None)
