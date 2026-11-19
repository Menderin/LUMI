# Banco Wi-Fi de motores

Fecha: 2026-11-19. Estado: en implementación. Petición del usuario: pasar de las pruebas directas con fuente a la app, usando una red de la ESP solo durante las pruebas de motores. Se consultaron GitHub (sin issues abiertos) y la HU de hardware de Trello (To Do). No se cambiaron tarjetas.

## Especificación

- ESP32-S3 con C++/ESP-IDF, AP WPA2 `LUMI-BANCO`, un cliente, servidor HTTP local. Temporal; la integración final sigue Android → Raspberry/ROS → USB → ESP.
- Solo canal A, GPIO4/5 dirección y GPIO6 PWM; GPIO7/15/16 siempre bajos. Dos motores en paralelo comparten una orden. No probar giros de robot con este cableado.
- Imagen Android mantiene simulación/cámara anterior y añade modo real identificado por API. Oculta enrolamiento/vídeo en banco, ofrece conexión ESP, habilitación, joystick adelante/atrás y parada.
- Arranque desarmado. Rearme explícito en cero, espera de 5 s para comenzar. Órdenes con sesión, epoch, secuencia y deadline de hasta 250 ms; cliente usa 180 ms. No rearmar al reconectar ni renovar un gesto cancelado.
- PWM fijo máximo 15%, sin regulación ni medida de corriente. Pulso máximo 2 s aunque el usuario mantenga el mando. Para invertir hay que parar y rearmar. Fallo/red desconectada/caducidad invalida órdenes en cola.
- No ejecutar comandos de movimiento real desde herramientas del agente. Primera verificación lógica de la máquina de estados no accede a GPIO. Carga y comprobación de arranque requieren fuente de motores apagada.

## Riesgo eléctrico pendiente

El usuario indica pruebas previas directas con fuente de 5 A y corrientes de 1–4 A a tensión reducida, frenando la rueda. No valida el L298N bajo carga ni corriente de bloqueo a 12 V. El docente considera viable el módulo, pero faltan medidas y condiciones de esa validación. No sustituir protecciones físicas por límites de software. Pulldown 10 kΩ en ENA y jumper ENA retirado según montaje descrito por el usuario. Lógica de 5 V/JP1 debe verificarse físicamente.

## Verificación y entrega

Compilar firmware y APK firmado con la clave de actualización existente. Ejecutar autopruebas C++ de la máquina de estados sin GPIO: arranque, falta de rearme, deadline, sesión vieja, secuencia, inversión y pulso máximo. Comprobar serial de arranque tras carga: selftest correcto, desarmado y PWM cero. Probar red/API sin mandar movimiento físico; las pruebas con fuente encendida corresponden al usuario con ruedas elevadas.

Registrar aquí resultados observados y pendientes. No afirmar prueba visual en teléfono ni ensayo físico si no se realizaron. Artefactos y respaldo de firmware permanecen fuera de Git.

## Resultado observado, 2026-11-19

- Firmware wifi_banco compilado con ESP-IDF 5.5.0; flash 16 MB, sin uso de PSRAM. App 0.4 compilada y firmada usando la clave de actualización existente.
- Carga en la ESP32-S3 confirmada por hashes de esptool. El reinicio por watchdog reenumeró USB y esptool terminó con excepción de puerto desaparecido después de verificar la escritura. Se comprobó después el firmware ejecutándose, no se asumió éxito solo por la escritura.
- Lectura USB final de seis estados consecutivos con uptime creciente: selftest=true, wifi_ready=true, armed=false y pwm=0. Autopruebas C++ incluyen secuencia repetida y sesión caducada, y nunca tocan GPIO.
- Tres pruebas Python del protocolo de base anterior pasan. APK declara versión 0.4/código 4, minSdk 23. No hay dispositivo ADB conectado para verificar la interfaz en el teléfono.
- Red y HTTP preparados por firmware: LUMI-BANCO, WPA2, 192.168.4.1:8080. No se conectó el PC al AP ni se probaron peticiones del móvil en esta sesión. No se enviaron órdenes de giro desde herramientas ni se energizaron motores por el agente. Pruebas físicas, consumo, parada medida y validación en teléfono pendientes.
- Logs, hashes y resultados locales en datos/procesados/base-wifi/2026-11-19/, excluidos de Git. APK entregado desde el directorio android-build del espacio de trabajo.

## Diagnóstico y corrección Android 0.4.1, 2026-11-19

El usuario confirmó que el acceso fallaba cuando Android prefería datos móviles frente al Wi-Fi local sin Internet. Se agregó EspWifiRoute: las peticiones destinadas a 192.168.4.1 usan Network.openConnection sobre la interfaz Wi-Fi con dirección 192.168.4.x, sin requerir validación de Internet. No cambia la red del sistema ni dirige otras URLs por esa interfaz. Se añadieron permisos normales de estado/cambio de red. Además se evita enviar parada con contrato desconocido antes de identificar el servidor y se muestran HTTP/cuerpo de rechazo en lugar de un error genérico. Respuestas de conexiones anteriores no actualizan la sesión nueva.

APK versión 0.4.1/código 5 compilado y firmado con la clave anterior. Falta validación de esta corrección en el móvil. No se modificó firmware ni se enviaron órdenes de movimiento. La última lectura USB confirmó wifi_ready=true, power=true, armed=false, pwm=0: el firmware permite actuación real tras rearme, no está en modo seco.

El usuario informó después pitido sin giro y un ruido que atribuye a la ESP, incluso alimentada por USB. Pendiente aislar ESP sola de driver/motores y obtener el mensaje exacto de rechazo. No aumentar PWM ni eliminar el rearme mientras el origen del ruido y el estado eléctrico no se hayan aclarado. El PWM actual es 1 kHz/15%; un zumbido del motor no demuestra ruido de la ESP ni capacidad eléctrica suficiente.

## Corrección de sesión 0.4.2

Síntoma del usuario: aparece PWM 15%, pitido y después sesion_o_secuencia. Se encontraron defectos comprobables de sincronización: GET retrasado podía revertir epoch frente a una respuesta más nueva; la estimación del reloj omitía el tiempo de tránsito; y el firmware sobrescribía una causa de parada anterior al rechazar una orden antigua. No se capturó todavía el intercambio exacto del teléfono que originó el síntoma, por lo que no se afirma que todas las causas físicas o de latencia estén descartadas.

MotorSessionClock, Java sin Android, ahora rechaza respuestas antiguas y compensa estimativamente la mitad del RTT. Cada ACK del firmware incluye el estado para actualizar sesión inmediatamente. RTT de 250 ms o mayor bloquea el envío, sin aumentar la caducidad. Se detecta reinicio y se exige nuevo rearme. El firmware conserva la causa de parada y publica ultimo_rechazo e intervalo entre órdenes; por USB también epoch, seq y gap_ms. PWM 15%, 1 kHz, pulso 2 s y límite de vigencia 250 ms no cambiaron.

Seis escenarios de regresión Java pasan: tránsito, respuestas ACK/GET fuera de orden, reinicio, RTT excesivo, estado caducado y desconexión. Las autopruebas del firmware prueban además que una orden antigua tras caducidad no oculta la causa original. Firmware compilado/cargado y hashes verificados. Tras reenumeración USB se observaron cinco estados con uptime creciente, selftest=true, wifi_ready=true, armed=false, pwm=0, epoch=1, seq=0, rejection=ninguno. Fuente de motores apagada confirmada por usuario antes de carga. No se enviaron comandos de movimiento desde herramientas.

APK 0.4.2/código 6 compilado/firmado con clave existente. Falta reproducir el gesto en el teléfono con fuente apagada, y después validar movimiento físico si corresponde. Logs locales en datos/procesados/base-wifi/2026-11-19/sesion-0.4.2/.

## Conexión HTTP 0.4.3

Síntoma posterior a 0.4.2: tiempo de espera al conectar. Se leyó firmware activo con salidas cero. El usuario indicó después que no podía conectar a la propia red Wi-Fi. No atribuir automáticamente ese fallo de asociación Wi-Fi a la sesión de comandos.

Se identificó un riesgo de agotamiento de conexiones: máximo cuatro sockets HTTP, sin purga LRU, y selección repetida de objetos Network en Android. Se habilitó purga LRU y keepalive TCP acotado; Android conserva el objeto Network equivalente para reutilizar su pool. El tiempo de espera de conexión/lectura pasa a 2 s, sin cambiar deadline de órdenes (hasta 250 ms), PWM (15%) ni pulso (2 s). No se ha demostrado aún que este riesgo fuera la causa concreta del fallo del teléfono.

El firmware ahora ejecuta 12 GET HTTP reales a su servidor mediante loopback, valida status 200, JSON, estado deshabilitado y PWM cero. No manda ninguna orden de motor. Prueba observada correcta en ESP: http_test=true, http_requests=12, phone_connected=false, selftest=true, wifi_ready=true, uptime creciente, armed=false y pwm=0. Esta prueba valida HTTP interno, no asociación Wi-Fi externa ni la app. Se agregaron contador HTTP y presencia de estación a la telemetría USB.

Firmware compilado y cargado, escritura verificada. APK 0.4.3/código 7 compilado y firmado. Pendiente que el usuario reconecte a LUMI-BANCO y compruebe /api/estado en navegador antes de reintentar el mando. Logs locales de build/carga/arranque en datos/procesados/base-wifi/2026-11-19/http-0.4.3/.

El usuario confirmó que, tras olvidar y volver a conectar LUMI-BANCO en Android, el navegador muestra el JSON de /api/estado. Conexión Wi-Fi y lectura HTTP externa comprobadas manualmente. Queda comprobar la app 0.4.3 en el mismo enlace, inicialmente con la fuente de motores apagada. No volver a atribuir el fallo previo únicamente a la sesión: hubo también falta de asociación al AP tras reinicio.

## HTTP 409 y caducidad observada, 0.4.4

Lectura USB anterior al cambio: fault=caducidad, rejection=rearme_antiguo, epoch=20, seq=60, gap_ms=151, HTTP requests=600, phone_connected=true. Esto confirma caducidad seguida de rechazo de un rearme antiguo; no es fallo de asociación Wi-Fi ni prueba de insuficiente potencia. El intervalo es el último recibido, no una medición completa de latencia extremo a extremo.

Se verificó en ESP-IDF que las respuestas HTTP pequeñas se envían con cabecera/cuerpo separados y el socket de conexión no tenía TCP_NODELAY configurado por este proyecto. Se añadió open_fn para desactivar agrupación Nagle; si no puede aplicarse, esa conexión se cierra. Es una corrección de latencia potencial de transporte, no una prueba de que todo el jitter medido provenga de Nagle. La renovación Android pasa de 80 a 50 ms (20 Hz), conservando como máximo una petición en vuelo y descartando órdenes de gestos anteriores.

El error HTTP 409 muestra ahora la causa de parada, último rechazo e intervalo entre órdenes del JSON recibido, en lugar de ocultarlos tras Orden rechazada. PWM 15%, 1 kHz, pulso 2 s y vigencia máxima de orden 250 ms se mantienen. El timeout de conexión HTTP de 2 s no habilita una orden vencida.

APK 0.4.4/código 8 compilado y firmado. Firmware compilado/cargado con escritura verificada. Tras reenumeración USB se observaron cinco estados de arranque con selftest=true, http_test=true, HTTP requests=12, armed=false y PWM cero. No se enviaron consignas de movimiento desde herramientas. Falta verificar el gesto completo en teléfono, primero con fuente de motores apagada. No declarar resuelto el rechazo solo por compilar o por pasar las lecturas HTTP internas.

El usuario solicitó documentar todas las decisiones: se consolidaron D-13 a D-22 en docs/decisiones.md y se reconciliaron docs/instalacion.md, Agents/contexto.md y el índice AGENTS.md. La guía de vídeo queda en docs/video-ros-pi3.md. Ubuntu Server instalado es una declaración del usuario; versión exacta y arquitectura siguen sin verificación remota.


## 0.5.0: tickets ESP y control UDP

El usuario reportó nuevamente caducidad/rearme_antiguo, incluso con intervalo 105 ms. Las correcciones 0.4.2–0.4.4 no resolvieron el fallo. Lectura USB previa adicional: epoch 9, seq 33, gap 252 ms, caducidad, PWM cero. Se implementó protocolo V2: tickets emitidos/verificados por ESP, watchdog contado desde recepción válida, control UDP 8082 con ACK y consulta HTTP separada. No se subió PWM. Ver [contrato completo y prueba pendiente](banco-protocolo-v2.md).

Usuario confirmó fuente apagada, USB solamente y 5 V del driver separado antes de cargar. Firmware compilado (861393 bytes de aplicación), escrito y hashes verificados. El reinicio por watchdog reenumera USB y esptool informa dispositivo desaparecido después de verificar; arranque confirmado luego por seis estados USB con uptime creciente, protocol=2, selftest=true, udp_ready=true, udp_test=true, http_test=true, http_requests=12, armed=false, pwm=0, epoch=1 y seq=0. Pruebas de red internas: solo GET/PING, ninguna orden física de motor. Regresión Java de tokens y APK 0.5.0/código 9 compilados; firma verificada con clave existente. SHA256 APK: 558691334384D401331171A3A8B5C4B1DCAB661D438B660A46244B82B92C645C.

No declarar resuelto el gesto hasta que el usuario pruebe ambos extremos actualizados. Primero fuente apagada; movimiento, corriente y parada física siguen pendientes. Evidencia local en datos/procesados/base-wifi/2026-11-19/tokens-0.5.0/. No se hizo commit ni push.


## App 0.5.1: joystick, Wi-Fi y confirmaciones

El fallo continuó en 0.5.0. USB mostró seq 49, gap 260 ms y caducidad: hay órdenes que llegan a ESP. Se reprodujo en loopback que ACK 140 ms provoca timeout con ventana 100 ms, y que ventana 180 lo acepta. Esto identifica un defecto comprobable de la app, sin afirmar causa única del móvil. Se solicita Wi-Fi de baja latencia en primer plano, se separan gesto/TX/ACK y se incorpora prueba de 12 PING sin motores, con informe copiable. [Implementación, evidencia y pendientes](diagnostico-joystick-enlace.md).

APK 0.5.1/código 10 compilado y firmado. SHA256 6B6CCD81F087A1FA1665BA957FB4E01C02EC47C0843031C1CE191B0E9E978730. Pruebas Java de joystick/enlace y tokens correctas. No se cambió/cargó firmware, no se movió hardware ni se usó ADB. Falta el informe de Wi-Fi del móvil y validación de mando con fuente apagada. No declarar resuelto por compilar.


## Ensayo PWM 20 % / 500 ms

Usuario informó pitido sin giro con dos motores a 15 %, fuente a 12 V/CV e indicador 0,5 A; el límite ajustado no quedó verificado. Solicitó mantener ambos motores pese a recomendación de aislar uno. Se preparó ensayo breve 20 % con corte 500 ms, sin aumento automático ni eliminación del rearme/watchdog. Fuente apagada confirmada antes de carga. [Registro y límites](ensayo-pwm20.md).

Firmware compilado, cargado con hashes verificados y autopruebas correctas. USB confirmó pwm_limit=20, max_pulse_ms=500, desarmado y PWM cero en cuatro estados. Solo lectura por herramientas, sin ensayo físico de movimiento. APK 0.5.2/código 11 firmado muestra valores publicados por ESP; 0.5.1 es compatible pero conserva texto antiguo de 2 s. Evidencia local en datos/procesados/base-wifi/2026-11-19/pwm20-500ms/. Pendiente resultado del pulso por usuario.
