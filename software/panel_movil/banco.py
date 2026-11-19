"""Simulación de la API móvil. Sin salida a ROS o actuadores."""
import math


class Banco:
    def __init__(self):
        self.fase = "espera"
        self.fin = 0
        self.direccion = "parar"
        self.vence = 0

    def estado(self, ahora):
        if self.fase == "enrolando" and ahora >= self.fin:
            self.fase = "aprobado"
        if ahora >= self.vence:
            self.direccion = "parar"
        return dict(enrolamiento=self.fase, movimiento=self.direccion,
                    segundos=max(0, math.ceil(self.fin - ahora)))

    def orden(self, recurso, accion, ahora):
        self.estado(ahora)
        if recurso == "movimiento":
            if accion not in {"adelante", "atras", "izquierda", "derecha", "parar"}:
                return False
            if accion != "parar" and self.fase in {"enrolando", "aprobado"}:
                return False
            self.direccion = accion
            self.vence = ahora + .5
            return True
        if recurso != "enrolamiento":
            return False
        if accion == "nuevo" and self.fase not in {"enrolando", "aprobado"}:
            self.direccion = "parar"
            self.fase, self.fin = "enrolando", ahora + 10
        elif accion == "confirmar" and self.fase == "aprobado":
            self.fase = "confirmado"
        elif accion == "cancelar":
            self.direccion = "parar"
            self.fase, self.fin = "espera", 0
        else:
            return False
        return True
