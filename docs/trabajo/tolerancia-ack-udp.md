# Tolerancia acotada a ACK perdidos — Android 0.6.0

Fecha: 2026-11-19. Corrección de transporte del banco temporal Android→Wi-Fi ESP. Firmware V2 no cambia: PWM 60 %, máximo 5 s, rearme manual y watchdog 250 ms desde recepción válida. Arquitectura final Raspberry/ROS 2→USB→ESP se conserva.

## Problema observado

Usuario confirma giro durante el perfil nuevo y no percibe sobrecalentamiento por ahora. Es observación manual sin medida de temperatura, no aceptación eléctrica. Reporta `Sin ACK UDP de adelante #418 en 180 ms; no se confirmó la recepción`. La app 0.5.x convertía cada timeout individual en error fatal: cerraba socket y solicitaba parada, aunque solo se hubiera perdido una confirmación. La ausencia de ACK no permite saber si el datagrama de mando llegó o si se perdió su respuesta.

## Cambio de comportamiento

Durante adelante/atrás se mantiene envío nominal cada 50 ms. Cada datagrama lleva request y seq nuevos; nunca se retransmite una orden vieja. Una espera individual de hasta 45 ms sirve para recoger confirmaciones, sin bloquear la siguiente renovación durante 180 ms. Si no hay respuesta, se conserva socket y sesión y se muestra ACK pendiente; no se ordena parada por esa única ausencia. Una sola llamada de envío/recepción se ejecuta a la vez, pero varias solicitudes recientes pueden esperar ACK.

Se admiten confirmaciones de solicitudes pendientes recientes del mismo sentido, boot y epoch. La ventana acepta ACK con menos de 200 ms desde envío y solo mientras no se haya agotado la ventana de silencio; descarta IDs desconocidos, duplicados y respuestas anteriores a una ya confirmada. El RTT registrado corresponde al envío original, no al tiempo de espera de la llamada que finalmente recoge la respuesta. Los estados viejos siguen filtrados por MotorSessionToken.

Criterios de fallo: cuatro esperas consecutivas sin respuesta, o 200 ms sin una confirmación válida. La espera de recepción se acota al presupuesto restante de esa ventana; una respuesta posterior no revive el gesto. Entonces se bloquea el mando y se intenta parada; una nueva habilitación explícita es necesaria. NACK explícito del firmware, cambio de boot/epoch, JSON inválido o fallo de socket siguen siendo errores que detienen; no se ocultan mediante reintentos.

Ping/rearme siguen requiriendo ACK propio (hasta 600 ms); parada mantiene su confirmación de hasta 180 ms. No se arma automáticamente al recuperar la red. Durante el gesto ya preparado se evita un ping bloqueante de refresco antes de cada renovación: se usan tickets de ACK/estado reciente y la ESP sigue comprobando su vigencia de menos de 250 ms. Antes del primer movimiento se puede refrescar por ping, sin solicitar movimiento durante ese ping.

La marca de petición en vuelo se libera al terminar el trabajo de red mediante un campo volatile, sin esperar un callback de interfaz. El sondeo de estado y el joystick siguen en la app existente. La cadencia de 50 ms es nominal; no se promete tiempo real en Android/Wi-Fi.

## Seguridad temporal conservada

No se modifica la ESP ni se amplía su watchdog a segundos para ocultar pérdida de enlace. Si dejan de llegar órdenes válidas, el firmware sigue desarmando a los 250 ms desde la última recepción válida. Máximo de movimiento 5 s y parada al soltar se conservan. La tolerancia de ACK no autoriza reanudar tras caducidad, reinicio, parada o inversión. El límite PWM no mide/limita corriente ni certifica el driver L298N.

## Comprobaciones

Pruebas Java deterministas de ventana: una respuesta perdida tolerada, ACK reciente retrasado, ID desconocido, duplicado, reinicio explícito de ventana, agotamiento al cuarto timeout y bloqueo tras 200 ms sin reactivación por respuesta tardía.

Pruebas reales UDP de loopback Windows: pérdida de un ACK, dos ACK consecutivos perdidos, respuestas retrasadas 70 ms recogidas en intercambios posteriores y ausencia total de respuestas. Se comprueba el mismo puerto/socket pese a pérdidas aisladas, secuencia de requests nuevos sin retransmisiones, continuidad en pérdidas parciales y fin acotado del gesto ante blackout. No se contacta a la ESP ni se mueven motores. Pruebas de sesión V2 y joystick/enlace previas también deben pasar.

APK 0.6.0/código 12 compilado y firmado con la clave existente. La compilación no demuestra recepción Wi-Fi del móvil ni actuación física. Sin carga/actualización de firmware, sin ADB y sin órdenes físicas desde herramientas en esta corrección.

GitHub consultado sin issues abiertas; HU hardware de Trello sigue To Do. No se modifican servicios externos, commits ni push.

## Prueba del usuario

Instalar APK 0.6.0 como actualización; no flashear ESP. Primero con fuente de motores apagada, conectar/armar y mantener joystick: comprobar que ACK pendiente transitorio desaparece al recibirse otra confirmación, sin deshabilitación inmediata. Soltar sigue parando. Si el enlace queda sin confirmaciones, debe pedir nuevo rearme. No provocar pérdida de red con robot apoyado en el suelo para validar esta corrección.

Después, ensayo manual supervisado con ruedas elevadas y corte accesible. Registrar si reaparece error y texto exacto. El informe de enlace y control-enlace.log conservan diagnóstico. No considerar ausencia de calor percibido como sustituto de medición térmica/corriente.

## Reproducción de la regresión nueva

Desde raíz, salida temporal fuera de Git:

```sh
javac -encoding UTF-8 -d CARPETA_TEMPORAL software/panel_movil/android/DriveAckWindow.java software/panel_movil/android/DatagramRoundTrip.java pruebas/software/android/DriveAckWindowTest.java
java -cp CARPETA_TEMPORAL cl.lumi.panel.DriveAckWindowTest
```

Requiere UDP loopback permitido por el entorno de pruebas. Nunca arma ni envía paquetes al robot.


Resultado de entrega: regresiones de DriveAckWindowTest, JoystickLinkTest y MotorSessionTokenTest correctas. APK 0.6.0 firmado, SHA256 1F4A2274B4CEA131C9172B2506441A42A0BEC6AA38257B56EA39EA71C7A2A750. Inspección del diff de fuentes previa a integrar confirma cambios limitados al transporte/gesto/versionado, sin sobrescribir otras modificaciones del usuario. Sin verificación visual de Android ni ensayo en teléfono por el agente.
