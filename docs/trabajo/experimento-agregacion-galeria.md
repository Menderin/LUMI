# E1: minimo frente a mediana de tres distancias

Estado: implementado; verificado con datos sinteticos y CNN real, pendiente de NUC. Autorizacion usuario 2026-11-23: preparar el experimento para probarlo al volver al laboratorio. Se toma E1 de la revision como primer cambio aislado, sin introducir trackers ni fusion a la vez.

Objetivo: comparar histograma y CNN actuales con versiones que toman la mediana de las tres menores distancias a la misma galeria aprobada (24 recortes en la practica). No entrenar, aumentar muestras, modificar detector ni limpiar galeria en esta comparacion. Las referencias originales permanecen disponibles. Umbral y margen propios calibrados en la particion de calibracion; resultados nuevos sin sobrescribir anteriores. Esta variante puede rechazar vistas raras y no se presume mejor.

Criterios: comando guiado opcional y extension de cache para no recapturar/reetiquetar; registrar regla, k y metadatos; rechazar umbrales de otro perfil; conservar equivalente la referencia original; probar con datos sinteticos y pesos CNN reales disponibles. Movimiento restringido. La app sigue usando su flujo actual y no requiere nuevo APK para este experimento offline.

Fuentes de alcance: solicitud actual, docs/trabajo/revision-investigacion-seguimiento.md, HU https://trello.com/c/zU5nasgb consultada (Doing), GitHub feat/pipeline-percepcion consultado. Pendiente prueba humana en NUC.

## Ejecucion reutilizando la sesion del laboratorio

Desde la raiz del repo sincronizado y el entorno activado:

```bash
python -m software.percepcion.guiada --continuar datos/enrolamientos/guiada-20261120-172419-823225 --cnn --comparar-galeria
```

No abre camara ni requiere repetir enrolamiento. Conserva etiquetas ya revisadas; si falta alguna, solicita completarla. Compara histograma, Euclidea, Mahalanobis, CNN y las dos variantes mediana3. CC-PPCA sigue pendiente si no hay galeria negativa. Se puede agregar --mejorar-pca para conservar tambien las variantes ecualizadas de la tabla anterior, sin cambiar el efecto aislado de E1. --descargar-cnn descarga pesos si faltan; --cnn por si solo exige los ya descargados.

El minimo de referencia sigue siendo la minima distancia a cualquiera de los24recortes. Mediana3 calcula distancias con el mismo descriptor y toma las tres menores, cuya mediana es la segunda menor. Es un estadistico de comparacion, no un embedding nuevo ni una media de imagenes. No requiere tres muestras de la misma pose ni clasifica orientaciones. La galeria se mantiene intacta y cada score recibe umbral/margen propios.

## Solo cache disponible

Si ya existe cache-completa con todos los recortes y etiquetas:

```bash
python -m software.percepcion.comparar_sesion con-agregacion CACHE_ANTERIOR CACHE_E1_NUEVA
python -m software.percepcion.comparar_sesion calibrar CACHE_E1_NUEVA UMBRALES_E1.json --permitir-sin-distractores
python -m software.percepcion.comparar_sesion evaluar CACHE_E1_NUEVA UMBRALES_E1.json RESULTADOS_E1
```

Los nombres en mayusculas son rutas a sustituir. Si la cache ya contiene CNN, la incluye; si no, solo agrega histograma_mediana3. Quitar --permitir-sin-distractores al calibrar con otra persona anotada. No reutilizar los umbrales anteriores: el perfil forma parte de la firma y se rechazan calibraciones incompatibles. La copia de cache conserva los datos originales y necesita una carpeta nueva.

## Resultados

Flujo guiado crea datos/procesados/bateria-guiada-FECHA/ e imprime INFORME. Archivos:

- informe.md y comparacion.csv: resultados de todas las variantes.
- comparacion-galeria.csv: pares minimo/mediana3 con delta de aciertos y falsas aceptaciones; delta=mediana3 menos minimo. Mas aciertos es favorable; mas falsas aceptaciones es desfavorable. No decidir solo por delta agregado: revisar peor escenario y sustituciones.
- umbrales.json: umbrales/margenes por metodo, perfil y trazabilidad de calibracion.
- repeticion-01..03: JSON por escenario/metodo y JSONL por fotograma. Las repeticiones verifican estabilidad, no son tres participantes ni nuevas tomas.
- cache-completa/*_mediana3.npz: misma representacion, con regla mediana3 y k3 registrados. No contiene reentrenamiento.

El flujo de cache directa genera comparacion.csv y decisiones/metricas; el informe agregado y comparacion-galeria.csv los produce guiada.

## Prueba nueva con dos personas

El piloto anterior sin distractores solo sirve para desarrollo. Con el companero disponible, despues de probar app:

```bash
python -m software.percepcion.guiada --camara 0 --cnn --comparar-galeria
```

No usar --solo para esta bateria. Durante el enrolamiento de esta interfaz de escritorio debe estar solo el objetivo en el encuadre; se conservan24recortes. Despues, el acompanante participa en escenas de distractor solo y cruces segun instrucciones. La seleccion entre varios implementada en la app pertenece al servidor_movil, no a esta ventana guiada. No mezclar galerias ni datos de ambas sesiones para aparentar una sola comparacion.

Incluir objetivo solo, distractor solo, escena vacia, oclusion/salida/reaparicion, cruce y ropa similar. Calibracion y evaluacion deben ser clips distintos. Revisar ventanas de cruces para detectar errores breves. La toma final independiente debe reservarse despues de elegir configuracion; no seguir ajustando sobre sus resultados.

## Evidencia y pendientes

61 pruebas Python pasaron con pesos oficiales CNN disponibles, incluyendo galeria24 intacta, variantes con referencia identica, calibracion incompatible rechazada, informes con todas las variantes y decisiones repetibles. No hay resultados nuevos del laboratorio. La app0.8.0 conserva su APK, contrato y movimiento restringido; este cambio solo amplia la comparacion offline. ByteTrack/fusion y filtros no estan implementados por este experimento.
