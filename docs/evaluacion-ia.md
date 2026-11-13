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

## Ejecución del banco offline

Desde la raíz, instalar las dependencias en el entorno local y validar el manifiesto.

~~~sh
python -m pip install -r software/percepcion/requirements.txt
python -m software.percepcion.dataset.manifiesto datos/particiones/piloto.json
python -m software.percepcion.experimentos datos/particiones/piloto.json datos/particiones/config.json datos/procesados/corrida-01 --split calibracion
~~~

Configuración JSON de ejemplo (rutas relativas al manifiesto y umbral ilustrativo, no calibrado):

~~~json
{"metodo":"histograma","galeria":["../enrolamientos/muestra.png"],"umbral":0.2,"margen":0.02,"asociacion":false,"hilos":1}
~~~

Métodos: histograma HSV 16×8 por región con Bhattacharyya; euclidea y mahalanobis con PCA de hasta 8 componentes y alto 128 o 64; reid con encoder OSNet x0.25 ONNX y alto 256 o 128. Re-ID requiere ruta `encoder` y exportación que devuelva el embedding. El detector opcional requiere `detector` con `archivo`, `lado` y `confianza`. Admite exportaciones YOLO ONNX con NMS y salida 1×N×6 (XYXY en píxeles, confianza, clase; persona=0), entrada RGB cuadrada en [0,1] con relleno inferior y derecho. Verificar el contrato de cada exportación. Sin detector se usan cajas anotadas. El modo manual sirve para aislar identificación; comparar asociación temporal sobre vídeo con detección.

Primero comparar dos pesos compatibles y revisar recuperación a IoU 0,5, falsos positivos y p95. Luego repetir identificadores con galería monoluz y mixta, máximo 12 recortes. Usar una corrida por usuario/galería. Ajustar umbral en calibración por cero falsas aceptaciones observadas y máxima recuperación. Congelar antes de evaluar. Una sustitución en cruce, oclusión o transición descarta la configuración. Ordenar candidatas por peor tasa de acierto entre escenarios, p95 y RAM. Revisar JSONL para recuperación y sustituciones por secuencia. Repetir tres veces por plataforma con mismo vídeo y configuración, registrar pesos y condiciones térmicas. El banco no elige automáticamente ni reemplaza la validación física.

Autoencoder condicional: si fallan los candidatos y existen datos independientes, entrenar offline con RTX A5000, RGB 128×64 y 64×32, latente 32, L1 y parada temprana. Comparar latentes por coseno y reportar reconstrucción aparte. No hay entrenamiento ejecutado ni selección final.

## Batería en el servidor

Instalar las dependencias del ejecutor en el entorno Python del servidor. Preparar un JSON local en `datos/particiones/` con las configuraciones que se quieren comparar. Cada entrada apunta a un JSON del ejecutor individual, relativo a la matriz. Las rutas de vídeos, pesos y galerías de cada configuración siguen siendo relativas al manifiesto.

~~~json
{"corridas":[
  {"id":"hsv-interior","config":"hsv-interior.json"},
  {"id":"pca-euclidea-interior","config":"pca-euclidea-interior.json"},
  {"id":"pca-mahalanobis-interior","config":"pca-mahalanobis-interior.json"},
  {"id":"osnet-interior","config":"osnet-interior.json"}
]}
~~~

Desde la raíz del repositorio en Linux:

~~~sh
python -m pip install -r software/percepcion/requirements.txt
bash herramientas/ejecutar-bateria.sh datos/particiones/piloto.json datos/particiones/matriz.json --equipo servidor --split calibracion --repeticiones 3
~~~

También se puede usar `python -m software.percepcion.bateria` con los mismos argumentos. Para evaluación usar otra matriz con las configuraciones ya congeladas y `--split evaluacion`. Incluir entradas separadas por usuario, iluminación, detector y asociación según el plan. El lanzador ejecuta la matriz indicada en CPU, de forma secuencial. La calibración de umbrales y el entrenamiento condicional se realizan aparte.

Cada lanzamiento imprime su carpeta bajo `datos/procesados/baterias/`, excluida de Git. Allí quedan `bateria.json` con la configuración usada, `indice.csv` para comparar corridas, un log por intento y, para las corridas completas, `resumen.json`, `corrida.json` y `frames.jsonl`. Si una corrida falla, el resto continúa y el comando devuelve un código distinto de cero. Compartir solo resultados agregados revisados.

## Vista previa

En un entorno con escritorio, instalar las dependencias y sustituir la variante sin GUI en ese entorno Python:

~~~sh
python -m pip uninstall -y opencv-python-headless
python -m pip install opencv-python
~~~

Añadir `--vista-previa` al comando de la batería o de una corrida individual. La ventana muestra el vídeo grabado del manifiesto, los candidatos en ámbar y el objetivo seleccionado en verde. Pulsar Q o Esc para cerrar la vista sin interrumpir la corrida actual. En modo manual se muestran los recuadros anotados. La reproducción sigue el ritmo del procesamiento. Ejecutar los benchmarks sin vista previa para evitar que el dibujo y la ventana afecten los FPS y el uso de CPU.
