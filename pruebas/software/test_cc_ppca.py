import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from software.percepcion.cc_ppca import CCPPCA
from software.percepcion.experimentos import gris
from software.percepcion.comparar_sesion import agregar_negativa
from software.percepcion.practica import guardar_json,Video


def galeria(semilla, color):
    rng=np.random.default_rng(semilla)
    imagenes=[]
    for i in range(12):
        x=np.full((128,64,3),color,np.uint8)
        x[20:100,10:54]=rng.integers(0,220,(80,44,3),dtype=np.uint8)
        imagenes.append(x)
    return imagenes


class CuartoExperimento(unittest.TestCase):
    def test_proyeccion_y_regla_del_articulo(self):
        a,b=galeria(1,(10,30,220)),galeria(2,(220,30,10))
        m=CCPPCA(a,b)
        self.assertEqual(m.q,8)
        conjunto=np.stack([gris(x,128) for x in a+b]).astype(np.float64)
        scores=[]
        x=conjunto[0]
        for imagenes,c in zip((a,b),m.clases):
            self.assertGreater(c["sigma2"],0)
            datos=np.stack([gris(t,128) for t in imagenes]).astype(np.float64)
            mu=datos.mean(axis=0)
            _,s,vt=np.linalg.svd(datos-mu,full_matrices=False)
            lam=s[:m.q]**2/len(datos)
            w=vt[:m.q].T*np.sqrt(lam-c["sigma2"])
            posterior=np.linalg.solve(w.T@w+c["sigma2"]*np.eye(m.q),w.T@(x-mu))
            propio=-.5*(posterior@posterior+m.q*np.log(2*np.pi))
            z=(conjunto-mu)@w@np.linalg.inv(w.T@w+c["sigma2"]*np.eye(m.q))
            logs=-.5*((z*z).sum(axis=1)+m.q*np.log(2*np.pi))
            nu=logs.max()+np.log(np.exp(logs-logs.max()).mean())
            self.assertAlmostEqual(c["log_nu"],nu,places=8)
            scores.append(propio+nu)
        self.assertAlmostEqual(m.distancia(a[0]),scores[1]-scores[0],places=8)
        with tempfile.TemporaryDirectory() as carpeta:
            ruta=Path(carpeta)/"modelo.npz"
            m.guardar(ruta)
            with np.load(ruta) as datos:
                self.assertEqual(int(datos["q"]),8)
                self.assertTrue(np.isfinite(datos["objetivo_sigma2"]))

    def test_galeria_degenerada_informa_fallo(self):
        constante=[np.zeros((128,64,3),np.uint8)]*12
        with self.assertRaisesRegex(ValueError,"sin variacion"):
            CCPPCA(constante,galeria(2,(220,30,10)))

    def test_rechaza_fuente_negativa_de_evaluacion(self):
        from software.percepcion.comparar_sesion import sha256
        with tempfile.TemporaryDirectory() as carpeta:
            root=Path(carpeta)
            negativa=root/"negativa"/"galeria-1"
            negativa.mkdir(parents=True)
            imagenes=galeria(2,(220,30,10))
            nombres=[]
            for i,x in enumerate(imagenes):
                nombre=f"{i:02}.png"
                nombres.append(nombre)
                cv2.imwrite(str(negativa/nombre),x)
            guardar_json(negativa/"galeria.json",{"aprobada":True,"intento":1,"imagenes":nombres})
            video=negativa.parent/"enrolamiento-1.avi"
            escritor=Video(video,10,imagenes[0])
            escritor.escribir(imagenes[0])
            escritor.cerrar()
            cache={"galeria_sha256":[],"videos":[{"sha256":sha256(video)}]}
            with self.assertRaisesRegex(ValueError,"calibracion/evaluacion"):
                agregar_negativa(root,cache,negativa)


if __name__=="__main__":
    unittest.main()
