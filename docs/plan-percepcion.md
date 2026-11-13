# Plan acordado de percepción de LUMI

Este documento reúne el plan del piloto y los experimentos de la [HU de Vicente](https://trello.com/c/zU5nasgb). Las 18 horas-persona son una referencia para el primer bloque. La adaptación profunda y la validación física se reestiman después del piloto.

## Enrolamiento y estados

Con el robot detenido y el usuario a 1,5 m, una pulsación inicia 10 segundos de giro continuo y pausado. Puede dar más de una vuelta. Capturar frente, espalda y ambos perfiles. Guardar hasta 12 recortes válidos espaciados y omitir tramos con varias personas. El operador verifica cobertura en el piloto. Ajustar el mínimo de recortes durante el piloto.

Al vencer el plazo, crear una galería fija de sesión si la captura cumple los criterios. Una segunda pulsación, con coincidencia válida, habilita el seguimiento. Si falla, descartar muestras y permitir reintento, con un máximo de cinco capturas iniciadas. Ante pérdida o ambigüedad, detenerse. Confirmar visualmente al usuario y exigir otra pulsación para reanudar.

| Estado | Señal |
| --- | --- |
| Espera | Todos apagados |
| Enrolando | Ámbar fijo |
| Fallo de enrolamiento | Ámbar intermitente |
| Listo | Tres destellos verdes y luego todos apagados |
| Siguiendo | Verde fijo |
| Perdido o ambiguo | Rojo fijo |

Verificar con participantes que entienden las señales. Probar la secuencia con motores deshabilitados. El enrolamiento correcto no debe causar movimiento. Consultar [arquitectura y transiciones](arquitectura.md).

## Dataset

- Piloto propio con 4–6 personas. Usar soporte a la altura e inclinación previstas y comprobar encuadre a 1,2, 1,5 y 1,8 m. Registrar geometría, resolución, FPS, exposición y balance de blancos si están disponibles. Repetir validación al montar la cámara en el chasis.
- Comenzar con un RGB fijo mientras se confirma la cámara de doble lente. Si entrega pares sincronizados, guardar originales, marcas de tiempo y calibración. Si entrega profundidad, registrar unidades y alineación. Mantener cada par y sus derivados en una sola partición.
- Separar por persona sesiones de enrolamiento, calibración y evaluación. Capturar enrolamientos interior y exterior. En calibración y evaluación grabar recorridos interior→interior, exterior→exterior y transiciones continuas en ambas direcciones. Incluir cruces, oclusiones, escena vacía y distractores sin objetivo. Mantener la ropa dentro del bloque.
- Anotar recuadros, identidad y visibilidad a 2 Hz y revisar todos los fotogramas de ventanas críticas. Registrar IDs pseudónimos, origen, sesión, escenario, fase de luz, geometría y partición. Guardar datos, anotaciones y galerías en datos/, fuera de Git.
- Usar [JRDB](https://jrdb.erc.monash.edu/dataset/) y [L-CAS](https://lcas.lincoln.ac.uk/wp/research/data-sets-software/l-cas-rgb-d-t-re-identification-dataset/) como referencias. La evaluación de LUMI requiere captura propia a su altura y distancia. Ver [protocolo y manifiesto](construccion-dataset.md).

## Experimentos

Vídeo → detector → recorte corporal → representación → comparación con galería → asociación temporal → objetivo válido o sin objetivo.

El ejecutor recibe vídeo, manifiesto, galería y configuración, y registra decisiones y tiempos por fotograma. Comparar identificación primero con cajas manuales y luego con detecciones. Calibrar un umbral por método para las cuatro condiciones de luz y congelarlo antes de abrir la evaluación. Comparar galería de una sola iluminación y galería mixta con el mismo máximo de 12 recortes.

| Ensayo | Configuración acordada |
| --- | --- |
| Detección | Dos detectores ligeros preentrenados en CPU. Elegir por recuperación del objetivo visible con IoU ≥ 0,5, luego falsos positivos y latencia p95. |
| Color | HSV H–S de 16×8 bins por región central de torso y parte inferior, sin relleno. Normalizar y comparar con Bhattacharyya. |
| PCA | Gris 128×64 y 64×32, alto×ancho, conservando proporción. Hasta ocho componentes según rango del enrolamiento. Comparar Euclídea y Mahalanobis regularizada con la misma proyección. |
| CNN Re-ID | OSNet x0.25 fijo a 256×128, embeddings normalizados y coseno. Probar 128×64 con calibración propia si la latencia lo justifica. |
| Asociación | Comparar decisión por fotograma y asociación IoU en los dos mejores identificadores. Exigir identidad válida al reaparecer. |
| Autoencoder condicional | Si fallan los primeros métodos y hay datos independientes suficientes, entrenar en RGB a 128×64 y 64×32, latente de 32 dimensiones, L1 y parada temprana. Comparar latentes por coseno y reportar reconstrucción por separado. |

Las dos RTX A5000 están disponibles para entrenamiento offline. El primer bloque utiliza modelos preentrenados. Evaluar una GAN posteriormente solo si se identifica una brecha de iluminación que justifique ese estudio. Ver [configuración y ejecución](evaluacion-ia.md).

## Selección y entrega

- Reportar falsas aceptaciones, rechazos del objetivo visible, sustituciones, recuperación e intentos de enrolamiento, con conteos y denominadores por dirección del cambio de luz. Una sustitución observada en cruce, oclusión o transición descarta la configuración para integración.
- Entre candidatas que cumplen, priorizar el acierto con objetivo visible en el peor escenario de luz. Desempatar por latencia p95 y RAM máxima. Seleccionar en calibración y confirmar sobre evaluación reservada.
- Ejecutar candidata y respaldo tres veces por equipo disponible, con los mismos vídeos, en Pi 5 de 4 GB y NUC i3. Registrar p50/p95, FPS, CPU, RAM y temperatura disponible. La respuesta física se valida en el chasis.
- Verificar particiones sin fugas, escenas vacías sin objetivo, decisiones equivalentes entre repeticiones y patrones LED. Enlazar scripts, configuraciones, resultados agregados y recomendación desde la HU. Registrar qué pruebas siguen pendientes y por qué.

## Punto de partida para continuar

Consultar el [registro de implementación](trabajo/pipeline-percepcion.md) y la rama local feat/pipeline-percepcion. Distinguir el plan de las pruebas realmente ejecutadas. No hay capturas propias ni resultados en Pi 5 o NUC documentados todavía.
