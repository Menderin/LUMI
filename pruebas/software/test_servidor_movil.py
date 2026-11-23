import base64
import json
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import cv2
import numpy as np

from software.percepcion.seleccion_persona import SeleccionPersona
from software.percepcion.servidor_movil import BancoVision, manejador


def argumentos():
    return SimpleNamespace(metodo="histograma",umbral=.45,margen=.08,fps_proceso=10)


def imagen(indice=0):
    frame=np.zeros((480,640,3),np.uint8)
    frame[40:400,60:200]=(10,30,220)
    frame[100:170,85:170]=np.random.default_rng(indice).integers(20,150,(70,85,3),dtype=np.uint8)
    frame[40:400,380:520]=(220,30,10)
    return frame


CAJAS=[(60,40,200,400),(380,40,520,400)]


class SeleccionMovil(unittest.TestCase):
    def test_asocia_reordenamiento_y_rechaza_superposicion(self):
        s=SeleccionPersona()
        s.caja=CAJAS[0]
        self.assertEqual(s.actualizar(CAJAS[::-1])[0],1)
        self.assertIsNone(s.actualizar([CAJAS[0],(70,45,210,400)])[0])
        self.assertIsNone(s.caja)

    def test_captura_solo_elegido_aunque_haya_dos_personas(self):
        with tempfile.TemporaryDirectory() as carpeta:
            b=BancoVision(argumentos(),Path(carpeta))
            snap=b.procesar(imagen(),CAJAS,0)
            b.accion({"accion":"iniciar"},.1)
            b.accion({"accion":"seleccionar","frame_id":snap["frame_id"],"candidato":0},.2)
            b.accion({"accion":"capturar"},.3)
            for i in range(160):
                b.procesar(imagen(i),CAJAS if i%2==0 else CAJAS[::-1],.4+i*.1)
            self.assertEqual(b.sesion.registro.estado,"revision")
            self.assertEqual(len(b.sesion.registro.muestras),24)
            for muestra in b.sesion.registro.muestras:
                self.assertGreater(muestra[:,:,2].mean()-muestra[:,:,0].mean(),100)
            self.assertEqual(b.revision["recortes"],24)
            self.assertTrue(all(len(x["cajas_escena"])==2 and len(x["cajas"])==1 for x in b.registros))
            b.accion({"accion":"confirmar"},17)
            self.assertEqual(b.sesion.registro.estado,"listo")
            self.assertFalse(b.estado()["movimiento_habilitado"])
            self.assertTrue((Path(carpeta)/"galeria-1/galeria.json").exists())
            b.procesar(imagen(),CAJAS,17.1)
            b.accion({"accion":"iniciar_seguimiento"},17.2)
            self.assertEqual(b.sesion.registro.estado,"siguiendo")
            b.procesar(imagen(),[],17.3)
            self.assertEqual(b.sesion.registro.estado,"perdido")

    def test_toque_caducado_y_no_cambia_objetivo_durante_captura(self):
        with tempfile.TemporaryDirectory() as carpeta:
            b=BancoVision(argumentos(),Path(carpeta))
            snap=b.procesar(imagen(),CAJAS,0)
            b.accion({"accion":"iniciar"},.1)
            with self.assertRaisesRegex(ValueError,"antigua"):
                b.accion({"accion":"seleccionar","frame_id":snap["frame_id"],"candidato":0},2)
            with self.assertRaisesRegex(ValueError,"Candidato"):
                b.accion({"accion":"seleccionar","frame_id":snap["frame_id"],"candidato":True},.2)
            b.accion({"accion":"seleccionar","frame_id":snap["frame_id"],"candidato":0},.2)
            b.accion({"accion":"capturar"},.3)
            with self.assertRaisesRegex(ValueError,"no cambiar"):
                b.accion({"accion":"seleccionar","frame_id":snap["frame_id"],"candidato":1},.4)
            b.procesar(imagen(),CAJAS,3.4)
            b.procesar(imagen(),[CAJAS[1]],3.5)
            self.assertEqual(b.sesion.registro.estado,"fallo")
            self.assertEqual(len(b.sesion.registro.muestras),0)
            self.assertIsNone(b.video)

    def test_api_sin_movimiento_y_snapshot_atomico(self):
        with tempfile.TemporaryDirectory() as carpeta:
            b=BancoVision(argumentos(),Path(carpeta))
            snapshot=b.procesar(imagen(),CAJAS,time.monotonic())
            server=ThreadingHTTPServer(("127.0.0.1",0),manejador(b))
            server.daemon_threads=True
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            base=f"http://127.0.0.1:{server.server_port}"
            try:
                with urlopen(base+"/api/vision/frame") as response:
                    body=json.load(response)
                self.assertEqual(body["frame_id"],snapshot["frame_id"])
                decoded=cv2.imdecode(np.frombuffer(base64.b64decode(body["jpeg"]),np.uint8),cv2.IMREAD_COLOR)
                self.assertEqual(decoded.shape[:2],(body["alto"],body["ancho"]))
                self.assertEqual(body["cajas"],[list(x) for x in CAJAS])
                with urlopen(base+"/api/vision/frame.jpg") as response:
                    self.assertEqual(response.headers["Content-Type"],"image/jpeg")
                    metadata=json.loads(response.headers["X-Lumi-Metadata"])
                    binario=response.read()
                self.assertEqual(metadata["frame_id"],body["frame_id"])
                self.assertEqual(metadata["cajas"],body["cajas"])
                self.assertNotIn("jpeg",metadata)
                self.assertEqual(binario,base64.b64decode(body["jpeg"]))
                self.assertLess(len(binario),len(body["jpeg"]))

                import http.client
                conexion=http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=2)
                try:
                    conexion.request("GET","/api/vision/frame")
                    primera=conexion.getresponse()
                    self.assertEqual(primera.version,11)
                    self.assertEqual(primera.status,200)
                    primera.read()
                    sock=conexion.sock
                    conexion.request("GET","/api/estado")
                    segunda=conexion.getresponse()
                    self.assertEqual(segunda.status,200)
                    segunda.read()
                    self.assertIs(conexion.sock,sock)
                finally:
                    conexion.close()

                with urlopen(base+"/api/webrtc/estado") as response:
                    self.assertFalse(json.load(response)["habilitado"])
                with self.assertRaises(HTTPError) as unavailable:
                    urlopen(Request(base+"/api/webrtc/offer",data=b'{}',headers={"Content-Type":"application/json"}))
                self.assertEqual(unavailable.exception.code,503)
                unavailable.exception.close()

                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(base+"/api/movimiento",data=b'{}',headers={"Content-Type":"application/json"}))
                self.assertEqual(error.exception.code,403)
                error.exception.close()
            finally:
                server.shutdown();server.server_close();thread.join(timeout=2)


if __name__=="__main__":
    unittest.main()
