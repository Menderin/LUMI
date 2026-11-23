"""CC-PPCA corporal: proyeccion posterior y regla NBC del articulo de 2011."""
import numpy as np
from threadpoolctl import threadpool_limits

from .experimentos import gris


def log_media_exp(valores):
    maximo = np.max(valores)
    return float(maximo + np.log(np.exp(valores-maximo).mean()))


class CCPPCA:
    metodo = "cc_ppca"

    def __init__(self, objetivo, otros, alto=128, componentes=8):
        if not 8 <= len(objetivo) <= 24 or not 8 <= len(otros) <= 24:
            raise ValueError("CC-PPCA requiere dos galerias revisadas de 8 a 24 recortes")
        self.alto = alto
        self.clases = []
        with threadpool_limits(limits=2):
            matrices = [np.stack([gris(x,alto) for x in muestras]).astype(np.float64)
                        for muestras in (objetivo,otros)]
            descomposiciones = []
            for x in matrices:
                media = x.mean(axis=0)
                _, s, vt = np.linalg.svd(x-media,full_matrices=False)
                tolerancia = s.max()*max(x.shape)*np.finfo(np.float64).eps
                rango = int(np.count_nonzero(s>tolerancia))
                if rango == 0:
                    raise ValueError("CC-PPCA: galeria de una clase sin variacion")
                descomposiciones.append((media,s,vt,rango))
            # Se deja al menos una direccion de variacion para estimar ruido.
            self.q = min(componentes,*(max(0,d[3]-1) for d in descomposiciones))
            if self.q < 1:
                raise ValueError("CC-PPCA requiere mas variacion por clase para estimar ruido")
            for x,(media,s,vt,rango) in zip(matrices,descomposiciones):
                autovalores = s*s/len(x)
                sigma2 = max(float(autovalores[self.q:].sum()/(x.shape[1]-self.q)),1e-8)
                principales = autovalores[:self.q]
                factores = np.sqrt(np.maximum(principales-sigma2,0))/principales
                self.clases.append({"media":media,"componentes":vt[:self.q],
                                    "factores":factores,"sigma2":sigma2})
            entrenamiento = np.concatenate(matrices,axis=0)
            for clase in self.clases:
                # nu_i = media sobre TODO el entrenamiento de producto phi(z_j).
                clase["log_nu"] = log_media_exp(self.log_marginales(entrenamiento,clase))
        self.metadata = {
            "modelo":"CC-PPCA/NBC corporal", "formula":"ecuaciones 1, 3 y 4 del articulo 2011",
            "q":self.q,"alto":alto,"prior":"clases equiprobables",
            "sigma2":[c["sigma2"] for c in self.clases],
            "log_nu":[c["log_nu"] for c in self.clases],
            "distancia":"score_otros - score_objetivo; menor favorece objetivo",
            "preprocesamiento":f"gris {alto}x{alto//2} proporcional, padding negro, /255; igual que PCA base",
        }

    def log_marginales(self, x, clase):
        latente = ((x-clase["media"]) @ clase["componentes"].T)*clase["factores"]
        return -.5*(np.square(latente).sum(axis=-1)+self.q*np.log(2*np.pi))

    def distancia(self, imagen):
        x = gris(imagen,self.alto).astype(np.float64)
        scores = [float(self.log_marginales(x,c))+c["log_nu"] for c in self.clases]
        valor = scores[1]-scores[0]
        if not np.isfinite(valor):
            raise ValueError("Puntuacion CC-PPCA no finita")
        return valor

    def guardar(self, ruta):
        datos = {"metodo":np.array(self.metodo),"alto":np.array(self.alto),"q":np.array(self.q)}
        for nombre,clase in zip(("objetivo","otros"),self.clases):
            datos.update({f"{nombre}_{k}":np.asarray(v) for k,v in clase.items()})
        np.savez_compressed(ruta,**datos)
