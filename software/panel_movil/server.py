"""Panel de banco local de LUMI."""
from .banco import Banco

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from software.percepcion.enrolamiento.estado import Enrolamiento


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--puerto", type=int, default=8080)
    parser.add_argument("--camara", type=int)
    parser.add_argument('--banco-android', action='store_true')
    args = parser.parse_args()
    pagina = Path(__file__).with_name("index.html").read_bytes()
    estado = Enrolamiento()
    banco = Banco()
    lock = threading.Lock()
    imagen = None
    detener = threading.Event()
    captura = None
    hilo = None

    if args.camara is not None:
        import cv2

        captura = cv2.VideoCapture(args.camara)
        if not captura.isOpened():
            captura.release()
            parser.error("No se pudo abrir la cámara")

        def leer():
            nonlocal imagen
            while not detener.is_set():
                ok, frame = captura.read()
                if ok:
                    alto, ancho = frame.shape[:2]
                    escala = min(1, 640 / ancho)
                    frame = cv2.resize(frame, (max(1, round(ancho * escala)),
                                              max(1, round(alto * escala))))
                    ok, jpeg = cv2.imencode(".jpg", frame)
                    imagen = jpeg.tobytes() if ok else None
                else:
                    imagen = None
                detener.wait(.15)

        hilo = threading.Thread(target=leer, daemon=True)
        hilo.start()

    class Panel(BaseHTTPRequestHandler):
        def responder(self, codigo, tipo, datos):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def json(self, codigo, datos):
            self.responder(codigo, "application/json", json.dumps(datos).encode())

        def do_GET(self):
            if self.path == "/":
                self.responder(200, "text/html; charset=utf-8", pagina)
            elif self.path == "/foto.jpg":
                foto = imagen
                if foto is None:
                    self.json(503, {"error": "Cámara sin imagen"})
                else:
                    self.responder(200, "image/jpeg", foto)
            elif self.path == "/api/estado":
                with lock:
                    ahora = time.monotonic()
                    estado.actualizar(ahora)
                    self.json(200, {
                        "estado": estado.estado, "intentos": estado.intentos,
                        "leds": estado.leds(ahora), "camara": imagen is not None,
                        "banco": banco.estado(ahora) if args.banco_android else None,
                    })
            else:
                self.send_error(404)

        def do_POST(self):
            partes = self.path.split("/")
            if args.banco_android and len(partes) == 5 and partes[:3] == ["", "api", "banco"]:
                if self.headers.get_content_type() != "application/json":
                    self.json(415, {"error": "Se requiere application/json"})
                    return
                with lock:
                    aceptada = banco.orden(partes[3], partes[4], time.monotonic())
                self.json(200 if aceptada else 409, {
                    "mensaje": "Solicitud simulada registrada" if aceptada else "Acción no disponible",
                })
                return
            if self.path != "/api/enrolamiento":
                self.send_error(404)
                return
            if self.headers.get("Content-Type") != "application/json":
                self.json(415, {"error": "Se requiere application/json"})
                return
            with lock:
                ahora = time.monotonic()
                estado.actualizar(ahora)
                if estado.estado not in ("espera", "fallo") or estado.intentos >= 5:
                    self.json(409, {"error": "El enrolamiento no está disponible"})
                    return
                estado.actualizar(ahora, pulsacion=True)
            self.json(202, {"estado": "enrolando"})

    try:
        with ThreadingHTTPServer((args.host, args.puerto), Panel) as servidor:
            print(f"Panel LUMI en http://{args.host}:{servidor.server_port}", flush=True)
            servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        detener.set()
        if hilo is not None:
            hilo.join(timeout=2)
            if not hilo.is_alive():
                captura.release()


if __name__ == "__main__":
    main()
