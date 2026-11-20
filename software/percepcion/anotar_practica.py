"""Anotar manualmente clips de practica, sin usar predicciones como etiquetas."""
import argparse
import json
from pathlib import Path

import cv2

from .practica import ventana_visible, guardar_json, normalizar_tecla


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
    try:
        cv2.namedWindow(ventana, cv2.WINDOW_NORMAL)
        indice = 0
        interrumpida = False
        while True:
            ok, frame = captura.read()
            if not ok:
                break
            if indice % paso == 0 and str(indice) not in datos["frames"]:
                vista = frame.copy()
                cv2.putText(vista, f"Frame {indice}: S anotar, N omitir", (8, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, .6, (255, 255, 255), 2)
                cv2.imshow(ventana, vista)
                tecla = normalizar_tecla(cv2.waitKey(0))
                if tecla == 27 or not ventana_visible(ventana):
                    interrumpida = True
                    break
                if tecla == ord("s"):
                    print("Selecciona TODAS las personas visibles: Enter siguiente recuadro, Esc termina.")
                    cajas = cv2.selectROIs(ventana, frame, showCrosshair=True, fromCenter=False)
                    personas = []
                    for i, (x, y, w, h) in enumerate(cajas, 1):
                        caja = [int(x), int(y), int(x+w), int(y+h)]
                        personas.append({"id": f"otro-{i}", "bbox": caja})
                        cv2.putText(frame, str(i), (int(x), max(20, int(y))),
                                    cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 0), 2)
                    cv2.imshow(ventana, frame)
                    cv2.waitKey(1)
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
