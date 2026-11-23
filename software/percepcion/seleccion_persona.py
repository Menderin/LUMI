"""Seleccion temporal conservadora; no sustituye identificacion ni revision humana."""
from .experimentos import iou


class SeleccionPersona:
    def __init__(self):
        self.caja = None

    def limpiar(self):
        self.caja = None

    def actualizar(self, cajas):
        if self.caja is None:
            return None, "Selecciona una persona"
        candidatos = sorted(((iou(self.caja, caja), i) for i, caja in enumerate(cajas)), reverse=True)
        if not candidatos or candidatos[0][0] < .30:
            self.limpiar()
            return None, "Se perdio la seleccion; vuelve a seleccionar"
        if len(candidatos) > 1 and candidatos[0][0] - candidatos[1][0] < .15:
            self.limpiar()
            return None, "Seleccion ambigua; separa a las personas y repite"
        indice = candidatos[0][1]
        a = cajas[indice]
        for j, b in enumerate(cajas):
            if j == indice:
                continue
            inter = max(0, min(a[2],b[2])-max(a[0],b[0])) * max(0,min(a[3],b[3])-max(a[1],b[1]))
            menor = min((a[2]-a[0])*(a[3]-a[1]),(b[2]-b[0])*(b[3]-b[1]))
            if inter / max(1,menor) > .15:
                self.limpiar()
                return None, "Personas superpuestas; repite con espacio entre ambas"
        self.caja = tuple(a)
        return indice, "Persona seleccionada"
