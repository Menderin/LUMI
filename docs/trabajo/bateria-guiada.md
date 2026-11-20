# Bateria guiada de tres identificadores

## Uso en el NUC

Una sola sesion de captura alimenta los tres metodos. La fase en vivo usa el histograma como referencia visual; la comparacion formal ejecuta histograma, PCA Euclidea y PCA Mahalanobis secuencialmente sobre los mismos recortes, sin tres detectores en paralelo.

Desde la terminal del escritorio del NUC, despues de actualizar el repo:

```bash
cd /home/lumi/Desktop/Lumi
source .venv-practica/bin/activate
python -m pip install -r software/percepcion/requirements-openvino.txt
python -m software.percepcion.guiada --camara 0
```

Si estas solo, usa:

```bash
python -m software.percepcion.guiada --camara 0 --solo
```

El modo completo requiere un acompanante para distractor y cruces. El modo solo omite esas escenas y marca el informe como exploratorio, sin ganador de identidad. Agrega --descargar-modelo si faltan pesos.

## Recorrido de una sola pasada

1. Pulsa E o Enrolar y completa la captura de 12 segundos despues de la cuenta regresiva. Aprueba las 20-24 miniaturas y el video con Enter.
2. La ventana anuncia cada escena. Pulsa N o el boton Paso cuando estes listo. Hay tres segundos para colocarte y luego la grabacion empieza y termina automaticamente. No necesitas pulsar V.
3. Calibracion contiene frente/perfiles/espalda (10 s), oclusion y reaparicion (10 s), escena vacia (6 s), distractor sin objetivo (8 s) y cruce (10 s). Evaluacion repite las acciones con tomas nuevas. El modo solo contiene las tres primeras escenas en ambas particiones.
4. Al terminar los clips la camara se libera. Se inicia la revision humana de calibracion. S selecciona un fotograma para revisar, N lo omite y Esc interrumpe. Dibuja TODAS las personas con el raton, Enter entre recuadros y Esc para terminar la seleccion. Luego haz clic en el recuadro del objetivo o pulsa su numero. 0 o el boton inferior indica objetivo ausente. Para escena vacia, S y terminar sin recuadros confirma la ausencia.
5. Se congelan los parametros de los tres metodos. Luego se revisan las tomas de evaluacion con el mismo procedimiento. No se usan sus etiquetas para ajustar umbrales.
6. El asistente prepara una cache comun, ejecuta los tres identificadores y repite cada comparacion tres veces. Genera informe.md, comparacion.csv, recomendacion.json y las corridas detalladas. No hace falta lanzar los tres experimentos manualmente.

Los cruces y oclusiones se revisan frame a frame. En las otras escenas se ofrece uno de cada cinco frames. Los omitidos quedan fuera de los denominadores. La revision humana es necesaria para distinguir realmente al objetivo de un distractor; el guion de acciones no se convierte en verdad de terreno automaticamente.

La identificacion por numero se hace sobre la ventana, sin volver a la terminal. Para mas de nueve personas se usa clic. En este piloto se esperan una o dos.

## Archivos y recuperacion

Capturas y guia.json quedan en datos/enrolamientos/guiada-FECHA/. Los resultados se guardan en datos/procesados/bateria-guiada-FECHA/. La terminal imprime la ruta del informe. sesion.json conserva el origen y el guion.

Esc durante la captura finaliza y conserva los datos, sin inventar un resultado para una bateria incompleta. Cancelar o repetir el enrolamiento despues de iniciar las escenas interrumpe la bateria para evitar mezclar galerias. No hay reanudacion de captura parcial en esta version.

Si interrumpes la revision despues de completar las capturas, puedes retomarla:

```bash
python -m software.percepcion.guiada --continuar datos/enrolamientos/guiada-FECHA
```

Sustituye FECHA por la carpeta real. Se conservan las etiquetas previas y se crea un directorio nuevo de analisis. La comparacion usa --repeticiones 3 por defecto, configurable para ensayos tecnicos.

## Informe e interpretacion

El informe contiene aciertos/visibles, falsas aceptaciones/ausentes, sustituciones por frame, peor acierto por escenario, latencia p95, CPU y RSS. Agrega medianas de tiempo/CPU y RAM maxima entre repeticiones. Comprueba si las decisiones fueron equivalentes.

Las ventajas y limitaciones de histograma y ambas distancias PCA se describen como propiedades teoricas, separadas de las mediciones. Un resultado favorable en estos videos no acredita robustez ante otras luces o ropa. El informe deja esos pendientes explicitos y no propone un ganador de identidad en modo solo.

CPU/RSS del comparador corresponden al trabajo offline. La latencia suma deteccion registrada e identificacion sobre cache; no es camara-pantalla. El consumo completo de la captura esta en recursos.csv. Repetir el mismo video no agrega participantes ni recorridos independientes.

## Verificacion

Se probo el guion de diez escenas, el modo solo de seis escenas, interrupcion por cambio de galeria, selector grafico de identidad y captura guiada por el punto de entrada de la ventana con camara/reloj simulados. La prueba de analisis usa AVI, galeria de 24 recortes, referencias humanas sinteticas, calibracion separada y dos repeticiones con decisiones equivalentes. La suite local actual tiene 29 pruebas. La validacion con Logitech C925e y personas reales en Ubuntu sigue pendiente.

Referencia de gestion: https://trello.com/c/zU5nasgb
