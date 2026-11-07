# Contexto y finalidad de LUMI

Actualizado: 2026-11-07. Base documental preliminar para revisión del equipo.

LUMI es un proyecto académico de innovación e inteligencia artificial de Víctor Jopia y Vicente Riveros, en la Universidad Católica del Norte, Coquimbo. El stakeholder principal, patrocinador y validador es el Dr. Juan Bekios Calfa, usando la grafía del Charter. El usuario confirmó que la mención anterior a Juan Villegas fue un error de dictado.

## Problema y visión

Transportar objetos mientras se camina exige esfuerzo e interacción constante con cargas o carros. Agricultura, logística y asistencia a personas mayores son posibles aplicaciones futuras. No son escenarios ya validados ni autorizan ampliar el MVP.

## MVP actual

Validar una plataforma pequeña que enrola visualmente a una persona, conserva su identidad frente a terceros, la sigue y regula su distancia en superficies lisas y regulares. No transporta cargas significativas ni sube escaleras o circula por terrenos irregulares. Procesamiento local, sin depender de una API remota para identificar o seguir.

El equipo describe un chasis metálico, cuatro ruedas y cuatro motores DC, agrupados por lado para dirección tipo tanque. Esto describe la intención de diseño, no un inventario verificado ni orugas físicas.

## Estado y lectura

- Estructura y documentación: presentes; aplicación, firmware y resultados experimentales: aún no implementados en esta base.
- Raspberry Pi 5 de 4 GB, sin acelerador dedicado de IA, o mini PC i3: plataformas candidatas. Modelo exacto, alimentación y rendimiento pendientes.
- Python para IA es la orientación del usuario; C/C++ para firmware y componentes de control, propuesta por concretar.
- Cámara obligatoria; sensores y controlador pendientes. ROS 2 es la preferencia de integración.
- Enrolamiento mediante botón y giro de la persona: interacción propuesta, no comportamiento ya validado.

Consultar [alcance](../docs/alcance.md) para métricas y [fuentes](../docs/fuentes-y-pendientes.md) para contradicciones. No convertir recomendaciones técnicas en decisiones aprobadas.
