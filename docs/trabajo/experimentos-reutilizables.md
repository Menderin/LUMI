# D0 y E1 sobre datos existentes

2026-11-23. Usuario solicita ejecutar/preparar experimentos para probarlos enNUC. Este primer bloque implementa diagnosticoD0 y ejecutaE1 ya implementado; no mezclar fusion ni trackers en la comparacion. El usuario confirmo preparar primeroD0 yE1; E2/T1/T2/F1 quedan fuera de este bloque. GitHub feat/pipeline-percepcion aa4bfe4 y HU https://trello.com/c/zU5nasgb (Doing) consultados.

No hay videos/galerias humanos del laboratorio en esta copia: datos/enrolamientos solo contiene.gitkeep. No atribuir resultados sinteticos al usuario. Preparar CLI sinGUI/camara con entrada sesion guiada ya etiquetada o cache existente, mantener fuente intacta y generar salida nueva bajo datos/procesados. Calibracion por metodo, mismos recortes, tres repeticiones y resultados agregados. Piloto sin distractores requiere consentimiento explicito mediante flag y nunca elige ganador.

D0 separa objetivo sin caja compatible(IoU.5), rechazo/ambiguedad cuando si existe caja compatible, seleccion de otro anotado y seleccion sin caja anotada compatible. Esto ultimo puede ser falso positivo o desajuste de recuadro: no demuestra por si solo confusion de identidad. Usar unicamente frames revisados. No corregir etiquetas, cambiarIoU ni ajustar umbrales con evaluacion. Reportar denominadores y diagnostico por escenario; no sumar categorias que se solapan.

E1 usa minimo versus mediana de tres mejores distancias para histograma yCNN opcional. Galeria fija24, sin nuevo entrenamiento. ConservarPCA originales y ecualizados si se solicitan. CCP-PCA solo si hay clase negativa aprobada y distinta. Los modos por cache no requieren reabrir los videos; sesion guiada requiere sus videos y anotaciones. Incompletos deben fallar con instrucciones, nunca abrir anotacion/camara silenciosamente.

Verificar ejecucion CLI, ausencia deGUI/captura, fuente no modificada, separacioncalibracion/evaluacion, errores por falta de datos, informeD0 y paresE1; inferenciaCNN real con imagenes sinteticas cuando pesos disponibles. Medicion y resultados realesNUC pendientes del operador. Capturas y reportes detallados permanecen fuera deGit.


## Ejecutar en el NUC

Actualizar el repositorio despues de publicar este cambio. No hace falta un APK nuevo ni arrancar el servidor de camara. El programa es offline, tambien funciona porSSH; cerrar el servidor movil es aconsejable para no sumar su consumo al medir CPU.

```bash
cd /home/lumi/Desktop/Lumi
source .venv-practica/bin/activate
python -m software.percepcion.bateria_reutilizable \
  datos/enrolamientos/guiada-20261120-172419-823225 \
  --cnn --mejorar-pca --permitir-sin-distractores
```

La ruta corresponde a la sesion aportada por el operador; sustituirla si los archivos se movieron. --cnn exige pesos0288 locales verificados; si faltan, descargarlos una vez con python -m software.percepcion.reid_openvino --descargar cuando el NUC tenga Internet. --mejorar-pca incluye las dos variantes ecualizadas ya comparadas. --permitir-sin-distractores reconoce la limitacion del piloto previo y evita seleccionar ganador. Para una bateria nueva con distractores revisados en ambas particiones, quitar ese flag.

**No abre camara ni solicita repetir enrolamiento/anotacion.** Si falta algun JSON revisado o la captura no termino, falla explicando el archivo; completar aparte con guiada --continuar RUTA y retomar despues. No fabricar etiquetas con predicciones. Las sesiones recientes de servidor_movil/app no sustituyen automaticamente una bateria guiada con clips de calibracion/evaluacion y etiquetas.

### Reutilizar la cache anterior (mas rapido)

Se acepta indistintamente la carpeta de una bateria anterior o su cache-completa. Este modo no necesita reabrir videos:

```bash
python -m software.percepcion.bateria_reutilizable \
  datos/procesados/BATERIA_ANTERIOR \
  --cnn --mejorar-pca --permitir-sin-distractores
```

BATERIA_ANTERIOR es un marcador a sustituir por la carpeta real. Conserva clase negativa si ya existia en la cache; en ese caso tambien evaluaCC-PPCA. Si no, registra el motivo pendiente sin impedir otros metodos. No incorpora ni entrena nuevas clases automaticamente.

### Solo diagnosticar decisiones anteriores

```bash
python -m software.percepcion.diagnosticar_sesion \
  datos/procesados/BATERIA_ANTERIOR/repeticion-01 \
  datos/procesados/diagnostico-D0-NUEVO
```

Esto solo lee decisiones/resumenes ya generados. No recalibra ni ejecuta inferencia; exige una salida nueva. Las decisiones comparadas deben pertenecer a los mismos frames, cajas y referencias. Cambios de referencias o duplicados producen error.

## Archivos entregados

Cada ejecucion completa genera datos/procesados/experimentos-D0-E1-FECHA/:

- informe.md y comparacion.csv: mismos metodos de referencia, mas histograma_mediana3 y cnn_reid_mediana3 si se incluyeCNN.
- comparacion-galeria.csv: E1, deltas mediana3 menos minimo; mirar aciertos, falsas aceptaciones, sustituciones y peor escenario antes de recomendar.
- diagnostico-D0/informe.md: tabla por metodo/escenario con denominadores.
- diagnostico-D0/frames.csv: categoria por decision, IoU maximo con objetivo, seleccion/identidad asociada, motivo, distancias y umbrales.
- diagnostico-D0/distancias-candidatos.csv: puntuaciones por candidato con rol segun referencia humana compatible; sin_asociar no significa otra persona confirmada.
- diagnostico-D0/por-escenario.csv y diagnostico.json: contadores y hashes de archivos leidos.
- umbrales.json: calibracion congelada, propia por variante.
- repeticion-01..03/: decisionesJSONL y metricasJSON; repetir un video comprueba estabilidad, no aumenta sujetos ni tomas. D0 usa solo repeticion01 para no triplicar conteos.
- cache-completa/: copia de datos necesarios; no altera los originales.
- ejecucion.json: fuente, hashes, commit, hashes del codigo realmente ejecutado, versiones, estado completa/fallida/interrumpida. Los fallos conservan la carpeta parcial identificada, sin borrar resultados previos.

Los informes detallados/capturas permanecen fuera deGit. CPU/RSS son del proceso offline y p95 incluye detector guardado+identificacion; no es latencia captura-pantalla de la app. Una falta de cajaIoU.5 puede provenir del detector o de discrepancia de anotacion: revisar antes de concluir. No ajustar metodos sobre evaluacion ni bajarIoU para favorecerlos. Las capturas ya usadas repetidamente son desarrollo; reservar nuevas tomas para validacion final.

## Evidencia de esta entrega

Ejecutado localmente el CLI completo con24recortes sinteticos, pesosCNN0288 oficiales, ocho variantes (tres referencias, dosPCA ecualizados, CNN y dosmediana3) y tres repeticiones. Decisiones equivalentes. Se generaron informesE1/D0 y CSV. Los datos artificiales se marcan explicitamente y no producen recomendacion de identidad humana. Esto valida el banco, no demuestra mejoras en el piloto del usuario.

Seis pruebas nuevas cubren diagnostico de perdida/rechazo/ambiguedad/sustitucion, caja sin referencia compatible, recorrido completo desdecache sin abrir video/GUI, sesion con videos ya anotados, conservacion de originales, particiones sin fugas, flag de piloto sin ganador y errores de anotaciones faltantes. Suite general ejecutada con LUMI_REID_XML apuntando a pesos reales:69 pruebas correctas, sin omisiones. Tambien se ejecuto el CLI D0 independiente sobre repeticion01. NUC y datos reales pendientes del operador.
