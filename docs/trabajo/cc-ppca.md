# Cuarto experimento CC-PPCA corporal

## Estado y procedencia

Solicitud del usuario el 2026-11-23. Se agrega cc_ppca al banco y al informe guiado como cuarto experimento. Fuente: Juan Bekios Calfa, Jose M. Buenaposada y Luis Baumela, Class-Conditional Probabilistic Principal Component Analysis: Application to Gender Recognition, Computacion y Sistemas 14(4), 2011, pp. 383-391. PDF proporcionado por el usuario.

Es una adaptacion a cuerpo completo de las ecuaciones 1, 3 y 4: proyeccion PPCA posterior, producto de marginales gaussianas estandar y comparacion de log-puntuaciones por clase. Conserva el preprocesamiento gris 128x64 proporcional, padding negro y escala [0,1] de los PCA actuales para aislar el cambio de modelo. El articulo usa rostros 25x25, ecualizacion y mascara ovalada. El rendimiento publicado del articulo no se traslada al robot.

## Modelo implementado

Clases objetivo y otros, con priors equiprobables. Cada clase estima media y PCA propia por SVD. Se usan hasta ocho dimensiones, limitadas por el rango de ambas galerias y dejando una direccion de variacion para estimar ruido. sigma2 es la varianza descartada media sobre las dimensiones restantes, con suelo numerico 1e-8.

W_i se obtiene de los autovalores y el ruido; el latente es la media posterior (W_i^T W_i + sigma_i^2 I)^-1 W_i^T (x-mu_i). La puntuacion usa log nu_i mas la suma de log densidades N(z_j;0,1), siguiendo la regla NBC descrita en el articulo. nu_i se calcula con todo el entrenamiento de ambas clases, segun su ecuacion 3. Se usa log-mean-exp por estabilidad numerica. Esta puntuacion es una regla experimental de clasificacion y no una probabilidad de identidad calibrada.

La distancia del adaptador es score_otros - score_objetivo. Valores menores favorecen al objetivo; pueden ser negativos. El calibrador permite esas escalas y conserva la rejilla original para los tres metodos previos. El ruido modifica la proyeccion posterior. La regla del articulo usada aqui puntua marginales latentes, sin agregar un umbral de reconstruccion ni una densidad completa en el espacio observado.

Se guardan q, sigma2, log nu, medias, proyecciones y factores en cc_ppca.npz; metadatos de configuracion aparecen en los JSON de resultados. Ajuste y comparacion siguen limitados a dos hilos BLAS. La primera entrega ejecuta el cuarto metodo offline, con los mismos recortes de los otros tres.

## Datos necesarios

La galeria aprobada del usuario puede reutilizarse. CC-PPCA necesita ademas una galeria aprobada de OTRA persona, con 8-24 recortes y variacion visual suficiente. El rol de otra persona lo declara el operador. El codigo no puede verificar por si mismo que las dos galerias sean identidades diferentes.

Esa segunda captura debe ser independiente de los clips de calibracion/evaluacion. La preparacion rechaza el mismo video fuente del objetivo cuando su hash esta registrado, origenes negativos que coincidan con videos de calibracion/evaluacion y recortes identicos a los del objetivo. Tambien verifica hashes de todos los recortes antes de ajustar/evaluar. No detecta derivados reexportados; el operador debe conservar la separacion por sesion.

Escenas vacias y sillas no proporcionan la clase de otras personas. Una sola galeria negativa tampoco representa toda la poblacion desconocida. Se siguen necesitando distractores de evaluacion para validar rechazo de identidades no vistas.

Si falta esa clase o no tiene variacion suficiente, el informe muestra cc_ppca pendiente con su motivo y celdas de metricas vacias. Los tres metodos previos se ejecutan normalmente. El modo --solo no selecciona ganador de identidad, incluso si se proporciona una segunda clase para entrenar.

## Reutilizar capturas anteriores

Despues de actualizar el repositorio, retomar la sesion y proporcionar la segunda galeria:

```bash
python -m software.percepcion.guiada --continuar datos/enrolamientos/SESION_OBJETIVO --galeria-negativa datos/enrolamientos/SESION_OTRA_PERSONA/galeria-1
```

Las etiquetas guardadas se reutilizan. La captura del usuario y sus videos de prueba se conservan. Si estan disponibles los archivos de la cache completa, se puede trabajar con ellos sin reabrir los videos originales del objetivo:

```bash
python -m software.percepcion.comparar_sesion con-negativos datos/procesados/BATERIA_ANTERIOR/cache-completa datos/enrolamientos/SESION_OTRA_PERSONA/galeria-1 datos/procesados/cache-cuatro
python -m software.percepcion.comparar_sesion calibrar datos/procesados/cache-cuatro datos/particiones/umbrales-cuatro.json
python -m software.percepcion.comparar_sesion evaluar datos/procesados/cache-cuatro datos/particiones/umbrales-cuatro.json datos/procesados/resultados-cuatro
```

Sustituir los nombres por las rutas reales. con-negativos crea una copia nueva y conserva el analisis original. La galeria negativa incluye su video de enrolamiento para verificar origen. La calibracion usa exclusivamente frames de calibracion. La evaluacion conserva sus umbrales congelados y produce CSV/JSON con los cuatro metodos si CC-PPCA dispone de datos suficientes.

Para nuevas caches tambien existe preparar --galeria-negativa RUTA. El informe guiado incluye ventajas y limitaciones del cuarto metodo y su estado pendiente/evaluado.

## Verificacion y limites

Pruebas numericas contrastan la proyeccion con la formula matricial directa, el normalizador por clase y el score final. Pruebas de integracion reutilizan cache con dos galerias, congelan calibracion, evalúan cuatro metodos y generan informe agregado. Se verifican galeria degenerada, fuente negativa de evaluacion, hashes alterados y estado pendiente sin negativos.

La bateria local paso 46 pruebas Python. Son datos sinteticos. Las mediciones reales y el beneficio frente a histograma, Euclidea y Mahalanobis quedan pendientes en el NUC. Los 39 frames visibles del piloto existente permiten una primera comparacion, pero nuevas tomas independientes seran necesarias para conclusiones posteriores al ajuste.
