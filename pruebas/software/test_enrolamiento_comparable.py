"""Regresiones de enrolamiento compartido, direccion y comparacion reproducible."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import cv2
import numpy as np

from software.control.direccion_simulada import DireccionSimulada
from software.percepcion.enrolamiento.sesion import SesionEnrolamiento
from software.percepcion.experimentos import crear_identificadores
from software.percepcion.comparar_sesion import (
    preparar, calibrar, evaluar, elegir_parametros, evaluar_puntuaciones, sha256, clonar_con_negativa,
)
from software.percepcion.practica import Video, guardar_json


class FlujoEnrolamiento(unittest.TestCase):
    def test_cuenta_revision_y_confirmacion_separada(self):
        s = SesionEnrolamiento()
        self.assertFalse(s.accion("iniciar", 0, personas=2))
        self.assertTrue(s.accion("iniciar", 0, personas=1))
        self.assertEqual(s.registro.intentos, 0)
        s.actualizar(2.9, personas=1, recorte=[1])
        self.assertEqual(s.registro.estado, "preparando")
        s.actualizar(3, personas=1, recorte=[1])
        for t in range(4, 12):
            s.actualizar(t, personas=1, recorte=[t])
        s.actualizar(13)
        self.assertEqual(s.registro.estado, "revision")
        self.assertFalse(s.accion("iniciar_seguimiento", 14, objetivo=True))
        self.assertTrue(s.accion("confirmar", 14))
        self.assertEqual(s.registro.estado, "listo")
        s.actualizar(15, objetivo=True)
        self.assertEqual(s.registro.estado, "listo")
        self.assertTrue(s.accion("iniciar_seguimiento", 16, objetivo=True))
        self.assertFalse(s.actualizar(17, objetivo=False))
        self.assertEqual(s.registro.estado, "perdido")
        s.actualizar(18, objetivo=True)
        self.assertEqual(s.registro.estado, "perdido")
        self.assertFalse(s.accion("reanudar", 18, objetivo=False))
        self.assertTrue(s.accion("reanudar", 19, objetivo=True))

    def test_ventana_confirma_y_espera_orden_de_inicio(self,metodo="histograma"):
        from software.percepcion.practica import practica
        sesion = SesionEnrolamiento(desde_video=True, recuperacion_simulada=True)
        reloj = {"ahora": 0, "frame": 0, "listo": 0, "occlusion": False}
        def leer_frame():
            reloj["frame"] += 1
            rng = np.random.default_rng(reloj["frame"])
            frame = np.full((480, 640, 3), (10, 30, 200), np.uint8)
            frame[80:150, 120:180] = rng.integers(0, 200, (70,60,3), dtype=np.uint8)
            return True, frame
        def tecla(_):
            reloj["ahora"] = round(reloj["ahora"] + .1, 1)
            if reloj["frame"] == 1:
                return ord("e")
            if sesion.registro.estado == "listo":
                reloj["listo"] += 1
                return ord("s") if reloj["listo"] == 2 else -1
            if sesion.registro.estado == "siguiendo" and reloj["occlusion"]:
                return 27
            if reloj["ahora"] > 25:
                return 27
            return -1
        def detecciones(frame):
            if sesion.registro.estado == "siguiendo" and not reloj["occlusion"]:
                reloj["occlusion"] = True
                return []
            return [(100,40,200,360)]
        camara = MagicMock()
        camara.get.return_value = 15
        camara.read.side_effect = leer_frame
        args = SimpleNamespace(detector="hog", hog_umbral=.5, fps=15, fps_proceso=10,
                               umbral=.45, margen=.08, metodo=metodo)
        if metodo=="cnn_reid":
            import os
            from software.percepcion.reid_openvino import configuracion
            args.cnn=configuracion(os.environ["LUMI_REID_XML"])
        with tempfile.TemporaryDirectory() as destino:
            with patch("software.percepcion.practica.SesionEnrolamiento", return_value=sesion), \
                 patch("software.percepcion.practica.abrir_camara", return_value=camara), \
                 patch("software.percepcion.practica.DetectorHOG") as hog, \
                 patch("software.percepcion.practica.time.monotonic", side_effect=lambda: reloj["ahora"]), \
                 patch("software.percepcion.practica.revisar", return_value=13), \
                 patch("cv2.setMouseCallback"), patch("cv2.namedWindow"), patch("cv2.imshow"), patch("cv2.destroyAllWindows"), \
                 patch("cv2.getWindowProperty", return_value=1), patch("cv2.waitKey", side_effect=tecla):
                hog.return_value.side_effect = detecciones
                hog.return_value.metadata = {}
                practica(args, Path(destino))
            with (Path(destino)/"decisiones.csv").open() as f:
                filas = list(csv.DictReader(f))
            self.assertIn("listo", [r["estado"] for r in filas])
            self.assertIn("siguiendo", [r["estado"] for r in filas])
            self.assertIn("buscando", [r["zona"] for r in filas])
            perdidas = [i for i,r in enumerate(filas) if r["estado"] == "perdido"]
            self.assertTrue(perdidas)
            self.assertTrue(any(r["estado"] == "siguiendo" for r in filas[max(perdidas)+1:]))
            self.assertEqual(sum(e.get("origen") == "recuperacion_simulada" for e in sesion.eventos),1)
            for r in filas:
                if r["estado"] == "listo":
                    self.assertEqual(r["intencion"], "Detener / sin objetivo")
            self.assertTrue((Path(destino)/"galeria-1"/"galeria.json").is_file())
            if metodo=="cnn_reid":
                with np.load(Path(destino)/"galeria-1"/"cnn_reid.npz") as datos:
                    self.assertEqual(datos["galeria"].shape,(24,256))
                self.assertFalse((Path(destino)/"galeria-1"/"euclidea.npz").exists())
            else:
                a = np.load(Path(destino)/"galeria-1"/"euclidea.npz")
                b = np.load(Path(destino)/"galeria-1"/"mahalanobis.npz")
                with a, b:
                    np.testing.assert_array_equal(a["componentes"], b["componentes"])
            self.assertEqual(sesion.registro.intentos, 1)
            self.assertEqual(len(sesion.registro.galeria), 24)

    def test_ventana_cnn_con_pesos_reales_si_disponibles(self):
        import os
        if not os.environ.get("LUMI_REID_XML"):
            self.skipTest("Falta LUMI_REID_XML para inferencia real sin descargar")
        self.test_ventana_confirma_y_espera_orden_de_inicio(metodo="cnn_reid")

    def test_limite_cancelacion_y_repeticion(self):
        s = SesionEnrolamiento()
        for intento in range(5):
            t = intento*20
            self.assertTrue(s.accion("repetir", t, personas=1))
            s.actualizar(t+3)
            self.assertTrue(s.accion("cancelar", t+4))
            self.assertEqual(s.registro.intentos, intento+1)
        self.assertFalse(s.accion("iniciar", 100, personas=1))
        self.assertFalse(s.accion("repetir", 100, personas=1))
        self.assertEqual(s.registro.galeria, ())

    def test_zonas_histeresis_y_perdida(self):
        d = DireccionSimulada()
        def decidir(x):
            return d.actualizar((x*100-5, 0, x*100+5, 100), 100)["zona"]
        self.assertEqual(decidir(.5), "centro")
        self.assertEqual(decidir(.39), "centro")
        self.assertEqual(decidir(.36), "izquierda")
        self.assertEqual(decidir(.42), "izquierda")
        self.assertEqual(decidir(.44), "centro")
        self.assertEqual(decidir(.64), "derecha")
        self.assertEqual(decidir(.58), "derecha")
        self.assertEqual(decidir(.56), "centro")
        self.assertEqual(d.actualizar(None, 100)["intencion"], "Detener / sin objetivo")


def muestras():
    rng = np.random.default_rng(12)
    resultado = []
    for i in range(8):
        imagen = np.full((128, 64, 3), (10, 30, 220), np.uint8)
        imagen[15+i:30+i, 10:40] = (60+i, 10, 100)
        imagen = cv2.add(imagen, rng.integers(0, 8, imagen.shape, dtype=np.uint8))
        resultado.append(imagen)
    return resultado


class Comparacion(unittest.TestCase):
    def test_misma_pca_y_rango_degenerado(self):
        modelos = crear_identificadores(muestras(), Path("."))
        a, b = modelos["euclidea"], modelos["mahalanobis"]
        np.testing.assert_array_equal(a.componentes, b.componentes)
        np.testing.assert_array_equal(a.media, b.media)
        np.testing.assert_array_equal(a.galeria, b.galeria)
        for modelo in modelos.values():
            self.assertTrue(np.isfinite(modelo.distancia(muestras()[0])))
        with self.assertRaises(ValueError):
            crear_identificadores([np.zeros((128,64,3), np.uint8)]*8, Path("."))

    def test_metricas_ignoran_frames_no_revisados_y_detectan_sustitucion(self):
        filas = [{
            "secuencia": "a", "frame": 0, "tiempo_s": 0, "escenario": "cruce",
            "objetivo": "objetivo",
            "referencia": [{"id": "objetivo", "bbox": [0,0,20,40]},
                           {"id": "otro", "bbox": [40,0,60,40]}],
            "candidatos": [{"bbox": [0,0,20,40]}, {"bbox": [40,0,60,40]}],
            "distancias": [.9, .1],
        }]
        r, _ = evaluar_puntuaciones(filas, .3, .01)
        self.assertEqual(r["escenarios"]["cruce"]["sustituciones_frames"], 1)
        self.assertEqual(r["escenarios"]["cruce"]["revisados"], 1)
        r, _ = evaluar_puntuaciones(filas, .01, .01)
        self.assertEqual(r["escenarios"]["cruce"]["rechazos_identificador"], 1)
        filas[0]["candidatos"] = []
        filas[0]["distancias"] = []
        r, _ = evaluar_puntuaciones(filas, .3, .01)
        self.assertEqual(r["escenarios"]["cruce"]["perdidas_detector"], 1)
        self.assertEqual(r["escenarios"]["cruce"]["rechazos_identificador"], 0)

    def test_cache_calibracion_evaluacion_y_proteccion_galeria(self):
        with tempfile.TemporaryDirectory() as carpeta:
            root = Path(carpeta)
            galeria = root / "galeria-1"
            galeria.mkdir()
            for i, imagen in enumerate(muestras(), 1):
                cv2.imwrite(str(galeria / f"{i:02}.png"), imagen)
            guardar_json(galeria / "galeria.json", {
                "aprobada": True, "intento": 1, "imagenes": [f"{i:02}.png" for i in range(1,9)]
            })
            guardar_video(root / "enrolamiento-1.avi", [muestras()[0]])
            videos = []
            for split, detalle in (("calibracion", 0), ("evaluacion", 1)):
                video = root / f"{split}.avi"
                imagen = np.zeros((240,320,3), np.uint8)
                imagen[20:148, 20:84] = muestras()[detalle]
                imagen[20:148, 150:214] = (220,30,10)
                otro = np.zeros_like(imagen)
                otro[20:148,150:214] = (220,30,10)
                guardar_video(video, [imagen, otro, np.zeros_like(imagen)])
                videos.append(video)
                guardar_json(video.with_suffix(".anotaciones.json"), {
                    "split": split, "escenario": "interior", "objetivo": "objetivo",
                    "frames": {
                        "0": [{"id":"objetivo","bbox":[20,20,84,148]}, {"id":"otro","bbox":[150,20,214,148]}],
                        "1": [{"id":"otro","bbox":[150,20,214,148]}], "2": []
                    }
                })
            with (root/"decisiones.csv").open("w",newline="") as f:
                writer=csv.DictWriter(f,fieldnames=["clip","frame_clip","cajas","detector_ms","tiempo_monotonico_s"])
                writer.writeheader()
                for video in videos:
                    for i, cajas in enumerate(([[20,20,84,148],[150,20,214,148]],[[150,20,214,148]],[])):
                        writer.writerow({"clip":video.name,"frame_clip":i,"cajas":json.dumps(cajas),
                                         "detector_ms":12,"tiempo_monotonico_s":i*.1})
            cache=root/"cache"
            preparar(galeria,cache,videos)
            cfg=root/"congelada.json"
            calibrar(cache,cfg)
            firma=sha256(cfg)
            evaluar(cache,cfg,root/"resultado")
            self.assertEqual(sha256(cfg),firma)
            with (root/"resultado"/"comparacion.csv").open() as f:
                registros=list(csv.DictReader(f))
            self.assertEqual(len(registros),3)
            self.assertEqual({r["revisados"] for r in registros},{"3"})
            self.assertTrue((root/"resultado"/"recomendacion.json").is_file())
            self.assertEqual(json.loads((root/"resultado"/"cc_ppca.json").read_text())["estado"],"pendiente")
            negativa=root/"otra-sesion"/"galeria-1"
            negativa.mkdir(parents=True)
            for i,imagen in enumerate(muestras(),1):
                cv2.imwrite(str(negativa/f"{i:02}.png"),imagen[:,:,::-1])
            guardar_json(negativa/"galeria.json",{"aprobada":True,"intento":1,
                         "imagenes":[f"{i:02}.png" for i in range(1,9)]})
            guardar_video(negativa.parent/"enrolamiento-1.avi",[muestras()[0][:,:,::-1].copy()])
            cache4=root/"cache4"
            clonar_con_negativa(cache,negativa,cache4)
            cfg4=root/"congelada4.json"
            calibrar(cache4,cfg4)
            evaluar(cache4,cfg4,root/"resultado4")
            with (root/"resultado4"/"comparacion.csv").open() as f:
                self.assertEqual(len(list(csv.DictReader(f))),4)
            cc=json.loads((root/"resultado4"/"cc_ppca.json").read_text())
            self.assertEqual(cc["modelo"]["modelo"],"CC-PPCA/NBC corporal")
            self.assertTrue((cache4/"cc_ppca.npz").is_file())
            from software.percepcion.guiada import informe
            (root/"informe4").mkdir()
            informe(root/"informe4",[root/"resultado4"],solo=False)
            with (root/"informe4"/"comparacion.csv").open() as f:
                cuatro=list(csv.DictReader(f))
            self.assertEqual(len(cuatro),4)
            self.assertEqual({r["estado"] for r in cuatro},{"evaluado"})
            self.assertIn("## cc_ppca",(root/"informe4"/"informe.md").read_text())

            from software.percepcion.comparar_sesion import clonar_con_mejoras
            cache6=root/"cache6"
            clonar_con_mejoras(cache4,cache6)
            with self.assertRaises(ValueError):
                evaluar(cache6,cfg4,root/"umbrales-antiguos")
            cfg6=root/"congelada6.json"
            calibrar(cache6,cfg6)
            evaluar(cache6,cfg6,root/"resultado6")
            with (root/"resultado6"/"comparacion.csv").open() as f:
                seis=list(csv.DictReader(f))
            self.assertEqual({r["metodo"] for r in seis},
                {"histograma","euclidea","mahalanobis","cc_ppca","euclidea_eqhist","mahalanobis_eqhist"})
            (root/"informe6").mkdir()
            informe(root/"informe6",[root/"resultado6"],solo=False)
            self.assertIn("## euclidea_eqhist",(root/"informe6"/"informe.md").read_text())

            from software.percepcion.comparar_sesion import clonar_con_agregacion
            cache_ag=root/"cache-agregacion"
            clonar_con_agregacion(cache6,cache_ag)
            with self.assertRaises(ValueError):
                evaluar(cache_ag,cfg6,root/"umbrales-otra-regla")
            cfg_ag=root/"calibracion-agregacion.json"
            calibrar(cache_ag,cfg_ag)
            evaluar(cache_ag,cfg_ag,root/"resultado-agregacion")
            (root/"informe-agregacion").mkdir()
            informe(root/"informe-agregacion",[root/"resultado-agregacion"],solo=False)
            with (root/"resultado-agregacion"/"comparacion.csv").open() as f:
                filas_ag=list(csv.DictReader(f))
            self.assertEqual(len(filas_ag),7)
            self.assertIn("histograma_mediana3",{f["metodo"] for f in filas_ag})
            self.assertEqual(sha256(cache6/"galeria/00.png"),sha256(cache_ag/"galeria/00.png"))

            # Integracion opcional con pesos oficiales reales; nunca descarga en tests.
            import os
            ruta_cnn=os.environ.get("LUMI_REID_XML")
            if ruta_cnn:
                from software.percepcion.reid_openvino import configuracion
                from software.percepcion.comparar_sesion import clonar_con_cnn
                cache7=root/"cache7"
                clonar_con_cnn(cache6,cache7,configuracion(ruta_cnn))
                cfg7=root/"congelada7.json"
                with self.assertRaises(ValueError):
                    evaluar(cache7,cfg6,root/"umbrales-sin-cnn")
                calibrar(cache7,cfg7)
                evaluar(cache7,cfg7,root/"resultado7")
                evaluar(cache7,cfg7,root/"resultado7b")
                (root/"informe7").mkdir()
                informe(root/"informe7",[root/"resultado7",root/"resultado7b"],solo=False)
                with (root/"informe7"/"comparacion.csv").open() as f:
                    siete=list(csv.DictReader(f))
                self.assertEqual(len(siete),7)
                self.assertIn("cnn_reid",{r["metodo"] for r in siete})
                recomendacion=json.loads((root/"informe7"/"recomendacion.json").read_text())
                self.assertTrue(recomendacion["decisiones_equivalentes"])
                with np.load(cache7/"cnn_reid.npz") as embeddings:
                    self.assertEqual(embeddings["galeria"].shape,(8,256))
                ficha=json.loads((root/"resultado7"/"cnn_reid.json").read_text())
                self.assertEqual(ficha["modelo"]["dimension"],256)
                cache9=root/"cache9"
                clonar_con_agregacion(cache7,cache9)
                cfg9=root/"congelada9.json"
                calibrar(cache9,cfg9)
                evaluar(cache9,cfg9,root/"resultado9")
                evaluar(cache9,cfg9,root/"resultado9b")
                (root/"informe9").mkdir()
                informe(root/"informe9",[root/"resultado9",root/"resultado9b"],solo=False)
                with (root/"informe9"/"comparacion.csv").open() as f:
                    filas9=list(csv.DictReader(f))
                self.assertEqual(len(filas9),9)
                self.assertIn("cnn_reid_mediana3",{f["metodo"] for f in filas9})
                self.assertTrue(json.loads((root/"informe9"/"recomendacion.json").read_text())["decisiones_equivalentes"])
                for metodo in ("histograma","cnn_reid"):
                    prev=(root/"resultado7"/f"{metodo}-frames.jsonl").read_text()
                    nuevo=(root/"resultado9"/f"{metodo}-frames.jsonl").read_text()
                    def decisiones(texto):
                        return [(r["secuencia"],r["frame"],r["seleccion"]) for r in map(json.loads,texto.splitlines())]
                    self.assertEqual(decisiones(prev),decisiones(nuevo))


            cv2.imwrite(str(cache4/"galeria-negativa"/"00.png"),np.zeros((128,64,3),np.uint8))
            with self.assertRaisesRegex(ValueError,"negativa cambio"):
                evaluar(cache4,cfg4,root/"resultado5")
            cv2.imwrite(str(cache/"galeria"/"00.png"),np.zeros((128,64,3),np.uint8))
            with self.assertRaisesRegex(ValueError,"galeria cambio"):
                evaluar(cache,cfg,root/"resultado2")

    def test_calibracion_requiere_negativos(self):
        fila={"secuencia":"a","escenario":"x","tiempo_s":0,"objetivo":"objetivo",
              "referencia":[{"id":"objetivo","bbox":[0,0,10,20]}],
              "candidatos":[{"bbox":[0,0,10,20]}],"distancias":[.1]}
        with self.assertRaisesRegex(ValueError,"escena vacia"):
            elegir_parametros([fila])


def guardar_video(ruta, frames):
    video = Video(ruta, 10, frames[0])
    try:
        for frame in frames:
            video.escribir(frame)
    finally:
        video.cerrar()


if __name__ == "__main__":
    unittest.main()
