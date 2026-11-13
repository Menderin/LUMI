"""Máquina de estados independiente de GPIO y motores."""
from dataclasses import dataclass, field


@dataclass
class Enrolamiento:
    minimo: int = 8
    estado: str = field(default="espera", init=False)
    intentos: int = field(default=0, init=False)
    galeria: tuple = field(default=(), init=False)
    _muestras: list = field(default_factory=list, init=False)
    _inicio: float = field(default=0, init=False)
    _ultima: float = field(default=float("-inf"), init=False)

    def __post_init__(self):
        if not 1 <= self.minimo <= 12:
            raise ValueError("El mínimo debe estar entre 1 y 12")

    def actualizar(self, ahora, *, pulsacion=False, objetivo=False,
                   personas=0, recorte=None, cobertura=False):
        """Tiempo monotónico, pulsación por flanco y recorte ya validado.

        objetivo indica coincidencia inequívoca, vigente y verificada.
        cobertura la confirma el operador del piloto.
        """
        if self.estado == "enrolando":
            if ahora - self._inicio >= 10:
                if cobertura and len(self._muestras) >= self.minimo:
                    self.galeria = tuple(self._muestras)
                    self.estado = "listo"
                else:
                    self.estado = "fallo"
                self._muestras.clear()
                self._inicio = ahora
            elif (personas == 1 and recorte is not None
                  and len(self._muestras) < 12 and ahora - self._ultima >= 0.8):
                self._muestras.append(recorte.copy())
                self._ultima = ahora
        elif self.estado in ("espera", "fallo"):
            if pulsacion and self.intentos < 5:
                self.intentos += 1
                self.estado = "enrolando"
                self._inicio = ahora
                self._ultima = float("-inf")
        elif self.estado == "siguiendo":
            if not objetivo:
                self.estado = "perdido"
        elif pulsacion and objetivo:
            self.estado = "siguiendo"
        return self.estado == "siguiendo" and objetivo

    def leds(self, ahora):
        """Devuelve (verde, rojo, ámbar)."""
        fase = int(max(0, ahora - self._inicio) * 4)
        return (
            self.estado == "siguiendo"
            or (self.estado == "listo" and fase < 6 and fase % 2 == 0),
            self.estado == "perdido",
            self.estado == "enrolando" or (self.estado == "fallo" and fase % 2 == 0),
        )

