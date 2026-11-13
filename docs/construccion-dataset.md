# Construcción del dataset y captura para enrolamiento

Estado: propuesta preliminar solicitada por el usuario. No se han capturado datos, descargado datasets ni implementado herramientas.

## Objetivo y separación de datos

Construir evidencia visual representativa de la cámara baja del robot para comparar identificación y seguimiento. No asumir que los datasets públicos son inútiles ni afirmar que no existe uno con vista baja sin una búsqueda específica. Los datos externos pueden servir como punto de partida, pero la evaluación del MVP debe incluir su cámara y condiciones reales.

| Uso | Datos | Qué puede ajustarse |
| --- | --- | --- |
| Desarrollo/entrenamiento | Sesiones destinadas al ajuste del modelo o preprocesamiento aprendido | PCA, encoder o parámetros aprendidos según experimento |
| Calibración | Sesiones separadas con objetivo y distractores | Umbrales y configuración; no usar la prueba final |
| Enrolamiento | Breve secuencia permitida del usuario antes del seguimiento | Galería/representación y, solo si se define, ajuste por sesión |
| Evaluación | Secuencias posteriores e independientes al enrolamiento | Nada: configuración congelada; medir identidad y seguimiento |

En un experimento de enrolamiento puede aparecer la misma persona en galería y evaluación: precisamente se evalúa reconocerla, pero las secuencias deben ser distintas. Si se afirma generalización de un encoder a usuarios nuevos, separar además identidades entre entrenamiento del encoder y evaluación. No mezclar ambos objetivos en una única métrica.

## Empezar antes de terminar el robot

1. Elegir la cámara candidata y un soporte estable que reproduzca altura, inclinación y orientación previstas. No hace falta tener motores funcionando.
2. Medir la altura del centro óptico sobre el suelo y registrar inclinación, resolución, FPS, lente y ajustes de exposición disponibles. No inventar una altura definitiva.
3. Comprobar que cabeza, torso y piernas resultan visibles al menos en el intervalo de seguimiento del Charter (1,2–1,8 m). Si el cuerpo queda cortado, revisar encuadre/óptica antes de recolectar masivamente.
4. Capturar un piloto pequeño: giro de enrolamiento con robot/cámara detenidos y recorridos independientes con frente, espalda, lateral, entrada/salida de imagen y cruces supervisados.
5. Revisar detección y recortes manualmente. Si la vista baja impide localizar personas, esa incertidumbre debe resolverse antes de comparar distancias de PCA.
6. Al montar la cámara en el robot, registrar una nueva versión de geometría y repetir evaluación: vibración, movimiento, exposición y alimentación pueden cambiar las imágenes. El piloto no demuestra funcionamiento móvil.

No se necesita entrenar un detector desde cero para comenzar: evaluar primero uno existente y su licencia. Si falla, documentar los casos y decidir si ajustar encuadre, detector o datos. Ninguna alternativa queda aprobada automáticamente.

## Matriz de captura propuesta

- Objetivo enrolado y varias personas distractoras; planificar diversidad sin fijar un número de participantes como criterio aún no acordado.
- Secuencias completas de frente, espalda y lateral, giro y desplazamiento; no solo fotos aisladas seleccionadas por éxito.
- Distancias del rango nominal y condiciones de pérdida de encuadre registradas; detener físicamente el robot durante captura piloto.
- Cruces, oclusiones, ropa parecida y distintos fondos e iluminación dentro del alcance controlado.
- Fondos sin personas y distractores sin objetivo para probar rechazo; no confundir ausencia con muestra positiva.
- Varias sesiones y, cuando sea viable, días distintos. Registrar cambios de ropa; decidir si son parte de evaluación actual o un desafío futuro, sin prometer invariancia a ropa.

Definir cantidades después del piloto observando cobertura de situaciones y errores. Miles de frames vecinos no equivalen a miles de ejemplos independientes.

## Manifiesto mínimo propuesto

Un CSV/JSON local por adquisición o conjunto debe registrar: dataset_version, session_id, sequence_id, participant_id pseudónimo, rol objetivo/distractor/ausente, camera_id, geometry_version, altura_m, inclinacion_grados, resolución, FPS y marca temporal/frame de origen, archivo relativo, vista, iluminación y split. Para recortes: bbox en píxeles con convención explícita y vínculo al original. Si se mide distancia, indicar método y referencia; dejar desconocida cuando no se midió.

Separar la identidad humana revisada del ID automático del tracker. Permitir escenas con varias personas y varias anotaciones por frame. No etiquetar al candidato de menor distancia como verdad de terreno. Documentar recortes truncados, detecciones faltantes y casos ambiguos; excluir o revisar con razón registrada.

## Procesamiento y particiones

Conservar originales, derivar frames y recortes sin sobrescribirlos y registrar configuración. Mantener relación de aspecto con una estrategia documentada; comparar las resoluciones de evaluacion-ia.md sin cambiar simultáneamente todos los factores.

Separar sesiones/secuencias antes de aumentación y ajuste de PCA, normalizadores, covarianza o encoder. No colocar frames vecinos ni versiones aumentadas del mismo original en splits distintos. Calcular estadísticas aprendidas con los datos permitidos; la prueba final no participa en selección de umbrales. [Referencia: prevención de fuga de datos](https://scikit-learn.org/1.5/common_pitfalls.html).

Los datasets públicos requieren revisión de licencia, perspectiva, anotaciones y correspondencia con el MVP. Como ejemplo, [PRID2011](https://www.tugraz.at/institute/icg/research/team-bischof/learning-recognition-surveillance/downloads/prid11/) contiene secuencias y poses en distintas vistas; esto no prueba que reproduzca la altura de LUMI ni autoriza descargarlo.

## Ubicación y entrega a otro agente

- Herramientas: software/percepcion/dataset/.
- Lógica de enrolamiento en operación: software/percepcion/enrolamiento/.
- Datos reales y metadatos: datos/, según su README; excluidos de Git salvo guías y marcadores.
- Resultados agregados y protocolo: docs/validacion/; modelos y recetas: modelos/.

Primera implementación sugerida, pendiente de pedido de código: capturar una sesión con cámara configurable, producir un manifiesto y extraer una muestra revisable. Después agregar anotación/particiones; finalmente integrar enrolamiento con el modelo seleccionado. No entrenar, activar cámara ni mover hardware por la mera existencia de esta propuesta.

## Evidencia para dar por preparada una versión del dataset

Verificar trazabilidad de recortes a originales, metadatos de geometría, cobertura de vistas y negativos, etiquetas revisadas, particiones sin cruces de secuencia y configuración reproducible. Registrar conteos por persona/sesión/vista y motivos de descarte. No declarar representatividad ni métricas de precisión sin datos observados. Volumen mínimo y protocolo final quedan para revisión del equipo.

## Piloto acordado

Capturar 4–6 participantes con consentimiento. Registrar geometría y comprobar encuadre a 1,2, 1,5 y 1,8 m. Separar enrolamiento, calibración y evaluación por sesión. Registrar un giro continuo pausado de 10 s en interior y otro en exterior. Capturar recorridos nominales interior→interior y exterior→exterior, transiciones en ambas direcciones, cruces, oclusiones, escena vacía y distractores solos. Mantener ropa por bloque. Anotar a 2 Hz y exhaustivamente en ventanas críticas.

Empezar con un RGB fijo. Si se dispone de estéreo sincronizado, guardar ambos originales, tiempos, calibración y rectificación. Para profundidad, registrar unidades y alineación. Usar el mismo identificador de par en el manifiesto.

El [validador](../software/percepcion/dataset/manifiesto.py) lee JSON con una clave `secuencias`. Cada entrada requiere `id`, `sesion`, `split`, `origen` y `video` relativo al manifiesto. Los derivados deben repetir el ID de origen. Añadir `par_estereo` si corresponde. Para ejecutar evaluación, incluir `escenario`, `objetivo` y `frames`, un mapa de números de fotograma (base cero) a listas de objetos con `id` y `bbox` XYXY en píxeles. Una lista vacía indica ausencia observada. Una clave omitida indica fotograma sin anotar. Mantener geometría y metadatos adicionales junto a cada entrada.
