# Enrolamiento comparable y direccion simulada

## Objetivo y decisiones vigentes

Implementacion del plan aprobado el 2026-11-20. Perfil inicial OpenVINO CPU con dos hilos y 10 FPS de proceso. El usuario observo aproximadamente 25 % CPU global y 18 % CPU LUMI en el NUC. Son observaciones del laboratorio, pendientes de una corrida registrada independiente.

Se comparan histograma HSV/Bhattacharyya, PCA/Euclidea y PCA/Mahalanobis regularizada. Los dos PCA comparten exactamente la media y la base de proyeccion calculada sobre la misma galeria. Las operaciones BLAS del ajuste y de la CLI offline se limitan a dos hilos. Cada candidato recibe las mismas detecciones guardadas y los mismos recortes. Re-ID y entrenamiento de autoencoders quedan para el siguiente bloque.

## Practica en vivo

Desde la raiz del repo actualizado, en la terminal del escritorio del NUC:

```bash
source .venv-practica/bin/activate
python -m pip install -r software/percepcion/requirements-openvino.txt
python -m software.percepcion.practica --camara 0
```

El detector por defecto es OpenVINO y el tope es 10 FPS. Usa --descargar-modelo si faltan pesos, o --detector hog para la referencia HOG. Los FPS de la camara siguen solicitandose a 15; la iteracion de proceso esta limitada a 10. Revisar FPS efectivos y CPU en pantalla.

- **E** solicita enrolamiento con una unica persona visible. Hay tres segundos para prepararse y luego doce segundos de grabacion de video fuente mientras giras despacio. Al terminar se reabre el video y se extraen hasta 24 recortes repartidos por los fotogramas validos. Se requieren al menos 20. Los tramos con cero o varias personas y los recuadros cortados por los bordes se descartan.
- Revisar el video y las 20-24 miniaturas en una unica ventana con botones. **Enter** aprueba identidad y cobertura frente/espalda/perfiles. La sesion queda en **Listo**. Si la galeria no tiene variacion para PCA, se informa fallo y se permite reintento.
- **S** inicia seguimiento solo con coincidencia vigente. Tras perdida/ambiguedad muestra Buscando objetivo y, en esta simulacion, reanuda automaticamente despues de tres coincidencias validas consecutivas.
- **C** cancela y descarta la galeria activa. **R** repite si hay una sola persona visible e intentos disponibles. Maximo cinco capturas efectivamente iniciadas por proceso, incluida cada captura cancelada. Cancelar durante la cuenta regresiva no consume captura.
- **V** inicia/finaliza un clip fuente sin anotaciones. **Esc** termina y cierra los archivos. Grabar calibracion y evaluacion en clips diferentes, independientes del video de enrolamiento.
- El modo en vivo inicial usa histograma con umbral provisional 0,45 y margen 0,08. Para pruebas manuales de PCA usar --metodo euclidea o --metodo mahalanobis y un --umbral especifico. Las escalas de las distancias son diferentes. La seleccion formal se hace offline, sin ajustar umbrales mirando la evaluacion.

La galeria aprobada queda en galeria-N/, con recortes, galeria.json y representaciones NPZ por metodo. El JSON se escribe despues de guardar los artefactos. Los videos de intentos descartados se conservan como evidencia local.

## Direccion simulada y acciones comunes

La ventana dibuja limites nominales al 40 % y 60 % del ancho. Usa el centro del recuadro del objetivo identificado, y muestra Girar izquierda, Alineado o Girar derecha. La zona central indica alineacion horizontal. La distancia no se estima en esta practica.

Histeresis de tres puntos porcentuales: desde centro entra a izquierda por debajo de 0,37 o derecha sobre 0,63. Izquierda retorna al centro al llegar a 0,43; derecha retorna al llegar a 0,57. Un salto de un extremo al otro cambia directamente. Al perder objetivo se borra el estado lateral y se indica Detener / sin objetivo.

SesionEnrolamiento expone acciones iniciar, confirmar, cancelar, repetir, iniciar_seguimiento y reanudar. Devuelve aceptacion y expone estado, intentos, segundos restantes y muestras. La ventana usa esa logica; el adaptador futuro de la app debe invocarla en el mismo propietario de sesion del NUC. El panel de banco existente sigue siendo una herramienta independiente. No se crea un segundo propietario ni un servidor nuevo en esta entrega.

decisiones.csv agrega zona, x_normalizada, intencion y detector_ms. Las intenciones son diagnosticos visuales, sin conexion a ROS ni a la ESP.

## Anotacion manual

Grabar objetivo solo, escena vacia, distractor solo, cruces, oclusiones y transiciones interior/exterior en ambas direcciones. Mantener la ropa dentro del bloque y el detector/configuracion durante la comparacion. Guardar consentimiento e IDs pseudonimos segun la guia de datos.

Para cada clip, indicar particion y escenario, por ejemplo:

```bash
python -m software.percepcion.anotar_practica datos/enrolamientos/SESION/prueba-100.avi --split calibracion --escenario interior-exterior-cruce --paso 5
python -m software.percepcion.anotar_practica datos/enrolamientos/SESION/prueba-400.avi --split evaluacion --escenario interior-exterior-cruce --paso 5
```

Sustituir SESION y nombres por los archivos de la captura. Con 10 FPS nominales, paso 5 es aproximadamente 2 Hz. Usar paso 1 en un clip corto de cruce, perdida o transicion para revisar todos sus fotogramas. El tiempo real viene del CSV, no del FPS nominal del AVI.

En la ventana, **S** revisa el fotograma y **N** lo omite. Seleccionar TODAS las personas con el raton y Enter entre recuadros; Esc termina la seleccion. Los recuadros se numeran. En la terminal indicar cual numero corresponde al objetivo, o 0 si esta ausente. Esc sin recuadros y S de revision confirma escena vacia. Los fotogramas omitidos no cuentan como negativos.

Se guarda prueba-100.anotaciones.json junto al video, con split, escenario, objetivo y frames revisados. Se puede reabrir para continuar los pendientes. Para corregir etiquetas ya revisadas editar ese JSON local y volver a preparar una cache nueva. La identidad del objetivo se etiqueta como objetivo y los distractores como otro-N por fotograma; las metricas de sustitucion son conteos de frames, no trayectorias individuales de cada distractor.

## Comparacion offline

Preparar una cache nueva con la galeria aprobada y todos los clips anotados:

```bash
python -m software.percepcion.comparar_sesion preparar datos/enrolamientos/SESION/galeria-1 datos/procesados/comparacion-01 datos/enrolamientos/SESION/prueba-100.avi datos/enrolamientos/SESION/prueba-400.avi
python -m software.percepcion.comparar_sesion calibrar datos/procesados/comparacion-01 datos/particiones/umbrales-01.json
python -m software.percepcion.comparar_sesion evaluar datos/procesados/comparacion-01 datos/particiones/umbrales-01.json datos/procesados/resultados-01
```

Agregar los demas clips al primer comando. Debe haber calibracion con objetivo visible, ausencia y distractores. La preparacion reutiliza decisiones.csv de cada carpeta de captura y extrae los recortes de los AVI originales. Rechaza videos repetidos por hash y el video de enrolamiento. Requiere clips grabados con la version actual por el campo detector_ms. No vuelve a ejecutar OpenVINO. Todas las referencias son humanas y solo se puntuan los frames revisados.

La calibracion usa una busqueda acotada de hasta 24 umbrales y 12 margenes por metodo. Busca cero selecciones incorrectas observadas y maximiza el peor acierto visible por escenario, luego aciertos totales. Si solo consigue rechazar todo marca util=false. Guarda un unico umbral/margen por metodo para todos los escenarios. No sobrescribe una configuracion previa.

La evaluacion valida la firma de calibracion y hashes de galeria y recortes. Reutiliza los parametros congelados, sin consultar etiquetas de evaluacion al calibrar. Recortes vecinos del mismo video nunca se dividen entre particiones. No mezclar derivados del mismo recorrido entre calibracion y evaluacion; el hash solo detecta duplicados exactos, no videos reexportados.

## Resultados y limites de interpretacion

- comparacion.csv incluye revisados, visibles, ausentes, objetivo_detectado, perdidas_detector, rechazos del identificador, rechazos totales, correctos, falsas aceptaciones, sustituciones y selecciones incorrectas con objetivo visible, peor acierto visible, p95, CPU y RSS.
- Un JSON por metodo separa escenarios y denominadores. Frames JSONL por metodo guardan las distancias, seleccion, referencia y metricas para auditar errores.
- Cualquier sustitucion observada o seleccion incorrecta descarta esa configuracion para integracion. El ranking favorece el peor escenario de luz, p95, CPU y RAM. Si no hay candidata util, recomendacion.json indica null.
- La recuperacion_muestreada_s mide desde el primer fotograma revisado sin acierto hasta el siguiente acierto de la secuencia. Con anotacion dispersa es una aproximacion, no un tiempo exacto de recuperacion. Revisar ventanas criticas a paso 1.
- La latencia offline separa identificacion y suma detector registrado + identificacion sobre cache. No representa latencia fisica camara-pantalla ni mide de nuevo carga del detector. CPU/RSS de la comparacion son del proceso offline; el consumo completo esta en recursos.csv de la captura. La RSS puede incluir modelos compartidos y bibliotecas ya cargadas.
- La prueba en vivo demuestra interfaz y flujo. La eleccion requiere resultados revisados, tres repeticiones por perfil y validacion posterior. Cero sustituciones en el piloto no garantiza comportamiento general.

## Evidencia

Pruebas sinteticas del flujo completo de galeria, AVI, cache, calibracion y evaluacion. Verificar tambien cuenta regresiva, cinco intentos, cancelacion, confirmacion sin inicio, reanudacion explicita, histeresis y perdida. La prueba fisica con la C925e y participantes en el NUC queda pendiente.

Referencia de gestion: https://trello.com/c/zU5nasgb

Verificacion ejecutada en el entorno local Windows con OpenCV 4.14.0 y scikit-learn 1.9.1. Pasaron las 18 pruebas Python previas/al momento de la integracion, mas una regresion de la ventana por teclado agregada posteriormente. Se comprobo creacion de los tres NPZ con la misma PCA, que confirmar queda Listo y que S inicia seguimiento. Total actual 19 pruebas. La comparacion usa datos sinteticos y no acredita rendimiento en participantes reales.

## Correccion de captura y controles, 2026-11-20

El usuario solicita 24 recortes y video de 12 segundos tras observar nueve recortes y un fallo de enrolamiento. El muestreo anterior cada 0,8 s y su limite de doce se reemplazan en la practica por extraccion posterior desde el AVI fuente. No se duplica un frame para rellenar la galeria. El intervalo de captura usa reloj monotonico. El FPS del AVI sigue siendo nominal; el tiempo real de cada fotograma queda en el JSON de captura. Los lectores offline aceptan galerias anteriores de 8-12 y nuevas de hasta 24.

Se registra enrolamiento-N.captura.json con indices, tiempos y detecciones originales; enrolamiento-N.extraccion.json con origen de cada recorte y conteos sin persona/varias/borde; acciones.json con teclas/acciones aceptadas o rechazadas y motivo. Los fallos de extraccion o PCA mantienen la ventana en Fallo, con opcion de repetir. Ante otra excepcion se guarda error.json con traceback y estado antes de cerrar.

Las teclas aceptan mayusculas y minusculas. Se agregan botones clicables para Enrolar, Repetir, Cancelar, Seguir y Grabar. En revision los botones son Aprobar, Repetir, Cancelar y Salir. S durante la revision indica que primero debe aprobarse con Enter. S en Listo o Perdido requiere una coincidencia valida; la razon de rechazo se muestra en pantalla. Se vacian acciones pendientes al salir de revision para que una pulsacion anterior no inicie seguimiento.

Pasaron 22 pruebas Python locales, incluida una corrida por el punto de entrada de la ventana con reloj/camara simulados, AVI reproducible, captura de 12 s, extraccion de 24 recortes, aprobacion y S posterior. Se verificaron mayusculas, clics, fallo recuperable, videos incompletos y compatibilidad con galerias previas. El cierre informado por el usuario no tiene traceback disponible; no se afirma haber determinado su causa. La interfaz nativa de Ubuntu y el video de la C925e requieren revalidacion en el NUC.

## Reencuentro automatico en la simulacion, 2026-11-20

El usuario solicita seguir buscando despues de una oclusion, como quedar detras de una silla. La ventana ya seguia capturando y puntuando imagenes; lo que bloqueaba la reanudacion era el estado Perdido y la exigencia de otra pulsacion S.

La practica activa recuperacion_simulada=True. La primera activacion sigue requiriendo galeria aprobada y S. Tras una perdida la interfaz y el CSV indican Buscando objetivo. Se exige coincidencia no ambigua con la galeria fija durante tres fotogramas consecutivos y luego se reanuda el seguimiento visual sin otra pulsacion. Una ausencia, rechazo o ambiguedad reinicia el contador. A 10 FPS efectivos son aproximadamente 0,3 s; depende de la frecuencia real.

Cancelar, repetir o un fallo borran el contador. Aprobar una galeria nueva sigue dejando Listo hasta pulsar S. La recuperacion se registra en acciones.json como reanudar con origen recuperacion_simulada. Configuracion.json registra el modo y el requisito de tres coincidencias. La clase compartida mantiene recuperacion_simulada=False por defecto; esta decision pertenece al piloto visual. Las rotaciones fisicas y su seguridad no se implementan aqui.

Verificacion: pasaron 23 pruebas Python locales. La prueba por el punto de entrada de la ventana simula una oclusion, ve zona Buscando y comprueba reanudacion posterior sin nueva S. Tambien verifica que ambiguedad reinicia el contador, que la galeria permanece fija y que cancelar impide reanudar. La prueba con silla y Logitech en el NUC queda pendiente.

## Ejecucion guiada integrada

El nuevo comando python -m software.percepcion.guiada encadena captura y comparacion. Ver [bateria guiada](bateria-guiada.md). El modo --solo permite medir con una persona e informa que falta validar distractores.
