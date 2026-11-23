# CNN Re-ID con galeria de 24 recortes

Estado: implementado y verificado localmente; pendiente de medicion en el NUC. Solicitud del usuario, 2026-11-23: implementar el experimento CNN para probarlo en el NUC conservando la galeria operativa de 24 recortes.

## Alcance y criterios

- Encoder preentrenado Intel person-reidentification-retail-0288, FP16, ejecutado por OpenVINO CPU con dos hilos y un stream. Sin entrenamiento ni actualizacion de galeria.
- Entrada corporal BGR 256x128, embedding de 256 valores normalizado L2. Distancia minima coseno contra la misma galeria aprobada usada por los otros metodos.
- Comparacion offline opcional, mismas detecciones, etiquetas y particiones; calibracion independiente y congelada. No activar camara ni motores para analizar datos existentes.
- Descargar pesos oficiales con comprobacion de integridad. Guardar hashes, version, configuracion y galeria codificada localmente. No incluir pesos ni datos en Git.
- Verificar preprocesamiento, normalizacion, errores de pesos, firma de calibracion y pipeline completo. Probar inferencia con pesos reales si la descarga esta disponible. La precision y rendimiento en el NUC requieren ejecucion alli.

Fuentes: [modelo y contrato](https://docs.openvino.ai/2023.3/omz_models_model_person_reidentification_retail_0288.html), [manifiesto oficial y checksums](https://github.com/openvinotoolkit/open_model_zoo/blob/master/models/intel/person-reidentification-retail-0288/model.yml). Manifiesto bajo Apache-2.0, licencia del paquete enlazada por ese manifiesto: [LICENSE](https://github.com/openvinotoolkit/open_model_zoo/blob/master/LICENSE). HU: https://trello.com/c/zU5nasgb (consulta devolvio error interno). GitHub feat/pipeline-percepcion consultado antes de implementar.

## Ejecutar en Ubuntu / NUC

Despues de sincronizar esta version de la rama feat/pipeline-percepcion, desde la raiz del repositorio:

```bash
cd /home/lumi/Desktop/Lumi
source .venv-practica/bin/activate
python -m pip install -r software/percepcion/requirements-openvino.txt
python -m software.percepcion.guiada --continuar datos/enrolamientos/guiada-20261120-172419-823225 --mejorar-pca --descargar-cnn
```

La ultima orden descarga aproximadamente 1 MB de pesos oficiales (XML y BIN) a modelos/pesos/person-reidentification-retail-0288, verifica los SHA-384 publicados y ejecuta la comparacion usando la sesion existente. No abre la camara al usar --continuar. Reutiliza las anotaciones guardadas; las que falten se piden con la interfaz existente. Se evaluan seis variantes si se activan mejoras PCA y CNN. CC-PPCA aparece pendiente hasta aportar la otra galeria.

Para repetir sin descargar: sustituir --descargar-cnn por --cnn. Para capturar una bateria nueva, quitar --continuar y su ruta; --solo conserva el protocolo sin distractores. --modelo-cnn RUTA_XML permite indicar los mismos pesos oficiales descargados en otra carpeta. Los archivos deben ser exactamente la variante 0288 FP16 verificada; no admite otros modelos con ese argumento.

La descarga tambien puede hacerse antes:

```bash
python -m software.percepcion.reid_openvino --descargar
```

## Solo cache de recortes disponible

Sin los videos originales, se puede ampliar una cache completa de la corrida anterior y calibrar/evaluar otra vez:

```bash
python -m software.percepcion.comparar_sesion con-cnn RUTA_CACHE_COMPLETA CACHE_CNN_NUEVA
python -m software.percepcion.comparar_sesion calibrar CACHE_CNN_NUEVA UMBRALES_CNN_NUEVOS.json --permitir-sin-distractores
python -m software.percepcion.comparar_sesion evaluar CACHE_CNN_NUEVA UMBRALES_CNN_NUEVOS.json RESULTADOS_CNN_NUEVOS
```

Descargar antes el modelo. RUTA_CACHE_COMPLETA debe contener calibracion y evaluacion, no solo calibracion. Quitar --permitir-sin-distractores si hay distractores etiquetados. Este flujo genera comparacion.csv y JSON/JSONL; el informe agregado con ventajas y limitaciones lo genera el flujo guiado. Cada salida debe ser nueva.

## Tratamiento y resultados

Se redimensiona cada recorte directamente a 256x128 como entrada BGR float32 0..255 NCHW. El IR oficial incorpora su tratamiento interno; no aplicar normalizacion RGB de ImageNet adicional. Se normaliza L2 cada embedding y se compara con los 24 vectores individuales: minima distancia coseno, no promedio de galeria ni porcentaje de certeza. Umbral y margen se ajustan solo en calibracion. Galeria fija durante toda la evaluacion. El codigo admite galerias anteriores aprobadas de 8-24 muestras; esta practica usa las 24 existentes.

La CNN tiene aprendizaje previo externo, mientras la PCA actual aprende su proyeccion en el enrolamiento. Compararlas evalua alternativas operativas con el mismo aporte del usuario, no igualdad de datos de entrenamiento.

El flujo guiado crea otra carpeta bajo datos/procesados/bateria-guiada-FECHA e imprime INFORME. Contiene informe.md, comparacion.csv, umbrales.json y repeticion-01..03. Cada repeticion incluye cnn_reid.json (parametros, metricas por escenario, hashes y recursos) y cnn_reid-frames.jsonl (decisiones). cache-completa/cnn_reid.npz guarda la galeria codificada de forma local. No sobrescribe resultados previos.

Tres inferencias de calentamiento se realizan antes de codificar la galeria y medir consultas. Se guardan tiempo de calentamiento y codificacion; compilacion no entra en el p95 de consultas. El p95 combinado sigue sumando deteccion guardada e identificacion offline, sin medir camara-pantalla. RSS refleja el proceso completo con modelos cargados, no memoria exclusiva de CNN. CPU y rendimiento deben medirse en el NUC. La primera entrega comparaba offline; la extension siguiente habilita tambien la seleccion explicita de CNN en vivo.

Los pesos, sus hashes y parametros forman parte del control de configuracion. Un cambio de pesos o agregar CNN invalida umbrales anteriores. Las tres repeticiones prueban estabilidad de decisiones, no nuevos participantes ni videos. El piloto sin distractores sigue sin elegir ganador de identidad. Los videos ya analizados son evidencia de desarrollo; despues de seleccionar configuracion hace falta otra evaluacion independiente.

## Evidencia local, 2026-11-23

- Descarga real desde OpenVINO verificada contra checksums oficiales.
- Inferencia CPU real con 24 imagenes sinteticas: galeria 24x256, valores finitos y distancia propia 0.
- 51 pruebas pasaron, incluida integracion con los pesos reales: preparar/reciclar cache, calibrar, evaluar dos veces, generar informe con siete metodos al aportar tambien negativos y mejoras PCA, y decisiones equivalentes entre corridas.
- Pruebas de BGR, escala, normalizacion, distancias, archivos incompletos/corruptos y rechazo de calibracion sin CNN sobre cache ampliada.
- Pendiente: ejecutar con los videos reales del usuario en el NUC. No se afirma precision ni FPS para ese equipo.

## Extension autorizada: prueba en vivo, 2026-11-23

Usuario solicita comprobar CNN en la ventana. Implementar selector cnn_reid conservando detector OpenVINO y perfil CPU/10 FPS. Mostrar metodo, umbral, margen y motivo. Permitir cargar umbrales de la corrida offline; verificar hashes de pesos. El nuevo enrolamiento usa hasta 24 recortes, no reentrena el encoder. Confirmar deja Listo y S inicia solo simulacion. Verificar selector, registro, rechazo y recuperacion mediante pruebas sinteticas; prueba fisica de camara pendiente en NUC.

### Ejecutar la CNN en vivo

Desde la terminal del escritorio del NUC, despues de sincronizar el codigo:

```bash
cd /home/lumi/Desktop/Lumi
source .venv-practica/bin/activate
python -m software.percepcion.practica --camara 0 --metodo cnn_reid --parametros auto
```

La opcion auto busca la carpeta bateria-guiada mas reciente que incluya cnn_reid en umbrales.json. No inventa umbrales si no los encuentra; informa un error. Es posible fijar la corrida con --parametros RUTA_UMBRALES_JSON. No combinarlo con --umbral/--margen. Verifica hashes del encoder contra los usados al calibrar y rechaza calibraciones sin aciertos utiles. Si faltan pesos, agregar --descargar-cnn (y --descargar-modelo si falta tambien el detector).

E inicia cuenta regresiva y captura de 12 segundos. Aprobar con Espacio o boton deja Listo; S inicia seguimiento simulado. R repite, C cancela, V graba clip independiente, Esc cierra. La CNN no se entrena: codifica hasta 24 recortes de este nuevo enrolamiento con pesos congelados. Se conserva la busqueda y recuperacion de tres coincidencias tras una perdida. No envia ordenes a ESP ni motores.

El panel muestra cnn_reid, umbral u, margen m y motivo (sin_galeria, ausencia, rechazo, ambiguedad, coincidencia o confirmacion). Cada recuadro muestra su distancia d; menor distancia indica mayor similitud, no probabilidad. Los indicadores de CPU y FPS permanecen. La galeria guarda cnn_reid.npz y metadatos de pesos; configuracion.json conserva metodo y parametros importados, decisiones.csv guarda distancias y estado. Solo se carga el identificador CNN al elegirlo, no tres identificadores simultaneos.

Importar el umbral offline es una referencia diagnostica. Al hacer otro enrolamiento cambia la galeria; la transferencia de ese umbral debe comprobarse y la prueba en vivo no sustituye una nueva evaluacion formal. No ajustar el umbral mirando evaluacion y presentar luego ese mismo video como prueba independiente.

Para volver a la referencia habitual:

```bash
python -m software.percepcion.practica --camara 0 --metodo histograma
```

En ese comando se conserva el umbral provisional historico .45 y margen .08; puede usarse --parametros auto para cargar la calibracion especifica del histograma.

Verificacion de esta extension: 54 pruebas pasaron, incluida ventana con camara sintetica y pesos CNN oficiales reales (24 embeddings, aprobar sin iniciar movimiento, S inicia, perdida y recuperacion). Pruebas de importacion automatica de umbrales y rechazo si cambian pesos o no existe calibracion. GitHub y HU de Trello consultados; HU en Doing. Prueba con camara y persona reales pendiente en el NUC.
