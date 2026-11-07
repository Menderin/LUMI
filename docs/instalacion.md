# Entorno e instalación: estado preliminar

No hay todavía aplicación ejecutable, firmware compilable, dependencias fijadas ni comandos de prueba del robot. Esta guía prepara decisiones; no constituye una instalación validada.

## Plataformas candidatas

Pi 5 arm64 o mini PC i3 amd64 con Linux. ROS 2 Jazzy y Ubuntu 24.04 de 64 bits son una opción documentada por ROS para ambas arquitecturas; elegir tras verificar periféricos y soporte del equipo. No inferir compatibilidad de cámara solo por compatibilidad del SO.

## Python y ROS

Elegir un intérprete compatible con la distribución ROS y sus paquetes. .venv reserva el entorno local, no versiones múltiples del intérprete. Después de acordarlo, crear desde la raíz:

~~~sh
python3 -m venv .venv
~~~

En Windows el ejecutable puede ser python; no asumir que ese entorno ejecutará paquetes ROS de Linux. Recrear el entorno en cada plataforma. Definir explícitamente si necesita acceso a paquetes del sistema; no instalar otra versión de Python encima de ROS sin verificar ABI y dependencias.

## C/C++ y firmware

La placa determina toolchain y herramientas de carga. ROS usa ament/colcon en el computador; firmware usa el SDK de la placa seleccionada. CMake es candidato de construcción y Conan de dependencias externas cuando haga falta; ninguno es el compilador por sí mismo.

Antes de publicar pasos operativos, registrar versiones, manifiestos, compilador, SO, arquitectura, cámara, permisos de dispositivo, comandos de compilación/prueba y ejecución observada. No descargar pesos ni flashear placas como parte de esta preparación documental.
