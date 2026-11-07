# Datos locales de LUMI

El repositorio versiona esta guía y los .gitkeep, no los datos capturados ni sus metadatos personales. .gitignore excluye el contenido de las carpetas siguientes.

| Carpeta | Finalidad |
| --- | --- |
| originales/ | Secuencias capturadas y metadatos de adquisición; conservar como fuente sin sobrescribir |
| procesados/ | Frames, recortes y anotaciones derivados, trazables a originales |
| particiones/ | Manifiestos locales de ajuste, calibración y evaluación |
| enrolamientos/ | Galerías y representaciones del usuario por sesión de operación |

No usar nombres reales en rutas o IDs. Conservar consentimiento y cualquier tabla de correspondencias fuera del repositorio y separados de los datos de experimentación. El equipo debe definir acceso, ubicación de respaldo y retención antes de capturar. Git no es el respaldo de estos datos.

Ver [construcción del dataset](../docs/construccion-dataset.md). Las carpetas están reservadas; no hay imágenes ni enrolamientos reales todavía.
