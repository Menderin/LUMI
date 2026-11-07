# Evaluación preliminar de identificación visual

Estado: diseño experimental propuesto. No hay resultados medidos ni algoritmo ganador.

## Pregunta

¿Puede una representación corporal ligera preservar la identidad del enrolado ante otras personas, con latencia y memoria compatibles con CPU local? Enrolar con un giro cubre algunas vistas de una sesión, no garantiza invariancia a ropa, iluminación o pose.

El detector localiza personas; PCA o el encoder representan recortes; el comparador decide coincidencia; el tracker asocia en el tiempo. Medir cada etapa y el conjunto. Entrenar con imágenes completas puede aprender el fondo; normalizar recortes corporales y evitar contaminación entre sesiones.

## Alternativas comparables

| Alternativa | Qué se prueba | Riesgo principal |
| --- | --- | --- |
| PCA + Euclídea | Línea base de proyección y comparación | Variación de fondo, escala, pose y ropa |
| PCA + Mahalanobis | Distancia con covarianza estimada en espacio reducido | Pocas muestras, matriz singular y distribución multimodal del giro |
| Autoencoder | Latente, reconstrucción y puntuaciones por separado | Reconstrucción buena no demuestra identidad |
| Person Re-ID preentrenado | Referencia candidata propuesta por el Charter | Costo de inferencia, dominio y licencia |

Comparar primero Euclídea y Mahalanobis con el mismo PCA y datos. Mahalanobis no es necesariamente superior: estimar covarianza con regularización, documentar el conjunto usado y comprobar estabilidad. Whitening equivale a una ponderación ligada a la covarianza con que se ajustó PCA; no es idéntico a cualquier covarianza de identidad. [PCA](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html), [covarianza y shrinkage](https://scikit-learn.org/stable/modules/covariance.html).

Para el autoencoder distinguir entrenamiento offline y enrolamiento: entrenar una red desde cero cada vez que gira el usuario es una hipótesis adicional de costo y datos. Un encoder preentrenado podría mantenerse fijo y construir una galería local, pero requiere evaluación. La literatura muestra limitaciones de reconstrucción como prueba de pertenencia; no demuestra rendimiento de Re-ID en LUMI. [Denouden et al.](https://arxiv.org/abs/1812.02765).

## Resolución y muestreo

25×25, 32×32 y 64×64 son candidatos mencionados por el usuario, no requisitos. Comparar con recortes que preserven proporción corporal, por ejemplo mediante padding o tamaños rectangulares. El PDF propone 64×128 y 96×192; ambas propuestas necesitan medición. No fijar FPS a 10 por haber sido un ejemplo: medir tiempos y seleccionar frecuencia útil.

## Protocolo propuesto

1. Reunir secuencias consentidas: enrolado y distractores, frente/espalda/lateral, cruces y oclusiones en superficie y luz acordadas.
2. Separar sesiones para enrolamiento, calibración y prueba; mantener frames cercanos en la misma partición.
3. Fijar detector, preprocesamiento y galería; comparar identificadores bajo condiciones equivalentes.
4. Ajustar umbrales con calibración, incluida clase desconocida, y congelarlos antes de evaluar.
5. Registrar falsas aceptaciones, rechazos del enrolado, cambios de identidad por recorrido, intentos de enrolamiento, latencia p50/p95 extremo a extremo, FPS efectivos, RAM, CPU y temperatura.
6. Publicar resultados agregados con configuración y limitaciones; seleccionar en función de AC-01/02 y del presupuesto de cómputo que aún debe acordarse.

No elegir el mejor número sobre los mismos datos usados para ajustar. El costo del detector puede dominar al de PCA; optimizar esa parte si las mediciones lo muestran. No hay aún presupuesto máximo de latencia ni umbral aceptable de falsos positivos acordado.

## Dependencia de datos propios

Antes de comparar identificadores, ejecutar el piloto de captura definido en [construcción del dataset](construccion-dataset.md). Verificar que el detector funciona desde el ángulo bajo y que los recortes tienen calidad suficiente. Separar galería de enrolamiento y secuencias de evaluación; ninguna colección está disponible todavía.
