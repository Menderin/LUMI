"""Estado de direccion visual, sin transporte ni actuacion."""
from dataclasses import dataclass


@dataclass
class DireccionSimulada:
    zona: str = "detenido"

    def actualizar(self, caja, ancho, *, buscando=False):
        if caja is None:
            self.zona = "buscando" if buscando else "detenido"
            return {"zona": self.zona, "x_normalizada": None,
                    "intencion": "Buscando objetivo" if buscando else "Detener / sin objetivo"}
        x = (caja[0] + caja[2]) / (2 * ancho)
        if x < .37:
            self.zona = "izquierda"
        elif x > .63:
            self.zona = "derecha"
        elif self.zona == "izquierda" and x < .43:
            pass
        elif self.zona == "derecha" and x > .57:
            pass
        else:
            self.zona = "centro"
        intencion = {"izquierda": "Girar izquierda", "derecha": "Girar derecha", "centro": "Alineado"}
        return {"zona": self.zona, "x_normalizada": x, "intencion": intencion[self.zona]}
