# Propuesta de tratamiento de imágenes de LUMI

**Estado:** propuesta para el laboratorio. Complementa el [plan de percepción](plan-percepcion.md), el [protocolo de captura](construccion-dataset.md) y la [guía de experimentos](evaluacion-ia.md).

## Del vídeo al objetivo

```text
Cámara RGB → fotograma con marca de tiempo → detector de personas → recorte corporal
  → representación visual → comparación con galería → asociación temporal
  → objetivo válido o sin objetivo

Cámara RGB → copia JPEG para el teléfono
```

- Montar la cámara a la altura e inclinación previstas. Comprobar encuadre a 1,2, 1,5 y 1,8 m, con frente, espalda y perfiles. Registrar resolución, FPS, montaje y, si la cámara los expone, exposición y balance de blancos.
- Empezar con un canal RGB fijo. Si la cámara entrega imágenes estéreo sincronizadas, preservar ambas con un ID de par, timestamps y calibración. Si entrega profundidad alineada, registrar unidades y alineación. Evaluar profundidad por separado para estimar distancia. Un recuadro por sí solo no da una distancia fiable.
- El detector produce recuadros de personas en coordenadas del fotograma original. Recortar desde la imagen original, con la caja limitada a sus bordes. Durante el enrolamiento, aceptar solo tramos con una persona visible y recortes utilizables. Revisar desenfoque, cuerpo truncado y tamaño insuficiente en el piloto antes de fijar umbrales.
- La app recibe una copia JPEG comprimida. La inferencia usa el fotograma de la cámara en la Pi o el NUC. La app muestra vídeo y solicita acciones. El ESP32 recibe órdenes de la base y no participa en el tratamiento de imágenes.

## Enrolamiento y galería

Con los motores deshabilitados en el banco, ubicar al usuario a 1,5 m e iniciar un giro continuo y pausado de 10 segundos. Conservar hasta 12 recortes espaciados al menos 0,8 s. Usar 8 como mínimo provisional y verificar frente, espalda y ambos perfiles con el operador. Omitir muestras de tramos con múltiples personas. Un intento fallido se descarta y puede repetirse hasta el máximo de cinco intentos de la sesión.

Guardar localmente la galería propuesta del intento que cumple los criterios. Para los experimentos, conservar los recortes en color a su resolución disponible junto al manifiesto. La aprobación técnica y la confirmación del operador son pasos distintos. Una vez confirmada, mantener fija la galería durante el seguimiento. El reconocimiento compara con esa galería y emite «sin objetivo» si falta una coincidencia vigente e inequívoca.

## Preparación por experimento

| Método | Entrada y tratamiento | Comparación |
| --- | --- | --- |
| Histograma de color | HSV. Dos regiones centrales del cuerpo, torso y parte inferior. Histograma H–S de 16×8 por región, normalizado y sin píxeles de relleno. | Distancia de Bhattacharyya. |
| PCA | Escala de grises a 128×64 y 64×32 (alto×ancho). Mantener proporción con relleno. Ajustar hasta ocho componentes según el rango de la galería. | Euclídea y Mahalanobis regularizada sobre la misma proyección. |
| OSNet x0.25 | RGB a 256×128 y preprocesamiento correspondiente a los pesos. Extraer y normalizar el embedding. Considerar 128×64 si el coste lo justifica. | Distancia coseno. |
| Autoencoder condicional | Si la comparación inicial lo justifica y hay datos independientes, probar RGB a 128×64 y 64×32, latente de 32 dimensiones y entrenamiento offline. | Coseno sobre latentes. Reportar reconstrucción por separado. |

Usar los mismos recortes de origen y muestras de galería para comparar métodos. Primero medir identificación con cajas anotadas. Repetir después con cajas del detector para localizar qué etapa falla. Probar galería de una sola iluminación y galería mixta con igual máximo de muestras. Medir interior, exterior y transiciones en ambos sentidos. Calibrar el umbral de cada configuración antes de abrir la evaluación reservada.

## Archivos y trazabilidad

| Ubicación local | Contenido |
| --- | --- |
| `datos/originales/` | Vídeos fuente sin sobrescribir y metadatos de cámara. |
| `datos/procesados/` | Recortes derivados y resultados por fotograma. |
| `datos/enrolamientos/` | Galerías por sesión con identificadores pseudónimos. |
| `datos/particiones/` | Manifiestos de enrolamiento, calibración y evaluación. |

Registrar sesión, origen, fotograma o timestamp, caja XYXY en píxeles, geometría, partición, iluminación y motivo de descarte cuando aplique. Anotar identidad, caja y visibilidad a 2 Hz y revisar todos los fotogramas de cruces, oclusiones y reapariciones. Cada vídeo, sus derivados y sus pares estéreo pertenecen a una sola partición. Capturar con consentimiento. Guardar imágenes y embeddings fuera de Git y compartir configuraciones y resultados agregados.

## Primera validación en laboratorio

1. Abrir la cámara y confirmar el encuadre desde el teléfono.
2. Grabar una secuencia breve desde el soporte y revisar los recortes de un detector compatible.
3. Verificar que el giro produce recortes útiles en las cuatro vistas. Incluir un tramo con dos personas y comprobar su exclusión.
4. Comparar la galería contra otro vídeo que incluya un distractor, una salida del objetivo y un cambio de luz. Registrar rechazos, falsas aceptaciones, sustituciones y latencia.
5. Repetir con la cámara montada en el chasis antes de usar los resultados para habilitar seguimiento físico.

El banco offline ya admite galerías preparadas en disco. La captura automática de recortes y la conexión del enrolamiento real con la app siguen pendientes.
