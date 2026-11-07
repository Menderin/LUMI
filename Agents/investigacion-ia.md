# Investigación y experimentos de IA

Leer docs/evaluacion-ia.md y el análisis tecnológico fuente. Separar detección de personas, asociación temporal e identificación del usuario enrolado. Un identificador de tracker no demuestra identidad persistente; PCA no detecta personas por sí solo.

## Comparaciones reproducibles

- Mantener detector, recortes, particiones y condiciones equivalentes entre alternativas cuando se compara el identificador.
- Separar enrolamiento, calibración y evaluación por secuencia o sesión; no repartir frames vecinos aleatoriamente entre entrenamiento y prueba.
- Incluir personas no enroladas, cruces, espalda, oclusiones e iluminación dentro del escenario acordado.
- Registrar configuración, semillas, versiones, hardware y calentamiento; medir latencia de extremo a extremo, no solo la proyección PCA.
- Ajustar umbrales con calibración y congelarlos antes de evaluación; no adaptar automáticamente la identidad con recortes dudosos.
- No asumir que error pequeño de reconstrucción implica identidad correcta o que Mahalanobis siempre mejora Euclídea.

Las imágenes y embeddings del usuario se conservan localmente con finalidad, acceso y retención definidos por el equipo; no subirlos al repositorio. Usar resultados agregados y datos sintéticos pequeños para pruebas versionadas. Registrar procedencia y licencia de modelos y datasets externos.

Un informe debe permitir distinguir mejora real, variación experimental y falta de evidencia. No adoptar automáticamente Person Re-ID, autoencoder o un detector específico: comparar y proponer la decisión.

## Captura y enrolamiento

Para construir datos leer [construccion-dataset.md](../docs/construccion-dataset.md). Implementar herramientas en software/percepcion/dataset/ y lógica de sesión en software/percepcion/enrolamiento/. Los datos reales viven en datos/, con exclusión de Git. Separar entrenamiento, calibración, galería y evaluación; no asumir que hay que terminar el robot ni entrenar desde cero para iniciar un piloto con cámara baja.
