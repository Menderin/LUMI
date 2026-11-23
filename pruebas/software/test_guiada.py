import csv
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import cv2
import numpy as np

from software.percepcion.guiada import Guia, analizar, validar_anotaciones
from software.percepcion.practica import Video, guardar_json
from software.percepcion.comparar_sesion import elegir_parametros
from software.percepcion.anotar_practica import elegir_objetivo


class BateriaGuiada(unittest.TestCase):
    def test_guion_cuenta_graba_y_termina(self):
        with tempfile.TemporaryDirectory() as carpeta:
            g=Guia(Path(carpeta))
            self.assertEqual(g.actualizar(0,"espera",0,None,ord("n")),ord("n"))
            self.assertEqual(g.fase,"espera")
            ahora=1
            for i,paso in enumerate(g.pasos):
                g.actualizar(ahora,"listo",1,None,ord("n"))
                self.assertEqual(g.fase,"cuenta")
                self.assertEqual(g.actualizar(ahora+3,"listo",1,None,-1),ord("v"))
                clip=SimpleNamespace(ruta=Path(carpeta)/f"prueba-{i}.avi")
                g.actualizar(ahora+3.1,"listo",1,clip,-1)
                self.assertEqual(g.actualizar(ahora+4+paso["duracion_s"],"listo",1,clip,-1),ord("v"))
                g.actualizar(ahora+4.1+paso["duracion_s"],"listo",1,None,-1)
                ahora+=paso["duracion_s"]+5
            self.assertTrue(g.terminada)
            self.assertEqual(len(g.clips),10)
            self.assertTrue(json.loads((Path(carpeta)/"guia.json").read_text())["terminada"])

    def test_captura_guiada_por_el_punto_de_entrada(self):
        from software.percepcion.practica import practica
        from software.percepcion.enrolamiento.sesion import SesionEnrolamiento
        with tempfile.TemporaryDirectory() as carpeta:
            carpeta=Path(carpeta)
            g=Guia(carpeta,solo=True)
            sesion=SesionEnrolamiento(desde_video=True,recuperacion_simulada=True)
            reloj={"ahora":0,"frame":0}
            def frame():
                reloj["frame"]+=1
                imagen=np.full((480,640,3),(10,30,220),np.uint8)
                y=80+reloj["frame"]%24
                imagen[y:y+20,120:180]=(100,30,20)
                return True,imagen
            def tecla(_):
                reloj["ahora"]=round(reloj["ahora"]+.2,1)
                if reloj["frame"]==1:
                    return ord("e")
                if g.fase=="espera" and sesion.registro.estado=="listo":
                    return ord("n")
                return 27 if reloj["ahora"]>250 else -1
            camara=MagicMock()
            camara.read.side_effect=frame
            camara.get.return_value=15
            args=SimpleNamespace(detector="hog",hog_umbral=.5,fps=15,fps_proceso=10,
                                 umbral=.45,margen=.08,metodo="histograma")
            with patch("software.percepcion.practica.abrir_camara",return_value=camara), \
                 patch("software.percepcion.practica.SesionEnrolamiento",return_value=sesion), \
                 patch("software.percepcion.practica.DetectorHOG") as hog, \
                 patch("software.percepcion.practica.revisar",return_value=13), \
                 patch("software.percepcion.practica.time.monotonic",side_effect=lambda:reloj["ahora"]), \
                 patch("cv2.setMouseCallback"),patch("cv2.namedWindow"),patch("cv2.imshow"), \
                 patch("cv2.destroyAllWindows"),patch("cv2.getWindowProperty",return_value=1), \
                 patch("cv2.waitKey",side_effect=tecla):
                hog.return_value.return_value=[(100,40,200,360)]
                hog.return_value.metadata={}
                practica(args,carpeta,guia=g)
            self.assertTrue(g.terminada)
            self.assertEqual(len(g.clips),6)
            self.assertEqual(len({r["video"] for r in g.clips}),6)
            self.assertTrue(all((carpeta/r["video"]).is_file() for r in g.clips))
            with (carpeta/"decisiones.csv").open() as f:
                clips={r["clip"] for r in csv.DictReader(f) if r["clip"]}
            self.assertEqual(clips,{r["video"] for r in g.clips})

    def test_solo_permite_calibracion_exploratoria(self):
        fila={"secuencia":"a","escenario":"solo","tiempo_s":0,"objetivo":"objetivo",
              "referencia":[{"id":"objetivo","bbox":[0,0,10,20]}],
              "candidatos":[{"bbox":[0,0,10,20]}],"distancias":[.1]}
        vacia={**fila,"tiempo_s":1,"referencia":[],"candidatos":[],"distancias":[]}
        with self.assertRaisesRegex(ValueError,"distractores"):
            elegir_parametros([fila,vacia])
        cfg=elegir_parametros([fila,vacia],exigir_distractor=False)
        self.assertTrue(cfg["util"])

    def test_cambio_galeria_interrumpe(self):
        with tempfile.TemporaryDirectory() as carpeta:
            g=Guia(Path(carpeta),solo=True)
            self.assertEqual(len(g.pasos),6)
            g.actualizar(0,"listo",1,None,ord("n"))
            self.assertEqual(g.actualizar(1,"listo",2,None,-1),27)
            self.assertTrue(g.cancelada)

    def test_eleccion_objetivo_por_tecla(self):
        frame=np.zeros((240,320,3),np.uint8)
        personas=[{"id":"otro-1","bbox":[10,10,100,200]}]
        with patch("cv2.setMouseCallback"),patch("cv2.imshow"),patch("cv2.getWindowProperty",return_value=1),patch("cv2.waitKey",return_value=ord("1")):
            self.assertEqual(elegir_objetivo("anotar",frame,personas),1)

    def test_analisis_completo_con_anotaciones_sinteticas(self):
        with tempfile.TemporaryDirectory() as carpeta:
            root=Path(carpeta)
            sesion=root/"sesion"
            sesion.mkdir()
            galeria=sesion/"galeria-1"
            galeria.mkdir()
            rng=np.random.default_rng(6)
            muestras=[]
            for i in range(24):
                imagen=np.full((128,64,3),(10,30,220),np.uint8)
                imagen[10+i:20+i,10:50]=rng.integers(0,150,(10,40,3),dtype=np.uint8)
                muestras.append(imagen)
                cv2.imwrite(str(galeria/f"{i+1:02}.png"),imagen)
            guardar_json(galeria/"galeria.json",{"aprobada":True,"intento":1,
                         "imagenes":[f"{i+1:02}.png" for i in range(24)]})
            self.video(sesion/"enrolamiento-1.avi",[muestras[0]])
            clips=[]
            decisiones=[]
            for split,j in (("calibracion",0),("evaluacion",1)):
                for k,escenario in enumerate(("frente-perfiles","oclusion","ausente","distractor","cruce")):
                    frame=np.full((240,320,3),30+j*40+k*15,np.uint8)
                    personas=[]
                    cajas=[]
                    if escenario in ("frente-perfiles","oclusion","cruce"):
                        frame[20:148,20:84]=muestras[j]
                        personas.append({"id":"objetivo","bbox":[20,20,84,148]})
                        cajas.append([20,20,84,148])
                    if escenario in ("distractor","cruce"):
                        frame[20:148,150:214]=(220,30,10)
                        personas.append({"id":"otro-1","bbox":[150,20,214,148]})
                        cajas.append([150,20,214,148])
                    video=sesion/f"{split}-{escenario}.avi"
                    self.video(video,[frame])
                    guardar_json(video.with_suffix(".anotaciones.json"),{
                        "split":split,"escenario":escenario,"objetivo":"objetivo","frames":{"0":personas}})
                    clips.append({"video":video.name,"split":split,"escenario":escenario,"instruccion":escenario})
                    decisiones.append({"clip":video.name,"frame_clip":0,"cajas":json.dumps(cajas),
                                       "detector_ms":10,"tiempo_monotonico_s":k})
            with (sesion/"decisiones.csv").open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=list(decisiones[0]))
                w.writeheader()
                w.writerows(decisiones)
            guardar_json(sesion/"guia.json",{"terminada":True,"cancelada":False,"solo":False,
                                          "galeria":"galeria-1","clips":clips})
            pasos=[]
            def anotador(video,split,escenario,paso):
                pasos.append((escenario,paso))
                return True
            with patch("software.percepcion.guiada.REPO",root):
                salida=analizar(sesion,repeticiones=2,anotador=anotador)
            self.assertEqual(len(pasos),10)
            self.assertEqual({p for escenario,p in pasos},{5})
            self.assertTrue((salida/"informe.md").is_file())
            self.assertIn("Limitacion:",(salida/"informe.md").read_text())
            with (salida/"comparacion.csv").open() as f:
                filas=list(csv.DictReader(f))
            self.assertEqual(len(filas),4)
            self.assertEqual({r["repeticiones"] for r in filas if r["estado"] == "evaluado"},{"2"})
            pendiente=next(r for r in filas if r["metodo"] == "cc_ppca")
            self.assertEqual(pendiente["estado"],"pendiente")
            self.assertEqual(pendiente["correctos"],"")
            self.assertTrue(json.loads((salida/"recomendacion.json").read_text())["decisiones_equivalentes"])
            with patch("software.percepcion.guiada.REPO",root):
                salida_ag=analizar(sesion,repeticiones=1,anotador=anotador,comparar_galeria=True)
            with (salida_ag/"comparacion.csv").open() as f:
                variantes=list(csv.DictReader(f))
            self.assertEqual(len(variantes),5)
            self.assertIn("histograma_mediana3",{r["metodo"] for r in variantes})
            self.assertTrue((salida_ag/"comparacion-galeria.csv").is_file())


    @staticmethod
    def video(ruta,frames):
        video=Video(ruta,10,frames[0])
        try:
            for frame in frames:
                video.escribir(frame)
        finally:
            video.cerrar()


if __name__=="__main__":
    unittest.main()
