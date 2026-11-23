import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from software.percepcion.reid_openvino import entrada, normalizar, validar_pesos, configuracion, ReIDOpenVINO, descargar, MODELO
from software.percepcion.comparar_sesion import firma_calibracion


class EncoderCNN(unittest.TestCase):
    def test_contrato_bgr_sin_normalizacion_adicional(self):
        imagen=np.full((60,30,3),(12,80,220),np.uint8)
        x=entrada(imagen)
        self.assertEqual(x.shape,(1,3,256,128))
        self.assertEqual(x.dtype,np.float32)
        np.testing.assert_array_equal(x[0,:,0,0],[12,80,220])
        self.assertTrue(x.flags.c_contiguous)
        with self.assertRaises(ValueError):
            entrada(np.zeros((10,10),np.uint8))

    def test_embedding_normalizado_y_distancia_no_es_probabilidad(self):
        vector=np.arange(1,257,dtype=np.float32)
        x=normalizar(vector)
        self.assertAlmostEqual(float(np.linalg.norm(x)),1,places=6)
        m=ReIDOpenVINO.__new__(ReIDOpenVINO)
        m.galeria=np.stack([x])
        m.vector=lambda _: x
        self.assertAlmostEqual(m.distancia(None),0,places=6)
        m.vector=lambda _: -x
        self.assertAlmostEqual(m.distancia(None),2,places=6)
        for invalido in (np.zeros(256),np.ones(255),np.full(256,np.nan)):
            with self.assertRaises(ValueError):
                normalizar(invalido)

    def test_integridad_y_descarga_reutiliza_pesos_verificados(self):
        with tempfile.TemporaryDirectory() as carpeta:
            root=Path(carpeta)
            ruta=root/f"{MODELO}.xml"
            archivos={ext:(len(ext),hashlib.sha384(ext.encode()).hexdigest()) for ext in ("xml","bin")}
            with patch("software.percepcion.reid_openvino.ARCHIVOS",archivos):
                for ext in archivos:
                    ruta.with_suffix("."+ext).write_text(ext)
                with patch("software.percepcion.reid_openvino.urlopen") as abrir:
                    self.assertEqual(descargar(root),ruta)
                    abrir.assert_not_called()
                cfg=configuracion(ruta)
                cache={"galeria_sha256":["a"],"frames":[]}
                self.assertNotEqual(firma_calibracion(cache),firma_calibracion({**cache,"cnn":cfg}))
                self.assertEqual(set(validar_pesos(ruta)),{"xml","bin"})
                ruta.with_suffix(".bin").write_bytes(b"corrupto")
                with self.assertRaisesRegex(ValueError,"incompatible"):
                    validar_pesos(ruta)
                ruta.unlink()
                with self.assertRaisesRegex(ValueError,"Faltan pesos"):
                    validar_pesos(ruta)


class ParametrosEnVivo(unittest.TestCase):
    def test_ultima_calibracion_y_pesos_coincidentes(self):
        import json
        from types import SimpleNamespace
        from software.percepcion.practica import cargar_parametros
        with tempfile.TemporaryDirectory() as carpeta:
            root=Path(carpeta)
            salida=root/"datos/procesados/bateria-guiada-20261123-1"
            salida.mkdir(parents=True)
            cfg={"metodos":{"cnn_reid":{"umbral":.23,"margen":.04,"util":True}},
                 "modelos":{"cnn_reid":{"sha256":{"xml":"a","bin":"b"}}}}
            (salida/"umbrales.json").write_text(json.dumps(cfg))
            args=SimpleNamespace(parametros="auto",metodo="cnn_reid",umbral=None,margen=None,
                                 cnn={"sha256":{"xml":"a","bin":"b"}})
            with patch("software.percepcion.practica.REPO",root):
                cargar_parametros(args)
            self.assertEqual((args.umbral,args.margen),(.23,.04))
            args.umbral=args.margen=None
            args.cnn["sha256"]["bin"]="otro"
            with self.assertRaisesRegex(ValueError,"pesos CNN"):
                cargar_parametros(args)

    def test_no_fabrica_umbral_si_no_hay_calibracion(self):
        from types import SimpleNamespace
        from software.percepcion.practica import cargar_parametros
        with tempfile.TemporaryDirectory() as carpeta:
            args=SimpleNamespace(parametros="auto",metodo="cnn_reid",umbral=None,margen=None)
            with patch("software.percepcion.practica.REPO",Path(carpeta)):
                with self.assertRaisesRegex(ValueError,"No se encontro"):
                    cargar_parametros(args)
