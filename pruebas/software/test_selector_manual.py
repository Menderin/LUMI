import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from software.percepcion.anotar_practica import SeleccionRecuadros, seleccionar_recuadros, anotar
from software.percepcion.practica import Video, normalizar_tecla


class SelectorManual(unittest.TestCase):
    def test_arrastrar_agrega_al_soltar(self):
        s=SeleccionRecuadros(640,480)
        s.evento(cv2.EVENT_LBUTTONDOWN,200,300)
        s.evento(cv2.EVENT_MOUSEMOVE,50,40)
        self.assertEqual(s.cajas,[])
        s.evento(cv2.EVENT_LBUTTONUP,50,40)
        self.assertEqual(s.cajas,[(50,40,150,260)])
        s.evento(cv2.EVENT_LBUTTONDOWN,10,10)
        s.evento(cv2.EVENT_LBUTTONUP,11,11)
        self.assertEqual(len(s.cajas),1)

    def ejecutar_selector(self, tecla, confirmar_clic=False):
        imagen=np.zeros((240,320,3),np.uint8)
        def registrar(ventana,callback):
            callback(cv2.EVENT_LBUTTONDOWN,20,30,0,None)
            callback(cv2.EVENT_MOUSEMOVE,100,200,0,None)
            callback(cv2.EVENT_LBUTTONUP,100,200,0,None)
            if confirmar_clic:
                callback(cv2.EVENT_LBUTTONDOWN,20,300,0,None)
        with patch("cv2.setMouseCallback",side_effect=registrar),patch("cv2.imshow"),patch("cv2.getWindowProperty",return_value=1),patch("cv2.waitKey",return_value=tecla):
            return seleccionar_recuadros("selector",imagen)

    def test_confirmar_con_espacio(self):
        self.assertEqual(self.ejecutar_selector(32),[(20,30,80,170)])

    def test_confirmar_con_clic_sin_teclado(self):
        self.assertEqual(self.ejecutar_selector(-1,confirmar_clic=True),[(20,30,80,170)])

    def test_vacio_y_cancelar_son_distintos(self):
        self.assertEqual(self.ejecutar_selector(ord("0")),[])
        self.assertIsNone(self.ejecutar_selector(27))
        self.assertEqual(normalizar_tecla(16777220),13)
        self.assertEqual(normalizar_tecla(16777221),13)

    def test_anotar_guarda_objetivo_sin_selectrois(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta=Path(carpeta)/"prueba.avi"
            imagen=np.zeros((240,320,3),np.uint8)
            v=Video(ruta,10,imagen)
            v.escribir(imagen)
            v.cerrar()
            with patch("cv2.namedWindow"),patch("cv2.destroyAllWindows"),patch("cv2.getWindowProperty",return_value=1),patch("software.percepcion.anotar_practica.pedir_revision",return_value=ord("s")),patch("software.percepcion.anotar_practica.seleccionar_recuadros",return_value=[(20,30,80,170)]),patch("software.percepcion.anotar_practica.elegir_objetivo",return_value=1):
                self.assertTrue(anotar(ruta,"calibracion","frente-perfiles",1))
            datos=json.loads(ruta.with_suffix(".anotaciones.json").read_text())
            self.assertEqual(datos["frames"]["0"],[{"id":"objetivo","bbox":[20,30,100,200]}])


    def test_modo_solo_guarda_sin_segundo_clic(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta=Path(carpeta)/"prueba.avi"
            (Path(carpeta)/"guia.json").write_text(json.dumps({"solo":True}))
            imagen=np.zeros((240,320,3),np.uint8)
            v=Video(ruta,10,imagen)
            v.escribir(imagen)
            v.cerrar()
            with patch("cv2.namedWindow"),patch("cv2.destroyAllWindows"),patch("cv2.getWindowProperty",return_value=1),patch("software.percepcion.anotar_practica.pedir_revision",return_value=ord("s")),patch("software.percepcion.anotar_practica.seleccionar_recuadros",return_value=[(20,30,80,170)]) as dibujar,patch("software.percepcion.anotar_practica.elegir_objetivo") as elegir:
                self.assertTrue(anotar(ruta,"calibracion","frente-perfiles",1))
                elegir.assert_not_called()
                self.assertTrue(dibujar.call_args.kwargs["solo"])
            datos=json.loads(ruta.with_suffix(".anotaciones.json").read_text())
            self.assertEqual(datos["frames"]["0"][0]["id"],"objetivo")

    def test_seleccion_multiple_conserva_bordes_y_clic(self):
        from software.percepcion.anotar_practica import elegir_objetivo
        frame=np.zeros((240,320,3),np.uint8)
        personas=[{"id":"otro-1","bbox":[20,30,100,200]}]
        def registrar(ventana,callback):
            callback(cv2.EVENT_LBUTTONDOWN,30,190,0,None)
        with patch("cv2.setMouseCallback",side_effect=registrar),patch("cv2.imshow") as mostrar,patch("cv2.waitKey",return_value=-1):
            self.assertEqual(elegir_objetivo("elegir",frame,personas),1)
        vista=mostrar.call_args.args[1]
        self.assertEqual(vista.shape,(326,320,3))
        self.assertTrue(np.any(vista[100,20]))
        self.assertFalse(np.any(frame))

    def test_solo_reemplaza_recuadro_al_redibujar(self):
        s=SeleccionRecuadros(320,240,maximo=1)
        for x in (20,40):
            s.evento(cv2.EVENT_LBUTTONDOWN,x,30)
            s.evento(cv2.EVENT_LBUTTONUP,x+80,200)
        self.assertEqual(s.cajas,[(40,30,80,170)])


if __name__=="__main__":
    unittest.main()
