"""Variante E1: misma representacion, mediana de las tres menores distancias."""
import numpy as np

PERFIL_AGREGACION = {"regla":"mediana3","k":3,"metodos":["histograma","cnn_reid"]}


class MedianaGaleria:
    metodo="agregacion_galeria"

    def __init__(self, base):
        if len(base.galeria)<3:
            raise ValueError("Mediana3 necesita al menos tres recortes de galeria")
        self.base=base
        self.metadata={**getattr(base,"metadata",{}),"agregacion":"mediana3","k":3,
                       "metodo_base":base.metodo,"galeria_recortes":len(base.galeria)}

    def distancia(self, imagen):
        valores=np.asarray(self.base.distancias_galeria(imagen),dtype=np.float64)
        if valores.ndim!=1 or len(valores)<3 or not np.isfinite(valores).all():
            raise ValueError("Distancias de galeria invalidas para mediana3")
        return float(np.median(np.partition(valores,2)[:3]))

    def guardar(self,ruta):
        from .experimentos import guardar_representacion
        guardar_representacion(self.base,ruta)
        with np.load(ruta,allow_pickle=False) as archivo:
            datos={clave:archivo[clave].copy() for clave in archivo.files}
        datos.update(agregacion=np.array("mediana3"),k=np.array(3))
        np.savez_compressed(ruta,**datos)
