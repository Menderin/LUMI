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
4. Al terminar los clips la camara se libera. Se inicia la revision humana de calibracion. S selecciona un fotograma para revisar, N lo omite y Esc interrumpe. Dibuja TODAS las personas arrastrando el raton; cada recuadro se agrega al soltar. Usa el boton Confirmar o Espacio para terminar la seleccion. Deshacer elimina el ultimo recuadro. Esc cancela la revision actual. Luego haz clic en el recuadro del objetivo o pulsa su numero. 0 o el boton inferior indica objetivo ausente. Para escena vacia, S y el boton Escena vacia (o 0) confirma la ausencia.
5. Se congelan los parametros de los tres metodos. Luego se revisan las tomas de evaluacion con el mismo procedimiento. No se usan sus etiquetas para ajustar umbrales.
6. El asistente prepara una cache comun, ejecuta los tres identificadores y repite cada comparacion tres veces. Genera informe.md, comparacion.csv, recomendacion.json y las corridas detalladas. No hace falta lanzar los tres experimentos manualmente.

Por defecto todas las escenas, incluidas oclusiones y cruces, ofrecen uno de cada cinco frames. Para revision exhaustiva usar --paso-revision 1. Los omitidos quedan fuera de los denominadores. La revision humana es necesaria para distinguir realmente al objetivo de un distractor; el guion de acciones no se convierte en verdad de terreno automaticamente.

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

## Revision vacia y controles, 2026-11-20

Se corrige el fallo de archivo ausente al omitir todos los frames. La anotacion crea su archivo de estado al comenzar, sin inventar etiquetas. Si termina vacia el asistente indica revision incompleta y permite --continuar sobre la captura ya completada. Las teclas desconocidas ya no avanzan silenciosamente. Enter y S abren revision. Hay botones Revisar, Omitir y Salir. N inicia una escena durante captura y omite un fotograma durante anotacion; ambos contextos se indican en pantalla.

Pasaron tres regresiones nuevas de archivo vacio, tecla desconocida seguida de Enter y mensaje de archivo ausente. La causa exacta de la captura del usuario no puede confirmarse sin su video; el codigo previo solo escribia el JSON al revisar un frame, de modo que omitir todos o no decodificar frames producia el error observado.

## Confirmacion sin Enter

Se reemplaza cv2.selectROIs por un selector propio. Arrastrar y soltar agrega cada recuadro. Confirmar con clic o Espacio termina la lista; Z deshace; 0 confirma escena vacia; Esc interrumpe sin etiquetar ausencia. La revision de enrolamiento tambien acepta Espacio o clic en Aprobar. Se reconocen codigos Enter adicionales de Qt, conservando Enter como alternativa.

Pasaron 37 pruebas Python locales, incluidas cinco regresiones del selector: arrastre inverso, clic sin teclado, Espacio, vacio frente a cancelar y guardado de etiquetas por el punto de entrada. Falta verificar el comportamiento nativo de teclado y raton en el Ubuntu del NUC. Las capturas anteriores se retoman con --continuar.

## Confirmacion directa en modo solo, 2026-11-22

La anotacion corresponde a las referencias humanas para evaluar los algoritmos. Dibujar un recuadro define su ubicacion y confirmar define que esa anotacion esta revisada. En una escena con distractores hace falta indicar ademas cual identidad es el objetivo.

El anotador detecta automaticamente solo=true desde guia.json de la captura, incluso al retomar con --continuar. En ese modo un unico recuadro confirmado se guarda directamente como objetivo, sin pantalla de segundo clic. Si se redibuja, el nuevo recuadro reemplaza al anterior. Para una escena vacia se usa 0 o el boton Escena vacia. En el anotador independiente tambien se puede indicar --solo.

Para varias personas se mantiene la seleccion explicita de identidad, con los bordes y numeros visibles. Se corrigio la desaparicion visual de los bordes en esa pantalla y se coloco el boton Ausente debajo de la imagen para no interceptar clics sobre el cuerpo. El guardado se realiza despues de la identidad y se muestra el numero acumulado de etiquetas en la siguiente pantalla, ademas de registrarse por terminal.

Las etiquetas previamente revisadas se conservan al continuar. Las nuevas pruebas comprueban deteccion automatica de --solo, guardado persistente del objetivo sin segundo clic, reemplazo al redibujar y bordes/clic en el modo multiple. La verificacion del raton nativo del NUC sigue pendiente.

## Muestreo practico de revision, 2026-11-23

Tras la carga manual observada por el usuario se elimina la excepcion que obligaba a revisar todos los frames de oclusion/cruce. La bateria usa paso 5 en todas las escenas, aproximadamente veinte imagenes por clip de diez segundos a 10 FPS nominales. --paso-revision 1 permite la revision exhaustiva. Se registra el paso en sesion.json. Al continuar se conservan todas las etiquetas existentes, incluso si son mas densas que el muestreo nuevo. La recuperacion temporal medida con etiquetas dispersas tiene menor precision; revisar ventanas concretas despues si hace falta.

## Escena vacia desde la pantalla inicial, 2026-11-23

El fallo estaba en pedir_revision: la tecla 0 se aceptaba dentro del selector de recuadros, pero se ignoraba en la pantalla inicial del fotograma. Se agrega 0 y el boton Vacia desde esa primera pantalla. Ambos guardan inmediatamente frames[indice]=[] y avanzan, sin dibujar. N conserva su significado de omitir. En la seleccion de identidad con otras personas, 0 sigue significando objetivo ausente y conserva los recuadros de los distractores.

Pasaron las catorce pruebas locales de revision/selector, incluidas tres nuevas para 0 inicial, clic inicial y guardado persistente de [] por el flujo de anotacion. La interaccion nativa del NUC sigue pendiente. No se realizo commit.
