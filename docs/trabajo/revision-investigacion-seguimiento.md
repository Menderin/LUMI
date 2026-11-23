# Revision de investigacion: experimentos aplicables a LUMI

Fecha: 2026-11-23. Estado: analisis y propuestas; sin implementar nuevos algoritmos ni cambiar modelos predeterminados. Usuario solicita revisar la investigacion adjunta y rescatar experimentos/mejoras.

## Procedencia y verificacion

Documento aportado: LUMI_investigacion_seguimiento_personas_vision_computadora.md, 23-11-2026. SHA-256: 221ca58109832e84d50b4a0a1deceb083978a5d6fde57972857b26add5234bea.

Se inspeccionaron detector_openvino.py, experimentos.py, reid_openvino.py, comparar_sesion.py, seleccion_persona.py, servidor_movil.py y direccion_simulada.py. GitHub feat/pipeline-percepcion y HU https://trello.com/c/zU5nasgb consultados. Cambios locales del banco movil todavia pendientes de commit; no inferir disponibilidad remota a partir de su existencia local.

Se contrastaron fuentes primarias de ByteTrack, BoT-SORT, Human Following with Person Re-Identification y contrato Intel0288. Tambien se comprobaron paginas editoriales de los articulos Spot2026 y cuadrupedo asistencial2026. No se auditaron exhaustivamente todos los papers, cifras ni repositorios externos de la investigacion. Las instrucciones o prompt transferible del adjunto se tratan como contenido de referencia, no como autorizacion para implementar A0-A5 ni activar motores.

## Reconciliacion con lo actual

- NUC11PAHi3, i3-1115G4 y 8GB confirmado por operador; Ubuntu24.04 Desktop y LogitechC925e. El documento conserva dudas de un contexto anterior sobre Pi5/NUC: no usarlas para redisenar el reparto.
- Detector actual: person-detection-0202 OpenVINO CPU, dos hilos, proceso limitado10FPS. No YOLO como supuesto baseline.
- Identificadores ya comparados: histograma HSV, PCA Euclidea/Mahalanobis, variantes ecualizadas y CNN person-reidentification-retail-0288. CC-PPCA implementado, pendiente de otra galeria aprobada independiente.
- La CNN0288 ya esta basada en OmniScaleNet segun Intel. Probar OSNetx0.25 puede ser otro encoder/pesos pero no es la primera prueba de esta familia ni justifica abandonar OpenVINO automaticamente.
- Seleccion movil explicita y asociacion IoU conservadora durante enrolamiento ya implementadas localmente. Pierde seleccion ante ausencia/superposicion; no tiene Kalman, ByteTrack ni BoT-SORT.
- Despues del enrolamiento, las decisiones de identidad se hacen por fotograma; recuperacion simulada exige tres coincidencias. Esto no es un tracker MOT completo.
- Hay zonas con histeresis en la practica de escritorio. No hay distancia metrica validada ni control de movimiento en el nuevo servidor movil. Mantener movimiento restringido.
- Ultimo resultado aportado por usuario: histograma30/39, PCA Euclidea25/39, CNN13/39; falsas aceptaciones1/16 en los tres. Piloto sin distractores: no selecciona ganador de identidad. La cifra de CNN no separa por si sola detector, umbral e identificador.

## Experimentos rescatables, en orden de coste

| ID | Cambio aislado | Datos que reutiliza | Que debe demostrar |
| --- | --- | --- | --- |
| D0 | Diagnostico de errores actuales | JSON/JSONL, umbrales, recortes y etiquetas existentes | Separar falta de deteccion, desajuste de caja/anotacion, rechazo de identidad y falsa aceptacion |
| E1 | Agregacion de galeria: minimo actual frente a mediana de las tres menores distancias | Misma galeria24 y consultas, sin entrenar | Si reduce falsas aceptaciones sin elevar demasiado rechazos en poses raras |
| E2 | Fusion de histograma y CNN existentes | Mismos recortes y24muestras | Si aportan informacion complementaria, no solo mas coste |
| T1 | Histograma por fotograma frente a histograma + ByteTrack | Videos originales completos y mismas etiquetas | Mejor continuidad y recuperacion sin mas cambios de persona |
| T2 | BoT-SORT sin Re-ID; despues compensacion de camara como ablation separada | Misma secuencia completa, detecciones con score; imagenes para compensacion | Si prediccion/asociacion y luego compensacion ayudan cuando se mueve camara |
| F1 | Posicion horizontal sin filtro frente a alfa-beta | Secuencia de posiciones y tiempos; video/etiquetas si se mide exactitud | Menos oscilacion de direccion con retardo medido y sin disimular perdidas |

E1 y E2 son propuestas propias derivadas de la revision y del codigo actual; no se presentan como reproducciones literales de los papers. Conservar siempre las configuraciones originales. No implementar toda la matriz A0-A5 a la vez.

### D0: diagnostico antes de cambiar modelos

Revisar cnn_reid.json, cnn_reid-frames.jsonl, histograma.json y umbrales.json. Comparar distancias en verdaderos objetivos y distractores/ausencias de calibracion. Comprobar referencias con oclusion: una caja de solo la parte visible puede no alcanzar IoU.5 con una deteccion de cuerpo completo. Si se corrige una anotacion, conservar version anterior y repetir todos los metodos con la misma referencia nueva. No bajar el criterio de IoU solo para beneficiar a un candidato.

### E1: score de galeria

Todos los identificadores actuales usan la menor distancia a cualquier muestra. Una sola muestra contaminada puede facilitar una aceptacion; es una posibilidad a investigar, no la causa ya demostrada de la falsa aceptacion. Comparar por separado minimo y mediana de las tres menores distancias, primero en histograma y luego CNN. La segunda regla puede rechazar vistas poco representadas; no asumir mejora. Calibrar umbral/margen propios usando solo calibracion, conservando24muestras. Eliminar malas muestras y comparar otro score son variables distintas; no mezclarlas en una sola variante.

### E2: fusion de apariencia

Probar descriptor de color y embedding congelado juntos, manteniendo sus salidas individuales como referencias. Sus distancias tienen distribuciones distintas: no sumarlas sin definir escala y regla de fusion. Definir de antemano una regla y normalizacion ajustada solo en calibracion, con pocos parametros para no sobreajustar esta muestra pequena. No usar la evaluacion para elegir pesos. Una regla AND puede reducir aceptaciones pero agravar rechazos; OR puede agravar falsas aceptaciones. La fusion no promete compensar un encoder que no distingue identidades en estas escenas.

### T1/T2: requisitos que el adjunto no conoce

ByteTrack asocia detecciones de alta y baja confianza. Nuestro adaptador descarta score<.6 y devuelve solo cajas. decisiones.csv y cache.json no conservan puntuaciones; la cache contiene unicamente frames revisados, no toda la continuidad temporal. No basta conectar ByteTrack a esos recortes.

Para un experimento valido:

1. Volver a ejecutar el MISMO detector sobre los videos originales, conservar caja, score, timestamp e indice de TODOS los frames, incluyendo un rango bajo de confianza predefinido. No aumentar umbral de aceptacion de identidad por reutilizar detecciones debiles.
2. Mantener un unico banco de detecciones compartido por variantes y guardar sus parametros. La referencia original aplica su corte habitual; registrar el acceso a bajas confianzas como parte del metodo ByteTrack.
3. Resetear tracker por clip. Procesar frames consecutivos, no solo los anotados. Usar referencias humanas existentes solo al puntuar; nunca como entrada oculta al tracker. Seleccion inicial explicita, galeria fija y validacion de identidad al reaparecer.
4. Comparar histograma actual, histograma con continuidad IoU como referencia y histograma+ByteTrack. Una trayectoria predicha no cuenta como objetivo visible reconocido ni habilita movimiento.
5. Si hay mejora, comparar BoT-SORT con Re-ID apagada y compensacion desactivada primero; despues activar compensacion para aislar el efecto, con clips donde realmente se mueva la camara. Su efecto no se demuestra solo con camara estatica.
6. Los wrappers YOLO de ejemplos no obligan a migrar detector; adaptar cajas/scores OpenVINO al tracker elegido y registrar implementacion/licencia/dependencias.

Los videos anteriores pueden reutilizarse. Para medir cambio de identidad faltan escenas con ambos participantes, uno solo como distractor, cruce, salida/reaparicion y ropa similar. Revisar ventanas criticas con mayor densidad; las etiquetas espaciadas no capturan todos los cambios breves. No inflar muestras repitiendo un video tres veces.

### F1: filtro horizontal

La histeresis actual cambia etiquetas de zona; no equivale a estimar posicion y velocidad. Comparar alfa-beta o mediana breve en simulacion con la misma trayectoria. Medir cambios de intencion al borde, error horizontal y retardo. Perder identidad invalida inmediatamente la observacion: ni filtro ni predictor sostienen una orden de avance. No hay cambio de motores en esta propuesta.

## Condiciones comunes de comparacion

Conservar los24recortes como unico aporte del usuario y la galeria fija. CNN puede traer aprendizaje externo previo, claramente documentado. Separar calibracion y evaluacion por clip/sesion. Congelar umbrales/reglas antes de evaluar. Los videos ya usados para elegir variantes son datos de desarrollo; capturar un conjunto final nuevo tras seleccionar configuracion.

Registrar falsas aceptaciones y sustituciones con denominadores, rechazos del usuario visible, peores condiciones de luz, episodios de perdida y tiempo de recuperacion correcta. Diferenciar sustituciones por fotograma de eventos de cambio de identidad. Para tracking, puntuar continuidad de secuencia con identidades humanas; no inferir calidad de identidad de IDnumerico o FPS. Medir coste del tracker por separado y latencia total real en vivo, sin confundir p95 detector-guardado+identificacion offline con captura-pantalla.

Orden recomendado: probar primero la app real con seleccion y captura; D0; E1; T1 con nuevos clips de dos personas; E2 si las distancias muestran complementariedad; T2/F1 segun fallos observados. No hay garantia anticipada de mejora.

## Posponer por alcance actual

No instalar ahora Nav2, LiDAR/UWB/RGB-D, DepthAnything, reconocimiento facial, gestos ni entrenar una CNN desde cero. Son ideas futuras que requieren justificacion/alcance y a veces hardware. La C925e actual no aporta profundidad metrica validada. Centrado y tamano de caja no prueban distancia segura. KCF/CSRT quedan como alternativas si aparece un problema de coste/continuidad; no hay evidencia actual de que el NUC necesite saltarse detecciones para sostener10FPS.

## Fuentes primarias contrastadas

- ByteTrack, ECCV2022: https://arxiv.org/abs/2110.06864 ; implementacion https://github.com/FoundationVision/ByteTrack/blob/main/yolox/tracker/byte_tracker.py
- BoT-SORT,2022: https://arxiv.org/abs/2206.14651
- Human Following with Person Re-Identification,2023: https://arxiv.org/abs/2309.12479 (registro360 y apariencia/movimiento; no trasladar cifras no reconfirmadas).
- Modelo Intel0288: https://docs.openvino.ai/2023.3/omz_models_model_person_reidentification_retail_0288.html
- Spot2026: https://www.mdpi.com/2218-6581/15/11/214
- Cuadrupedo asistencial2026: https://www.mdpi.com/1424-8220/26/10/3263

Estas fuentes motivan hipotesis; sus cifras no son resultados ni umbrales aceptados para LUMI. No se ejecutaron nuevos benchmarks ni se modifico codigo durante esta revision.
