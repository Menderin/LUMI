"""Acciones de enrolamiento comunes para ventana y futuro adaptador movil."""
from .estado import Enrolamiento


class SesionEnrolamiento:
    acciones = ("iniciar", "confirmar", "cancelar", "repetir", "iniciar_seguimiento", "reanudar")

    def __init__(self, *, desde_video=False):
        self.registro = Enrolamiento()
        self.desde_video = desde_video
        self.duracion = 12 if desde_video else 10
        self.minimo = 20 if desde_video else 8
        self.maximo = 24 if desde_video else 12
        self.mensaje = "Pulsa E o Enrolar para comenzar"
        self.cuenta_hasta = None
        self.eventos = []

    def accion(self, nombre, ahora, *, personas=0, objetivo=False):
        anterior = self.registro.estado
        aceptada = self._accion(nombre, ahora, personas=personas, objetivo=objetivo)
        self.eventos.append({"tiempo_s": ahora, "accion": nombre, "aceptada": aceptada,
                             "estado_antes": anterior, "estado_despues": self.registro.estado,
                             "mensaje": self.mensaje})
        return aceptada

    def _accion(self, nombre, ahora, *, personas=0, objetivo=False):
        if nombre not in self.acciones:
            raise ValueError(f"Accion desconocida: {nombre}")
        r = self.registro
        if nombre == "cancelar":
            r.descartar()
            self.cuenta_hasta = None
            self.mensaje = "Cancelado. Pulsa E o Enrolar para empezar"
            return True
        if nombre in ("iniciar", "repetir"):
            if r.intentos >= 5:
                self.mensaje = "Limite de cinco intentos; inicia otra sesion de evaluacion"
                return False
            if personas != 1:
                self.mensaje = "Debe haber exactamente una persona visible"
                return False
            if nombre == "iniciar" and r.estado not in ("espera", "fallo"):
                self.mensaje = "Cancela o pulsa Repetir para un nuevo enrolamiento"
                return False
            r.descartar()
            r.estado = "preparando"
            self.cuenta_hasta = ahora + 3
            self.mensaje = "Preparate para girar durante la captura"
            return True
        if nombre == "confirmar":
            aceptada = r.confirmar_revision(ahora)
            self.mensaje = "Enrolamiento aprobado. Pulsa S o Seguir" if aceptada else "No hay revision pendiente"
            return aceptada
        if r.estado == "siguiendo":
            self.mensaje = "El seguimiento visual ya esta activo"
            return True
        esperado = "listo" if nombre == "iniciar_seguimiento" else "perdido"
        if r.estado != esperado:
            self.mensaje = "Primero completa y aprueba la revision del enrolamiento"
            return False
        if not objetivo:
            self.mensaje = "No hay coincidencia valida; vuelve al encuadre y revisa la distancia d"
            return False
        self.mensaje = "Seguimiento visual habilitado"
        return r.actualizar(ahora, pulsacion=True, objetivo=True)

    def actualizar(self, ahora, *, personas=0, recorte=None, objetivo=False):
        r = self.registro
        if self.cuenta_hasta is not None:
            if ahora < self.cuenta_hasta:
                return False
            self.cuenta_hasta = None
            r.estado = "espera"
            r.actualizar(ahora, pulsacion=True)
        if self.desde_video and r.estado == "enrolando":
            if ahora - r._inicio >= self.duracion:
                r.estado = "procesando"
            return False
        return r.actualizar(ahora, personas=personas, recorte=recorte,
                            objetivo=objetivo, pedir_revision=True)

    def completar_video(self, muestras):
        r = self.registro
        if r.estado != "procesando":
            raise ValueError("No hay captura pendiente de procesar")
        if len(muestras) < self.minimo:
            self.fallar(f"Solo {len(muestras)} recortes validos; se necesitan {self.minimo}")
            return False
        r._muestras = [m.copy() for m in muestras[:self.maximo]]
        r.estado = "revision"
        self.mensaje = f"Revisa los {len(r.muestras)} recortes y aprueba"
        return True

    def fallar(self, motivo):
        self.registro.descartar()
        self.registro.estado = "fallo"
        self.cuenta_hasta = None
        self.mensaje = motivo

    def estado(self, ahora):
        r = self.registro
        return {"estado": r.estado, "intentos": r.intentos,
                "segundos_restantes": max(0, (self.cuenta_hasta or r._inicio + self.duracion) - ahora)
                if r.estado in ("preparando", "enrolando") else 0,
                "muestras": len(r.muestras), "mensaje": self.mensaje}
