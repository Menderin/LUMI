# Guía de entrada para agentes de LUMI

Leer [estructura del repositorio](Agents/estructura-repo.md) antes de añadir archivos.
Este archivo es un índice: cargar las guías relevantes según el trabajo, sin duplicarlas aquí.

| Trabajo | Lectura requerida |
| --- | --- |
| Comenzar o retomar | [Contexto](Agents/contexto.md), [flujo ODD](Agents/ODD.md) y [fuentes](docs/fuentes-y-pendientes.md) |
| Requisitos y prioridades | [Gestión y alcance](Agents/gestion-y-alcance.md), [alcance](docs/alcance.md) |
| Código e interfaces | [Desarrollo](Agents/desarrollo.md), [arquitectura](docs/arquitectura.md), [decisiones](docs/decisiones.md) |
| Datos y enrolamiento | Ver la sección específica de datos y enrolamiento de este archivo |
| Plan de percepción acordado | [Dataset, experimentos y estados del robot](docs/plan-percepcion.md) |
| IA y experimentos | [Investigación de IA](Agents/investigacion-ia.md), [evaluación de IA](docs/evaluacion-ia.md) |
| Motores, sensores y firmware | [Hardware y seguridad](Agents/hardware-y-seguridad.md), [componentes](hardware/componentes.md) |
| Ramas, commits y colaboración | [Guía de Git y ramas](Agents/git-y-ramas.md), propuesta para revisión del equipo |
| Verificar o entregar | [Pruebas](Agents/pruebas.md), [protocolo preliminar](docs/validacion/protocolo-preliminar.md) |

Las guías son específicas de este repositorio. No instalar herramientas, configurar otros repositorios ni activar delegación por el mero hecho de leerlas. El pedido del usuario y los acuerdos de alcance gobiernan el trabajo.

## Datos, construcción del dataset y enrolamiento

Antes de construir o modificar este flujo, leer [el protocolo de construcción](docs/construccion-dataset.md), [las instrucciones de investigación de IA](Agents/investigacion-ia.md) y [la organización de datos locales](datos/README.md).

| Trabajo o contenido | Ubicación y referencia |
| --- | --- |
| Captura, extracción, anotación y particiones | Código en [software/percepcion/dataset/](software/percepcion/dataset/README.md) |
| Registro del usuario durante la operación | Código en [software/percepcion/enrolamiento/](software/percepcion/enrolamiento/README.md) |
| Secuencias fuente y metadatos de adquisición | datos/originales/ |
| Frames, recortes y anotaciones derivados | datos/procesados/ |
| Manifiestos de ajuste, calibración y evaluación | datos/particiones/ |
| Galerías y representaciones por sesión | datos/enrolamientos/ |
| Protocolos, resultados agregados y limitaciones | docs/validacion/; seguir [evaluación de IA](docs/evaluacion-ia.md) |

### Reglas para futuros agentes

- Comprobar primero qué herramientas y datos existen; las carpetas reservadas no demuestran que haya un dataset disponible. Para trabajo sustancial, seguir [ODD](Agents/ODD.md).
- Preparar un piloto con la cámara a la altura e inclinación previstas; registrar su geometría y repetir la validación cuando esté montada en el robot. No asumir que los datos externos reproducen esa perspectiva.
- Separar construcción del dataset, entrenamiento, calibración, enrolamiento y evaluación. Mantener secuencias independientes y evitar frames vecinos o derivados del mismo original en particiones distintas.
- Conservar originales y trazabilidad de cada recorte, etiqueta y transformación mediante manifiestos locales. Usar identificadores pseudónimos; no convertir predicciones del modelo en etiquetas verificadas sin revisión.
- Versionar código, guías y resultados agregados. Mantener capturas, metadatos personales, galerías y embeddings dentro de las rutas locales excluidas de Git; comprobar .gitignore antes de añadir archivos. No subir esos datos al repositorio.
- Documentar configuración, particiones, comprobaciones y limitaciones. No afirmar capturas, entrenamiento ni métricas que no se hayan ejecutado.
- La documentación no autoriza activar cámaras, capturar personas ni mover hardware; ejecutar esas acciones cuando estén incluidas en el pedido autorizado.
