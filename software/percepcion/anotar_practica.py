"""Anotar manualmente clips de practica, sin usar predicciones como etiquetas."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from .practica import ventana_visible, guardar_json, normalizar_tecla, botones, callback_botones


def elegir_objetivo(ventana, frame, personas):
    """Elegir identidad revisada con tecla o clic, sin volver a la terminal."""
    cola=[]
    alto,ancho=frame.shape[:2]
    def clic(evento,x,y,flags,parametro):
        if evento != cv2.EVENT_LBUTTONDOWN:
            return
        if y >= alto-42:
            cola.append(0)
            return
        for i,persona in enumerate(personas,1):
            a,b,r,s=persona["bbox"]
            if a <= x <= r and b <= y <= s:
                cola.append(i)
                return
    cv2.setMouseCallback(ventana,clic)
    while True:
        vista=frame.copy()
        cv2.rectangle(vista,(0,0),(ancho-1,48),(20,20,20),-1)
        cv2.putText(vista,"Clic en TU recuadro o numero. 0 = ausente",(6,20),
                    cv2.FONT_HERSHEY_SIMPLEX,.48,(255,255,255),1)
        cv2.rectangle(vista,(0,alto-42),(ancho-1,alto-1),(65,65,65),-1)
        cv2.putText(vista,"Objetivo ausente [0] | Esc interrumpe",(8,alto-16),
                    cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
        cv2.imshow(ventana,vista)
        tecla=normalizar_tecla(cv2.waitKey(50))
        if cola:
            return cola[0]
        if tecla == 27 or not ventana_visible(ventana):
            return None
        if ord("0") <= tecla <= ord("9") and tecla-ord("0") <= len(personas):
            return tecla-ord("0")


def pedir_revision(ventana, frame, indice):
    """Las teclas desconocidas no descartan un fotograma."""
    cola=[]
    vista=frame.copy()
    cv2.rectangle(vista,(0,0),(vista.shape[1]-1,50),(20,20,20),-1)
    cv2.putText(vista,f"REVISION frame {indice}: S / Enter para etiquetar",(8,20),
                cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
    cv2.putText(vista,"N omite el frame; no confirma identidad",(8,42),
                cv2.FONT_HERSHEY_SIMPLEX,.48,(255,255,255),1)
    zonas=botones(vista,[("Revisar [S]",ord("s")),("Omitir [N]",ord("n")),("Salir [Esc]",27)],
                  max(55,vista.shape[0]-44))
    cv2.setMouseCallback(ventana,callback_botones(zonas,cola))
    cv2.imshow(ventana,vista)
    while True:
        tecla=normalizar_tecla(cv2.waitKey(50))
        if cola:
            tecla=cola.pop(0)
        if tecla in (10,13):
            tecla=ord("s")
        if tecla in (ord("s"),ord("n"),27):
            return tecla
        if not ventana_visible(ventana):
            return 27


class SeleccionRecuadros:
    def __init__(self, ancho, alto):
        self.ancho, self.alto = ancho, alto
        self.cajas = []
        self.inicio = None
        self.fin = None

    def evento(self, evento, x, y, flags=0, parametro=None):
        punto = (max(0,min(self.ancho-1,x)), max(0,min(self.alto-1,y)))
        if evento == cv2.EVENT_LBUTTONDOWN and 0 <= x < self.ancho and 0 <= y < self.alto:
            self.inicio = punto
            self.fin = punto
        elif evento == cv2.EVENT_MOUSEMOVE and self.inicio is not None:
            self.fin = punto
        elif evento == cv2.EVENT_LBUTTONUP and self.inicio is not None:
            x0,y0 = self.inicio
            x1,y1 = punto
            izquierda,arriba = min(x0,x1),min(y0,y1)
            ancho,alto = abs(x1-x0),abs(y1-y0)
            if ancho >= 3 and alto >= 3:
                self.cajas.append((izquierda,arriba,ancho,alto))
            self.inicio = self.fin = None


def seleccionar_recuadros(ventana, frame):
    """Soltar el raton agrega un recuadro; boton o Espacio confirma la lista."""
    alto,ancho=frame.shape[:2]
    seleccion=SeleccionRecuadros(ancho,alto)
    cola=[]
    lienzo_base = np.zeros((alto+86,ancho,3),dtype=frame.dtype)
    zonas=botones(lienzo_base,[
        ("Confirmar [Esp]",32),("Deshacer [Z]",ord("z")),
        ("Escena vacia [0]",ord("0")),("Cancelar [Esc]",27)],alto+43)
    pulsar=callback_botones(zonas,cola)
    def mouse(evento,x,y,flags,parametro):
        seleccion.evento(evento,x,y,flags,parametro)
        pulsar(evento,x,y,flags,parametro)
    cv2.setMouseCallback(ventana,mouse)
    while True:
        vista=lienzo_base.copy()
        vista[:alto]=frame
        for i,(x,y,w,h) in enumerate(seleccion.cajas,1):
            cv2.rectangle(vista,(x,y),(x+w,y+h),(0,230,0),2)
            cv2.putText(vista,str(i),(x,max(20,y)),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,230,0),2)
        if seleccion.inicio is not None:
            cv2.rectangle(vista,seleccion.inicio,seleccion.fin,(0,200,255),1)
        texto=f"Arrastra y suelta para agregar personas ({len(seleccion.cajas)}). Luego Confirmar."
        escala=min(.5,(ancho-12)/max(1,cv2.getTextSize(texto,cv2.FONT_HERSHEY_SIMPLEX,1,1)[0][0]))
        cv2.putText(vista,texto,(6,alto+23),cv2.FONT_HERSHEY_SIMPLEX,escala,(255,255,255),1)
        cv2.imshow(ventana,vista)
        tecla=normalizar_tecla(cv2.waitKey(50))
        if cola:
            tecla=cola.pop(0)
        if tecla == 27 or not ventana_visible(ventana):
            return None
        if tecla in (10,13,32,ord("a")):
            if seleccion.cajas:
                return list(seleccion.cajas)
        elif tecla == ord("z") and seleccion.cajas:
            seleccion.cajas.pop()
        elif tecla == ord("0"):
            return []


def anotar(video, split, escenario, paso):
    ruta = video.with_suffix(".anotaciones.json")
    datos = {"split": split, "escenario": escenario, "objetivo": "objetivo", "frames": {}}
    if ruta.exists():
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        if (datos["split"], datos["escenario"]) != (split, escenario):
            raise ValueError("La anotacion existente pertenece a otra particion o escenario")
    captura = cv2.VideoCapture(str(video))
    if not captura.isOpened():
        raise ValueError("No se pudo abrir el video")
    ventana = "Anotar personas (S revisar frame, N omitir, Esc salir)"
    guardar_json(ruta,datos)
    try:
        cv2.namedWindow(ventana, cv2.WINDOW_NORMAL)
        indice = 0
        interrumpida = False
        while True:
            ok, frame = captura.read()
            if not ok:
                break
            if indice % paso == 0 and str(indice) not in datos["frames"]:
                tecla = pedir_revision(ventana,frame,indice)
                if tecla == 27 or not ventana_visible(ventana):
                    interrumpida = True
                    break
                if tecla == ord("s"):
                    print("Arrastra y suelta para cada persona. Confirmar o Espacio termina; 0 confirma escena vacia.")
                    cajas = seleccionar_recuadros(ventana,frame)
                    if cajas is None:
                        interrumpida = True
                        break
                    personas = []
                    for i, (x, y, w, h) in enumerate(cajas, 1):
                        caja = [int(x), int(y), int(x+w), int(y+h)]
                        personas.append({"id": f"otro-{i}", "bbox": caja})
                        cv2.putText(frame, str(i), (int(x), max(20, int(y))),
                                    cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 0), 2)
                    if personas:
                        numero = elegir_objetivo(ventana,frame,personas)
                        if numero is None:
                            interrumpida = True
                            break
                        if numero:
                            personas[numero-1]["id"] = "objetivo"
                    datos["frames"][str(indice)] = personas
                    guardar_json(ruta, datos)
            indice += 1
    finally:
        captura.release()
        cv2.destroyAllWindows()
    print(ruta)
    if indice == 0 and not interrumpida:
        raise ValueError(f"El video no entrego fotogramas decodificables: {video}")
    if not datos["frames"]:
        print("Sin etiquetas revisadas. S o Enter dibuja personas; N solo omite. Retoma con --continuar.",flush=True)
        return False
    return not interrumpida


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--split", choices=["calibracion", "evaluacion"], required=True)
    parser.add_argument("--escenario", required=True, help="Incluir direccion de luz y cruce/oclusion")
    parser.add_argument("--paso", type=int, default=5, help="5 frames a 10 FPS nominales; 1 en ventanas criticas")
    args = parser.parse_args()
    if args.paso < 1:
        parser.error("--paso debe ser positivo")
    try:
        anotar(args.video.resolve(), args.split, args.escenario, args.paso)
    except (ValueError, OSError, cv2.error) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
