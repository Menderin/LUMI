# Diagnóstico de joystick y enlace Android 0.5.1

Fecha: 2026-11-19. Corrección del banco temporal, sin cambiar arquitectura ROS/USB ni firmware V2.

## Resultado solicitado y evidencia inicial

El usuario reportó tiempo de espera agotado al mantener adelante en app 0.5.0 y pidió revisar cómo se toma el joystick. GitHub consultado: sin issues abiertas; HU de hardware en Trello continúa To Do, sin validación física cerrada. No se modificaron servicios externos.

Lectura USB pasiva: protocol=2, udp_ready=true, udp_test=true, phone_connected=true, epoch=14, seq=49, gap_ms=260, fault=caducidad, rejection=rearme_antiguo, armed=false, pwm=0. Hay órdenes que llegan a ESP; esta evidencia no demuestra continuidad correcta del gesto ni permite atribuir toda la latencia al enlace. El contador 49 es secuencia de órdenes activas, no cantidad exacta de movimientos.

## Hallazgos y correcciones

- La app abortaba un intercambio UDP tras 100 ms y convertía la excepción en Tiempo de espera agotado, ocultando si faltaba ACK de ping, habilitación o movimiento. Prueba real con sockets de loopback reproduce: ACK retrasado 140 ms vence con timeout 100 y es recibido con 180. Esto demuestra la fragilidad del límite, no que todos los fallos del móvil tengan esa misma causa.
- Espera de ACK Android: 180 ms para movimiento/parada y 600 ms para ping/habilitar. Es una espera de recepción, no una ampliación del watchdog. Se mantienen 250 ms desde recepción válida en firmware, ticket de movimiento menor de 250 ms, PWM 15%, 1 kHz, pulso máximo 2 s y rearme explícito. Mayor espera puede dejar poco margen para renovar; si la red sigue irregular, se debe parar y medir, no seguir relajando límites.
- Se solicita WifiLock de baja latencia en Android 10/API 29 o superior; en API 23–28 se solicita alto rendimiento. Solo se mantiene con la app en primer plano y conexión configurada hacia ESP; se libera al pausar. Se mantiene la pantalla encendida durante control ESP. Permisos normales ACCESS_WIFI_STATE y WAKE_LOCK, sin diálogo de ubicación ni cambios en ajustes del sistema. El dispositivo puede no ofrecer la mejora: se informa solicitada, no garantizada.
- El ahorro energético del Wi-Fi del teléfono es una hipótesis compatible con retardos, aún sin medición en el teléfono. [Referencia Android](https://developer.android.com/reference/android/net/wifi/WifiManager#WIFI_MODE_FULL_LOW_LATENCY) y [WifiLock](https://developer.android.com/reference/android/net/wifi/WifiManager.WifiLock). Las pruebas internas ESP por loopback no recorren la radio del móvil.
- JoystickDirection separa geometría de transporte. Zona central: 25% del radio; arriba=adelante, abajo=atrás, dominante horizontal=izquierda/derecha (sin actuación lateral en canal A). Se conserva el dibujo sin conexión. Se muestra Gesto de manera independiente del permiso y el último TX/ACK por separado. Si desaparece el puntero activo, ahora centra y para en lugar de mantener el gesto anterior. Soltar/cancelar, cambio de sentido y límites mantienen parada/rearme.
- DatagramRoundTrip es transporte Java comprobable sin Android. Usa solo el peer conectado, correlaciona request, descarta ACK de otras solicitudes y no retransmite movimiento. Mantiene un intercambio en vuelo. Error muestra acción, número de solicitud y plazo: Sin ACK UDP de adelante #N en 180 ms, por ejemplo. HTTP de estado identifica su propio timeout de 2 s.

## Prueba de enlace sin motores

En app 0.5.1: Conectar ESP → Probar enlace · sin motores. Primero manda parada, bloquea habilitación/joystick durante la medición y comprueba deshabilitado en cada respuesta. Ejecuta 12 PING de solo lectura separados al menos por el tiempo restante hasta 50 ms. Nunca arma ni solicita movimiento. Si una respuesta indica habilitado, aborta.

Informa respuestas, pérdidas, RTT p50/p95/máximo e intervalo máximo de recepción en ESP (diferencia entre uptimes, sin convertir relojes). Umbral inicial de diagnóstico: 12/12 respuestas, p95 menor de 120 ms y separación máxima menor de 200 ms. Es un filtro de ensayo para dejar margen frente a watchdog 250 ms; no certifica movimiento, parada física o corriente. Copiar informe permite pegar el resultado en el chat.

La app guarda prueba-enlace.txt y control-enlace.log en almacenamiento privado local. El log conserva las últimas 128 entradas TX/ACK/error en memoria, volcadas tras fallo, prueba y pausa; no hace escritura por cada orden. Son diagnósticos técnicos sin imágenes. No se suben automáticamente ni requieren ADB para copiar el resumen de prueba.

## Verificación y límites

- Regresión Java: dirección, zona muerta, valores inválidos, prueba de enlace estable/lenta/con pérdida; sockets UDP reales con ACK 140 ms y ventanas 100/180 ms; ACK ajeno seguido del correcto; exactamente un datagrama enviado, sin retransmisiones. Ejecutada en Windows con loopback permitido. Primer intento dentro del aislamiento no recibió UDP; la misma prueba fuera del aislamiento pasó. No confundir esta restricción del PC con la red del teléfono.
- Regresión de tokens V2 sigue pasando: orden temporal, secuencia, epoch, reinicio, estado viejo, limpieza y wrap de uptime.
- APK 0.5.1/código 10 compilado y firmado con la misma clave. No se usa ADB, no se flashea firmware, no se envían consignas físicas. No hay inspección visual/emulador ni prueba del Android real por el agente.
- Pendiente: usuario instala APK, deja fuente apagada, ejecuta la prueba de enlace y copia el informe. Comprobar también que Gesto cambia al mover el dedo sin necesidad de habilitar. Solo después revisar control con fuente apagada; actuación y parada física siguen pendientes.

## Pruebas reproducibles

Desde raíz, sustituyendo CARPETA_TEMPORAL por salida local fuera de Git:

```sh
javac -encoding UTF-8 -d CARPETA_TEMPORAL software/panel_movil/android/JoystickDirection.java software/panel_movil/android/LinkProbeStats.java software/panel_movil/android/DatagramRoundTrip.java pruebas/software/android/JoystickLinkTest.java
java -cp CARPETA_TEMPORAL cl.lumi.panel.JoystickLinkTest
```

La regresión necesita UDP en loopback habilitado por el entorno de ejecución. No contacta al robot. La fuente de verdad de límites ESP sigue siendo [protocolo V2](banco-protocolo-v2.md); los 100 ms de espera de app del documento original son historial reemplazado por esta corrección.
