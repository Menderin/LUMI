# Contexto y finalidad de LUMI

Actualizado: 2026-11-07. Base documental preliminar para revisión del equipo.

LUMI es un proyecto académico de innovación e inteligencia artificial de Víctor Jopia y Vicente Riveros, en la Universidad Católica del Norte, Coquimbo. El stakeholder principal, patrocinador y validador es el Dr. Juan Bekios Calfa, usando la grafía del Charter. El usuario confirmó que la mención anterior a Juan Villegas fue un error de dictado.

## Problema y visión

Transportar objetos mientras se camina exige esfuerzo e interacción constante con cargas o carros. Agricultura, logística y asistencia a personas mayores son posibles aplicaciones futuras. No son escenarios ya validados ni autorizan ampliar el MVP.

## MVP actual

Validar una plataforma pequeña que enrola visualmente a una persona, conserva su identidad frente a terceros, la sigue y regula su distancia en superficies lisas y regulares. No transporta cargas significativas ni sube escaleras o circula por terrenos irregulares. Procesamiento local, sin depender de una API remota para identificar o seguir.

El equipo describe un chasis metálico, cuatro ruedas y cuatro motores DC, agrupados por lado para dirección tipo tanque. Esto describe la intención de diseño, no un inventario verificado ni orugas físicas.

## Estado y lectura

- Hay código de experimentos, app Android, puente ROS y firmware de banco Wi-Fi/USB. Compilación/arranque y algunas pruebas lógicas están registradas; percepción operativa, integración ROS en Raspberry y movimiento físico estable no están validados. Leer docs/trabajo/banco-wifi-motores.md para la evidencia actual.
- Cambio confirmado por usuario el 2026-11-19 por presupuesto: Raspberry Pi 3 Model B, 1 GB RAM. Sustituye Pi 5/NUC como equipo previsto. Preparar Ubuntu Server 24.04 arm64 + ROS 2 Jazzy ros-base según docs/instalacion.md; rendimiento completo de IA pendiente de medición.
- Python para IA es la orientación del usuario; C/C++ para firmware y componentes de control, propuesta por concretar.
- Cámara obligatoria; sensores y controlador pendientes. ROS 2 es la preferencia de integración.
- Enrolamiento mediante botón y giro de la persona: interacción propuesta, no comportamiento ya validado.

Consultar [alcance](../docs/alcance.md) para métricas y [fuentes](../docs/fuentes-y-pendientes.md) para contradicciones. No convertir recomendaciones técnicas en decisiones aprobadas.

## Decisiones vigentes

Consultar docs/decisiones.md, docs/plan-arquitectura-raspberry-esp.md y docs/video-ros-pi3.md. La ruta actual es Ubuntu Server por consola/SSH, ROS 2 Jazzy ros-base y una captura de cámara compartida. GUI opcional. El modo Wi-Fi directo de ESP es temporal para motores; no sustituye la arquitectura con Raspberry. No dar por resuelto un rechazo HTTP ni un problema de potencia porque se haya generado un APK.


Banco temporal vigente 0.5.0: el control de la app usa UDP 8082 con ACK y tickets emitidos por ESP; HTTP 8080 es para estado. No estimar reloj de ESP en Android. Firmware cargado con autopruebas correctas y PWM cero; mando del teléfono pendiente de validar. [Contrato V2](../docs/trabajo/banco-protocolo-v2.md).
