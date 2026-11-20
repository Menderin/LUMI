import tempfile
import unittest
from pathlib import Path
from collections import deque

import cv2
import numpy as np

from software.percepcion.enrolamiento.sesion import SesionEnrolamiento
from software.percepcion.enrolamiento.video import extraer
from software.percepcion.practica import Video, normalizar_tecla, botones, callback_botones


class CapturaVideo(unittest.TestCase):
    def test_12_segundos_y_24_muestras_posteriores(self):
        s=SesionEnrolamiento(desde_video=True)
        self.assertTrue(s.accion("iniciar",0,personas=1))
        s.actualizar(3)
        s.actualizar(14.9,personas=1,recorte=np.zeros((10,10,3),np.uint8))
        self.assertEqual(s.registro.estado,"enrolando")
        self.assertEqual(len(s.registro.muestras),0)
        s.actualizar(15)
        self.assertEqual(s.registro.estado,"procesando")
        with tempfile.TemporaryDirectory() as destino:
            ruta=Path(destino)/"captura.avi"
            registros=[]
            frame=np.zeros((240,320,3),np.uint8)
            video=Video(ruta,10,frame)
            try:
                for i in range(120):
                    frame[:]=i
                    video.escribir(frame)
                    registros.append({"frame":i,"tiempo_s":3+i*.1,"cajas":[[20,20,120,200]],
                                      "ancho":320,"alto":240})
            finally:
                video.cerrar()
            muestras,informe=extraer(ruta,registros)
        self.assertEqual(len(muestras),24)
        self.assertEqual(informe["validos"],120)
        self.assertEqual(informe["seleccion"][0]["frame"],0)
        self.assertEqual(informe["seleccion"][-1]["frame"],119)
        self.assertEqual(len({r["frame"] for r in informe["seleccion"]}),24)
        self.assertTrue(s.completar_video(muestras))
        self.assertTrue(s.accion("confirmar",16))
        self.assertEqual(len(s.registro.galeria),24)
        self.assertEqual(s.registro.estado,"listo")
        self.assertFalse(s.accion("iniciar_seguimiento",17,objetivo=False))
        self.assertIn("coincidencia",s.mensaje)
        self.assertFalse(s.eventos[-1]["aceptada"])
        self.assertTrue(s.accion("iniciar_seguimiento",18,objetivo=True))

    def test_busqueda_simulada_reencuentro_y_ambiguedad(self):
        s=SesionEnrolamiento(recuperacion_simulada=True)
        s.registro.estado="listo"
        s.registro.galeria=([1],[2])
        original=s.registro.galeria
        for t in range(4):
            self.assertFalse(s.actualizar(t,objetivo=True))
        self.assertEqual(s.registro.estado,"listo")
        self.assertTrue(s.accion("iniciar_seguimiento",4,objetivo=True))
        self.assertFalse(s.actualizar(5,objetivo=False))
        self.assertEqual(s.registro.estado,"perdido")
        self.assertFalse(s.actualizar(6,objetivo=True))
        self.assertFalse(s.actualizar(7,objetivo=True))
        self.assertFalse(s.actualizar(8,objetivo=False))
        self.assertEqual(s.coincidencias_reencuentro,0)
        self.assertFalse(s.actualizar(9,objetivo=True))
        self.assertFalse(s.actualizar(10,objetivo=True))
        self.assertTrue(s.actualizar(11,objetivo=True))
        self.assertIs(s.registro.galeria,original)
        self.assertEqual(s.eventos[-1]["origen"],"recuperacion_simulada")
        s.accion("cancelar",12)
        for t in range(13,18):
            self.assertFalse(s.actualizar(t,objetivo=True))
        self.assertEqual(s.registro.estado,"espera")

    def test_fallo_recuperable_y_descartes(self):
        s=SesionEnrolamiento(desde_video=True)
        s.accion("iniciar",0,personas=1)
        s.actualizar(3)
        s.actualizar(15)
        self.assertFalse(s.completar_video([np.zeros((10,10,3),np.uint8)]*9))
        self.assertEqual(s.registro.estado,"fallo")
        self.assertIn("9",s.mensaje)
        self.assertTrue(s.accion("repetir",16,personas=1))
        with tempfile.TemporaryDirectory() as destino:
            ruta=Path(destino)/"captura.avi"
            frame=np.zeros((240,320,3),np.uint8)
            video=Video(ruta,10,frame)
            registros=[]
            cajas=[[],[[0,20,100,200]],[[20,20,100,200],[120,20,200,200]]]
            try:
                for i,lista in enumerate(cajas):
                    video.escribir(frame)
                    registros.append({"frame":i,"tiempo_s":i*.1,"cajas":lista,"ancho":320,"alto":240})
            finally:
                video.cerrar()
            muestras,informe=extraer(ruta,registros)
            self.assertEqual(muestras,[])
            self.assertEqual(informe["descartes"],{"sin_persona":1,"borde":1,"varias_personas":1})
            with self.assertRaisesRegex(RuntimeError,"incompleto"):
                extraer(ruta,registros[:-1])

    def test_teclas_y_botones(self):
        for letra in "ERSCV":
            self.assertEqual(normalizar_tecla(ord(letra)),ord(letra.lower()))
        self.assertEqual(normalizar_tecla(-1),-1)
        self.assertEqual(normalizar_tecla(13),13)
        imagen=np.zeros((480,640,3),np.uint8)
        zonas=botones(imagen,[("Seguir",ord("s")),("Cancelar",ord("c"))],350)
        cola=deque()
        callback=callback_botones(zonas,cola)
        callback(cv2.EVENT_LBUTTONDOWN,30,365,0,None)
        callback(cv2.EVENT_LBUTTONDOWN,350,365,0,None)
        self.assertEqual(list(cola),[ord("s"),ord("c")])


if __name__=="__main__":
    unittest.main()
