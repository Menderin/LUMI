import json
import csv
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from software.percepcion.bateria_reutilizable import ejecutar, identificar, validar_particiones
from software.percepcion.comparar_sesion import sha256
from software.percepcion.diagnosticar_sesion import describir, diagnosticar
from software.percepcion.practica import guardar_json, Video


def cache_sintetica(root, *, solo=False):
    """Dos clases de color artificiales; no representa resultados de identidad humana."""
    root = Path(root)
    (root/"galeria").mkdir(parents=True)
    (root/"recortes").mkdir()
    rng = np.random.default_rng(429)
    hashes = []
    muestras = []
    for i in range(24):
        image = np.full((128,64,3),(10,30,220),np.uint8)
        image[10+i:20+i,10:50] = rng.integers(0,150,(10,40,3),dtype=np.uint8)
        path = root/"galeria"/f"{i:02}.png"
        cv2.imwrite(str(path),image);hashes.append(sha256(path));muestras.append(image)
    objetivo = root/"recortes/objetivo.png"
    distractor = root/"recortes/distractor.png"
    cv2.imwrite(str(objetivo),muestras[0]);cv2.imwrite(str(distractor),np.full((128,64,3),(220,30,10),np.uint8))
    a = {"bbox":[20,20,84,148],"imagen":"recortes/objetivo.png","sha256":sha256(objetivo)}
    b = {"bbox":[150,20,214,148],"imagen":"recortes/distractor.png","sha256":sha256(distractor)}
    frames = []
    for split in ("calibracion","evaluacion"):
        escenas = [("frente-perfiles",[a],[{"id":"objetivo","bbox":a["bbox"]}]),
                   ("ausente",[],[]),
                   ("oclusion",[],[{"id":"objetivo","bbox":a["bbox"]}])]
        if not solo:
            escenas += [("distractor",[b],[{"id":"otro","bbox":b["bbox"]}]),
                        ("cruce",[a,b],[{"id":"objetivo","bbox":a["bbox"]},{"id":"otro","bbox":b["bbox"]}])]
        for i,(escenario,candidatos,ref) in enumerate(escenas):
            frames.append({"secuencia":split,"frame":i,"split":split,"escenario":escenario,
                "objetivo":"objetivo","referencia":ref,"candidatos":candidatos,
                "tiempo_s":i*.1,"detector_ms":10.})
    guardar_json(root/"cache.json",{"galeria_sha256":hashes,"enrolamiento_sha256":"enrolamiento",
                 "videos":[],"frames":frames,"versiones":{"opencv":cv2.__version__,"numpy":np.__version__}})
    return root


class Diagnostico(unittest.TestCase):
    def base(self):
        return {"objetivo":"a","referencia":[{"id":"a","bbox":[0,0,20,40]},
                        {"id":"b","bbox":[40,0,60,40]}],
                "candidatos":[{"bbox":[0,0,20,40]},{"bbox":[40,0,60,40]}],
                "seleccion":None,"motivo":"rechazo"}

    def test_distingue_detector_identidad_ambiguedad_y_sustitucion(self):
        r = self.base()
        self.assertEqual(describir(r)["categoria"],"rechazo_con_objetivo_detectado")
        r["motivo"] = "ambiguedad"
        self.assertEqual(describir(r)["ambiguos_detectados"],1)
        r["seleccion"] = 1
        self.assertEqual(describir(r)["sustituciones_frames"],1)
        self.assertEqual(describir(r)["identidad_seleccionada"],"b")
        r["seleccion"] = 0
        self.assertEqual(describir(r)["categoria"],"acierto_objetivo")
        r["seleccion"] = None;r["candidatos"] = []
        self.assertEqual(describir(r)["categoria"],"objetivo_sin_deteccion_compatible")
        self.assertEqual(describir(r)["rechazos_identificador"],0)

    def test_caja_no_asociada_no_inventa_identidad(self):
        r = self.base();r["candidatos"] = [{"bbox":[100,0,120,40]}];r["seleccion"] = 0
        d = describir(r)
        self.assertIsNone(d["identidad_seleccionada"])
        self.assertEqual(d["sustituciones_frames"],0)
        self.assertEqual(d["aceptados_sin_referencia"],1)
        r["referencia"] = []
        self.assertEqual(describir(r)["falsas_aceptaciones"],1)
        r["seleccion"] = None
        self.assertEqual(describir(r)["categoria"],"rechazo_correcto_sin_objetivo")


class BateriaReutilizable(unittest.TestCase):
    def test_cache_d0_e1_sin_camara_y_originales_intactos(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);source = cache_sintetica(root/"cache")
            antes = {str(p.relative_to(source)):sha256(p) for p in source.rglob("*") if p.is_file()}
            with patch("cv2.VideoCapture",side_effect=AssertionError("No abrir video/camara en modo cache")), \
                 patch("cv2.imshow",side_effect=AssertionError("No abrir GUI")):
                out = ejecutar(source,root/"salida",repeticiones=2,mejorar_pca=True,datos_sinteticos=True)
            self.assertEqual(antes,{str(p.relative_to(source)):sha256(p) for p in source.rglob("*") if p.is_file()})
            cfg = json.loads((out/"umbrales.json").read_text())
            self.assertIn("histograma_mediana3",cfg["metodos"])
            self.assertIn("euclidea_eqhist",cfg["metodos"])
            info = json.loads((out/"ejecucion.json").read_text())
            self.assertEqual(info["estado"],"completa")
            self.assertTrue(info["datos_sinteticos"])
            self.assertTrue((out/"comparacion-galeria.csv").is_file())
            d0 = json.loads((out/"diagnostico-D0/diagnostico.json").read_text())
            for grupos in d0["escenarios"].values():
                self.assertEqual(sum(g["revisados"] for g in grupos.values()),5)
                self.assertEqual(grupos["oclusion"]["perdidas_detector"],1)
                self.assertEqual(grupos["oclusion"]["rechazos_identificador"],0)
            self.assertTrue(json.loads((out/"recomendacion.json").read_text())["decisiones_equivalentes"])
            self.assertIsNone(json.loads((out/"recomendacion.json").read_text())["candidato"])
            with self.assertRaisesRegex(ValueError,"nueva"):
                ejecutar(source,out)

    def test_sesion_etiquetada_no_reabre_anotacion_y_no_acepta_faltantes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);cache = cache_sintetica(root/"cache")
            source = root/"sesion";source.mkdir()
            shutil.copytree(cache/"galeria",source/"galeria-1")
            guardar_json(source/"galeria-1/galeria.json",{"aprobada":True,"intento":1,
                         "imagenes":[f"{i:02}.png" for i in range(24)]})
            gallery = cv2.imread(str(cache/"galeria/00.png"))
            def video(path,frames):
                writer = Video(path,10,frames[0])
                for frame in frames:
                    writer.escribir(frame)
                writer.cerrar()
            video(source/"enrolamiento-1.avi",[np.zeros((240,320,3),np.uint8)])
            clips,decisiones = [],[]
            refs = [[{"id":"objetivo","bbox":[20,20,84,148]},{"id":"otro","bbox":[150,20,214,148]}],
                    [{"id":"otro","bbox":[150,20,214,148]}],[]]
            for j,split in enumerate(("calibracion","evaluacion")):
                path = source/f"{split}.avi";frames = []
                for i,ref in enumerate(refs):
                    frame = np.full((240,320,3),30+30*j,np.uint8)
                    for p in ref:
                        x,y,r,b = p["bbox"]
                        frame[y:b,x:r] = gallery if p["id"]=="objetivo" else (220,30,10)
                    frames.append(frame)
                    decisiones.append({"clip":path.name,"frame_clip":i,"cajas":json.dumps([p["bbox"] for p in ref]),
                                       "detector_ms":10.,"tiempo_monotonico_s":i*.1})
                video(path,frames)
                guardar_json(path.with_suffix(".anotaciones.json"),{"split":split,"escenario":"mixto",
                    "objetivo":"objetivo","frames":{str(i):ref for i,ref in enumerate(refs)}})
                clips.append({"video":path.name,"split":split,"escenario":"mixto"})
            with (source/"decisiones.csv").open("w",newline="") as f:
                w = csv.DictWriter(f,fieldnames=list(decisiones[0]));w.writeheader();w.writerows(decisiones)
            guardar_json(source/"guia.json",{"terminada":True,"cancelada":False,"solo":False,
                         "galeria":"galeria-1","clips":clips})
            originales = {p.name:sha256(p) for p in source.rglob("*") if p.is_file()}
            with patch("software.percepcion.guiada.anotar",side_effect=AssertionError("No anotar")), \
                 patch("cv2.imshow",side_effect=AssertionError("No GUI")):
                out = ejecutar(source,root/"salida",repeticiones=1,datos_sinteticos=True)
            self.assertTrue((out/"diagnostico-D0/informe.md").exists())
            self.assertEqual(originales,{p.name:sha256(p) for p in source.rglob("*") if p.is_file()})
            (source/"calibracion.anotaciones.json").unlink()
            with self.assertRaisesRegex(ValueError,"etiquetas"):
                ejecutar(source,root/"sin-etiquetas",repeticiones=1)

    def test_solo_exige_flag_y_nunca_elige_ganador(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);source = cache_sintetica(root/"cache",solo=True)
            with self.assertRaisesRegex(ValueError,"distractores"):
                ejecutar(source,root/"rechazo",repeticiones=1)
            self.assertEqual(json.loads((root/"rechazo/ejecucion.json").read_text())["estado"],"fallida")
            out = ejecutar(source,root/"piloto",repeticiones=1,permitir_sin_distractores=True)
            self.assertIsNone(json.loads((out/"recomendacion.json").read_text())["candidato"])
            self.assertIn("No hay distractores",(out/"diagnostico-D0/informe.md").read_text())

    def test_rechaza_fuga_y_no_inicia_anotacion_de_sesion_incompleta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);source = cache_sintetica(root/"cache")
            cache = json.loads((source/"cache.json").read_text())
            cache["frames"][-1]["secuencia"] = "calibracion"
            with self.assertRaisesRegex(ValueError,"Fuga"):
                validar_particiones(cache,False)
            sesion = root/"sesion";sesion.mkdir()
            guardar_json(sesion/"guia.json",{"terminada":False,"cancelada":False})
            with patch("cv2.VideoCapture",side_effect=AssertionError("No capturar")), \
                 patch("cv2.imshow",side_effect=AssertionError("No GUI")):
                with self.assertRaisesRegex(ValueError,"incompleta"):
                    ejecutar(sesion,root/"incompleta")
            with self.assertRaisesRegex(ValueError,"Indica una sesion"):
                identificar(root)

if __name__ == "__main__":
    unittest.main()
