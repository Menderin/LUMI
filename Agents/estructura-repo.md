# Estructura del repositorio LUMI

Esta estructura organiza el proyecto de robot seguidor de personas. Las carpetas reservan espacio para el trabajo acordado; su existencia no implica que los módulos estén implementados ni que la arquitectura esté validada.

## Árbol inicial

~~~text
LUMI/
├── README.md
├── AGENTS.md
├── .gitignore
├── Agents/
│   ├── estructura-repo.md
│   ├── contexto.md
│   ├── ODD.md
│   ├── plantilla-trabajo.md
│   ├── gestion-y-alcance.md
│   ├── desarrollo.md
│   ├── investigacion-ia.md
│   ├── hardware-y-seguridad.md
│   └── pruebas.md
├── software/
│   ├── percepcion/
│   ├── control/
│   ├── comunicacion/
│   └── configuracion/
├── firmware/
│   └── controlador/
├── hardware/
│   ├── componentes.md
│   ├── conexiones/
│   └── mecanica/
├── pruebas/
│   ├── software/
│   └── integracion/
├── modelos/
│   └── README.md
├── docs/
│   ├── alcance.md
│   ├── arquitectura.md
│   ├── decisiones.md
│   ├── instalacion.md
│   ├── evaluacion-ia.md
│   ├── fuentes-y-pendientes.md
│   ├── trabajo/
│   └── validacion/
├── herramientas/
└── .venv/                     # Local; excluido de Git
~~~

Las carpetas reservadas contienen un archivo .gitkeep para que Git conserve su ubicación. Los archivos de instrucciones adicionales se añadirán cuando sean necesarios.

## Finalidad y contenido

| Ruta | Finalidad | Contenido esperado |
| --- | --- | --- |
| README.md | Presentar el proyecto y facilitar su navegación. | Objetivo, estado y enlaces a documentación. |
| AGENTS.md | Punto de entrada para agentes. | Reglas comunes y referencias a Agents/. |
| Agents/ | Centralizar instrucciones de trabajo. | Esta guía y futuras reglas de desarrollo, pruebas y contexto. No contiene el código del robot. |
| software/ | Agrupar el programa que ejecutará la Raspberry Pi o el mini PC. | Módulos de percepción, control e integración; punto de entrada cuando se acuerde la arquitectura. |
| software/percepcion/ | Detectar y seguir a la persona objetivo. | Captura y procesamiento de imágenes, detección y seguimiento. |
| software/control/ | Transformar observaciones en decisiones de movimiento. | Cálculo de distancia y dirección, estados y condiciones de parada acordadas. |
| software/comunicacion/ | Conectar el programa principal con el controlador. | Protocolo, envío de órdenes, recepción de datos y tratamiento de fallos de comunicación. |
| software/configuracion/ | Mantener parámetros del sistema. | Configuraciones de cámara, seguimiento y control; documentar unidades y valores pendientes. No guardar secretos. |
| firmware/ | Agrupar programas ejecutados en microcontroladores. | Código y configuración de compilación específicos de la placa elegida. |
| firmware/controlador/ | Operar motores y sensores desde el microcontrolador. | Lectura de sensores, actuación, recepción de comandos y paradas correspondientes al firmware. |
| hardware/ | Documentar el equipo físico. | Inventario, conexiones y montaje. |
| hardware/componentes.md | Registrar componentes disponibles y seleccionados. | Modelo exacto, función, disponibilidad y restricciones verificadas. |
| hardware/conexiones/ | Permitir reproducir el cableado. | Esquemas eléctricos, alimentación y tablas de pines. |
| hardware/mecanica/ | Documentar montaje y estructura física. | Chasis, medidas, planos, piezas y fotografías útiles. |
| pruebas/ | Verificar el comportamiento del sistema. | Pruebas de software e integración ligadas a criterios de aceptación. |
| pruebas/software/ | Verificar lógica de los módulos. | Pruebas automatizadas y datos sintéticos pequeños. |
| pruebas/integracion/ | Verificar interacción entre módulos y hardware. | Procedimientos y programas de prueba, requisitos del equipo y escenarios controlados. |
| modelos/ | Identificar y reproducir el uso del modelo de IA. | Referencias, licencia, versión, instrucciones de descarga y configuración. Evitar pesos grandes en Git. |
| docs/ | Mantener documentación técnica y acuerdos trazables. | Alcance, arquitectura, decisiones, instalación y validación. |
| docs/alcance.md | Delimitar qué se implementa. | Funciones, exclusiones y pendientes, diferenciando propuestas de acuerdos confirmados. |
| docs/arquitectura.md | Explicar cómo se relacionan los componentes. | Responsabilidades, flujo de datos e interfaces; propuestas identificadas como tales. |
| docs/decisiones.md | Conservar la justificación técnica. | Decisión, estado, alternativas, motivo y referencia a su acuerdo. |
| docs/instalacion.md | Permitir preparar y ejecutar el proyecto. | Sistemas compatibles, versiones verificadas, dependencias y pasos reproducibles. |
| docs/validacion/ | Conservar evidencia de cumplimiento. | Protocolos, métricas, resultados, incidencias y limitaciones. Los scripts van en pruebas/. |
| herramientas/ | Facilitar desarrollo y diagnóstico. | Utilidades de calibración, inspección y preparación; no lógica principal del robot. |
| .venv/ | Aislar dependencias de Python en cada equipo. | Entorno generado localmente. No administra varias versiones de Python ni se copia entre equipos. |

## Reglas de mantenimiento

- Mantener la separación entre software del equipo principal, firmware y documentación de hardware.
- Conservar los .gitkeep mientras hagan falta para mantener directorios sin contenido; pueden retirarse cuando haya archivos versionados.
- No versionar .venv, cachés, compilaciones, credenciales ni datos pesados. Los manifiestos de dependencias sí se versionan cuando se definan.
- La carpeta .venv inicial solo está reservada: su .gitkeep no crea un entorno Python funcional. Crearlo con el intérprete acordado mediante python -m venv .venv.
- No fijar versiones, umbrales de seguridad, modelos o componentes sin evidencia o acuerdo.
- Python para percepción e integración y C/C++ para firmware es la propuesta inicial. CMake y Conan se incorporarán si se acuerda usarlos; no se crean configuraciones ficticias.
- Mantener esta guía sincronizada con cambios de estructura y vincular trabajo y evidencias con las tarjetas de Trello.

## Documentos de trabajo y fuentes

Agents/ contiene reglas para ejecutar trabajo; docs/ contiene conocimiento del producto. No copiar requisitos completos en cada guía: enlazar su fuente canónica.

| Documento | Contenido y momento de lectura |
| --- | --- |
| Agents/contexto.md | Propósito, MVP y contexto al comenzar |
| Agents/ODD.md | Flujo flexible y criterios para documentar trabajo |
| Agents/plantilla-trabajo.md | Formato para un cambio sustancial |
| Agents/gestion-y-alcance.md | Consulta de fuentes, incrementos y cambios de alcance |
| Agents/desarrollo.md | Convenciones, interfaces y herramientas candidatas |
| Agents/investigacion-ia.md | Reglas de comparación y manejo de datos |
| Agents/hardware-y-seguridad.md | Diseño eléctrico, actuación y pruebas físicas |
| Agents/pruebas.md | Evidencia requerida según tipo de cambio |
| docs/evaluacion-ia.md | Hipótesis PCA/autoencoder/Re-ID y diseño experimental |
| docs/fuentes-y-pendientes.md | Procedencia, discrepancias y datos faltantes |
| docs/trabajo/ | Registros ODD por cambio sustancial; no segundo backlog |
| docs/validacion/protocolo-preliminar.md | Criterios, condiciones y evidencias de evaluación |

Los PDFs en docs/ son fuentes originales: conservarlos y enlazarlos, sin sobreescribirlos con interpretaciones. La estructura no impone aún un workspace ROS: cuando se seleccione, documentar distribución de paquetes y actualizar esta guía antes de reorganizar código.

## Datos y enrolamiento

~~~text
software/percepcion/
├── dataset/             # Herramientas de captura/preparación; README inicial
└── enrolamiento/        # Lógica de registro de usuario; README inicial
datos/
├── README.md
├── originales/          # Secuencias y metadatos locales
├── procesados/          # Frames/recortes/anotaciones derivados
├── particiones/         # Manifiestos locales de splits
└── enrolamientos/       # Galerías/representaciones por sesión
docs/construccion-dataset.md  # Diseño del proceso y guía para implementación
~~~

datos/ se conserva como espacio de trabajo local: únicamente README y .gitkeep se versionan. Las herramientas sí se versionan en software/percepcion/dataset/. En directorios con archivos útiles retirar .gitkeep; mantenerlo únicamente donde no hay contenido. Una carpeta con subdirectorios que ya se conservan tampoco necesita marcador propio.

## Colaboración con Git

Agents/git-y-ramas.md explica ramas, commits, pull requests, versiones y recuperación de errores para el equipo y los agentes. El flujo main más ramas de tarea es una propuesta para revisión; no configura protecciones ni crea ramas.
