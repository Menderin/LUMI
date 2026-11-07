# Desarrollo de software y firmware

## Límites y contratos

Mantener lógica de IA separada de transporte ROS y de actuación. El reconocimiento produce observaciones con tiempo de captura, candidato, puntuación y validez; el control decide movimiento; firmware opera motores y detecta comandos caducados. No tratar la puntuación de una distancia como probabilidad sin calibración.

Antes de integrar, documentar unidades, signos, frecuencia, caducidad, estados inválidos y respuesta ante fallos. Los nombres de mensajes y temas en arquitectura son propuestas hasta fijar contratos.

## Lenguajes y herramientas

Python para experimentación e IA. C/C++ para firmware; C++ en ROS 2 es candidato para control e interfaces cuando aporte valor medido. No reescribir inferencia en C++ por intuición.

ROS 2 vive en el computador Linux; un microcontrolador necesita firmware propio. Serie y micro-ROS son alternativas, no dependencias simultáneamente obligatorias. En ROS usar el ecosistema ament/colcon y gestión de dependencias de ROS; evaluar Conan para bibliotecas C++ externas si resuelve una necesidad concreta. Conan no es un compilador.

Fijar versiones después de verificar plataforma, compatibilidad y licencias. Mantener manifiestos y comandos reproducibles cuando existan; no crear comandos de ejecución ficticios. .venv es local y no se versiona; revisar compatibilidad del intérprete con ROS antes de crearlo.

## Convenciones iniciales

Usar nombres descriptivos, Python snake_case, parámetros con unidades y configuración fuera de lógica. Comentar decisiones físicas o matemáticas no evidentes. Validar medidas y tiempos antes de actuar. No incluir pesos grandes, capturas personales, secretos, cachés o compilaciones en Git.

Comprobar cambios con pruebas pertinentes y documentar fallos. No ocultar una prueba fallida ni afirmar ejecución en hardware sin haberla realizado.
