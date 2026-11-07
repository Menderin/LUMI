# Herramientas de construcción del dataset

Esta carpeta contendrá código Python de captura, extracción de frames, revisión de recortes, anotación y generación de particiones. No almacenar aquí imágenes ni videos personales.

Guía de diseño para implementar: [construcción del dataset](../../../docs/construccion-dataset.md). Datos locales: [datos/](../../../datos/README.md). Enrolamiento de operación: [enrolamiento/](../enrolamiento/README.md).

## Implementaciones posibles, todavía no presentes

- Capturador con OpenCV: seleccionar cámara, registrar geometría y configuración, grabar secuencias y un manifiesto por sesión.
- Extracción reproducible: muestrear temporalmente, conservar tiempo/frame de origen y evitar miles de imágenes casi idénticas.
- Recortador/anotador: proponer bounding boxes con detector y permitir revisión humana; registrar identidad pseudónima y casos sin detección.
- Particionador por sesiones/secuencias: separar ajuste, calibración y prueba antes de aumentación o ajuste de PCA.
- Auditor: detectar rutas inexistentes, etiquetas ausentes, sesiones mezcladas, duplicados y cambios de geometría.

Son responsabilidades propuestas, no scripts ejecutables ni dependencias instaladas. Antes de programar elegir un primer flujo mínimo y sus verificaciones; no crear una aplicación de anotación completa si basta revisar archivos y un manifiesto.
