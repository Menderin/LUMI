"""Acciones de enrolamiento comunes para ventana y futuro adaptador movil."""
from .estado import Enrolamiento


class SesionEnrolamiento:
    acciones = ("iniciar", "confirmar", "cancelar", "repetir", "iniciar_seguimiento", "reanudar")

    def __init__(self):
        self.registro = Enrolamiento()
        self.cuenta_hasta = None

    def accion(self, nombre, ahora, *, personas=0, objetivo=False):
        if nombre not in self.acciones:
            raise ValueError(f"Accion desconocida: {nombre}")
        r = self.registro
        if nombre == "cancelar":
            r.descartar()
            self.cuenta_hasta = None
            return True
        if nombre in ("iniciar", "repetir"):
            if r.intentos >= 5 or personas != 1:
                return False
            if nombre == "iniciar" and r.estado not in ("espera", "fallo"):
                return False
            r.descartar()
            r.estado = "preparando"
            self.cuenta_hasta = ahora + 3
            return True
        if nombre == "confirmar":
            return r.confirmar_revision(ahora)
        esperado = "listo" if nombre == "iniciar_seguimiento" else "perdido"
        if r.estado != esperado or not objetivo:
            return False
        return r.actualizar(ahora, pulsacion=True, objetivo=True)

    def actualizar(self, ahora, *, personas=0, recorte=None, objetivo=False):
        r = self.registro
        if self.cuenta_hasta is not None:
            if ahora < self.cuenta_hasta:
                return False
            self.cuenta_hasta = None
            r.estado = "espera"
            r.actualizar(ahora, pulsacion=True)
        return r.actualizar(ahora, personas=personas, recorte=recorte,
                            objetivo=objetivo, pedir_revision=True)

    def estado(self, ahora):
        r = self.registro
        return {"estado": r.estado, "intentos": r.intentos,
                "segundos_restantes": max(0, (self.cuenta_hasta or r._inicio + 10) - ahora)
                if r.estado in ("preparando", "enrolando") else 0,
                "muestras": len(r.muestras)}
