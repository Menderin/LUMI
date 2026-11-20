# Banco Wi-Fi temporal para dos motores en OUT1–OUT2

Este modo conecta Android directamente a la ESP32-S3 para laboratorio. El sistema final conserva Raspberry con ROS 2 y USB hacia la ESP. En este modo no hay cámara, IA, enrolamiento ni mando del canal B.

## App vigente: 0.7.0 con firmware protocolo 3

Instalar el APK 0.7.0 y usar firmware V3. Ver [contrato y pruebas](../../docs/trabajo/banco-protocolo-v3.md).

## Historial: app 0.6.1, recuperación del canal de datos

Instalar APK nuevo; firmware no cambia. Endpoint se conserva ante timeout/NACK y se vuelve a enlazar si cambia la red o falla el socket. Reconectar datos no rearma motores. Corrección de frescura de tokens con RTT original y PING de refresco. [Guía de verificación](../../docs/trabajo/recuperacion-canal-datos.md).

## Historial app 0.6.0: tolerancia acotada de ACK

Instalar APK 0.6.0 para esta corrección; no requiere cambiar firmware. Durante el mando, una espera sin ACK no cierra socket ni manda parada inmediata. Envía órdenes nuevas, acepta ACK recientes y detiene tras cuatro esperas fallidas o 200 ms sin confirmación. Los rechazos explícitos siguen deteniendo; no hay rearme automático. [Contrato y pruebas](../../docs/trabajo/tolerancia-ack-udp.md).

## Perfil vigente: PWM 60 %, máximo 5 s

Última petición: máximo 5000 ms mientras se mantiene el mando y llegan órdenes válidas. Soltar/cancelar, watchdog y rearme se conservan; no son cinco segundos de movimiento autónomo. Fuente apagada confirmada para carga; arranque con autopruebas correctas y PWM cero. [Ensayo y límites](../../docs/trabajo/ensayo-pwm60-5s.md). [Drivers candidatos](../drivers-mayor-corriente.md).

## Historial: PWM 60 %, corte a 500 ms

Actualización solicitada expresamente por usuario: [perfil 60 % y evidencia](../../docs/trabajo/ensayo-pwm60.md). Fuente Pro’sKit TE-5305 a 12 V, limitación aún sin verificar. No hay validación eléctrica ni prueba de movimiento por el agente. App 0.5.2 muestra límites recibidos sin actualización adicional.

## Historial: PWM 20 %, corte a 500 ms

Usuario solicita ensayo con dos motores OUT1–OUT2. Se cambió el perfil de 15 %/2 s a 20 %/0,5 s; no es una aprobación de capacidad eléctrica del L298. Fuente declarada 12 V/CV y límite no verificado. [Condiciones, cambios y evidencia](../../docs/trabajo/ensayo-pwm20.md). Firmware cargado y arranque sin movimiento verificado. App 0.5.2 muestra límites publicados; 0.5.1 es compatible, pero su texto 2 s quedó histórico.

## App de banco, firmware protocolo 2

Actualizar firmware y APK juntos. Control del banco por UDP 8082 con ACK y tickets emitidos por la ESP; HTTP 8080 permanece para consulta. Se elimina la estimación Android del reloj ESP. Ver [contrato, pruebas y límites temporales](../../docs/trabajo/banco-protocolo-v2.md). Los apartados 0.4.x inferiores son historial de correcciones que no resolvieron el fallo.

Antes del mando, ejecutar en la app **Probar enlace · sin motores**. La lectura USB confirma recepción parcial, no enlace estable. Ver [revisión del joystick y ACK](../../docs/trabajo/diagnostico-joystick-enlace.md). No hace falta volver a cargar firmware para pasar de app 0.5.0 a 0.5.1.

## Conexión

- Red WPA2: **LUMI-BANCO**. Contraseña de laboratorio: **LumiMotores26**. Se admite un teléfono.
- Servidor local: **http://192.168.4.1:8080**. La red no proporciona Internet; Android debe permanecer conectado.
- Instalar la versión 0.5.1 de `LUMI-Banco.apk`, firmada con la misma clave de desarrollo que versiones anteriores. Se instala como actualización.
- En la app: Elegir Wi-Fi → LUMI-BANCO → Conectar ESP · motores → Control manual → Habilitar canal A (5 s).
- Desplazar el joystick hacia arriba/abajo. Los movimientos laterales no se permiten con este cableado. Soltar detiene y deshabilita. Para otro ensayo, habilitar de nuevo. Tras detenerse por límite o fallo, soltar el dedo antes de rearmar.

El PWM fijo es 60%, los pulsos duran como máximo 5 s y el watchdog vence a los 250 ms desde la última orden válida recibida. La espera inicial de rearme es de 5 s. No hay velocidad ni corriente medidas. El PWM no limita la corriente de arranque ni garantiza que el L298N soporte los motores. No elevar la fuente a 5 A ni aumentar PWM para superar una rueda que no arranca sin revisar el dimensionamiento.

## Cableado y procedimiento

GPIO4→IN1, GPIO5→IN2, GPIO6→ENA, masa común. Jumper ENA a 5 V retirado y resistencia 10 kΩ de ENA a GND. Dos motores en paralelo entre OUT1/OUT2 respetando los sentidos comprobados. No aplicar potencia por protoboard o cables Dupont. Ver [circuito](banco-esp-l298n.md) para alimentación lógica de 5 V/JP1, todavía por verificar físicamente.

Durante carga y prueba inicial, fuente de motores apagada. Comprobar conexión y estado deshabilitado antes de alimentar potencia. El usuario realizará los ensayos con ruedas elevadas, fuente limitada y corte accesible, vigilando corriente y temperatura. El ensayo previo directo con fuente no valida la capacidad del driver. La herramienta del agente no manda consignas de movimiento real.

## Firmware

En `firmware/controlador`:

```sh
pio run -e wifi_banco
pio run -e wifi_banco -t upload --upload-port PUERTO
```

`wifi_banco` habilita actuación únicamente tras rearme explícito y orden vigente. Arranca a cero y mantiene GPIO7/15/16 a cero. `wifi_banco_seco` conserva la misma red/API con PWM bloqueado para pruebas de protocolo. `banco` conserva el banco serie L1 anterior sin Wi-Fi y con potencia bloqueada. No mezclar transportes de órdenes simultáneamente.

El servidor devuelve `modo=motores_esp`, `camara=false` y estado de canal A, habilitación, boot, epoch, seq, uptime, PWM ordenado/aplicado y motivo de parada. PWM aplicado es consigna interna, no medición del pin ni de movimiento.

API vigente: GET `/api/estado`; UDP 8082 con acciones ping/habilitar/adelante/atras/parar y respuesta correlacionada por request. Las tres acciones activas requieren boot, epoch, seq y ticket. Edad del ticket: menos de 1000 ms para habilitar y menos de 250 ms para mover. Cada orden válida de movimiento renueva 250 ms desde recepción; no es un límite de 250 ms desde generación en el móvil. Parada invalida epoch incluso desarmado. POST HTTP equivalente conserva contrato V2 con ticket, no deadline, para diagnóstico. El lazo de motores es independiente de red. Ver el contrato enlazado para latencia acumulada y límites.

No exponer este servidor fuera de la red de laboratorio. La contraseña es de demostración, no una credencial privada. Se identifica al dispositivo por la sesión de arranque; no se implementa autenticación de usuarios ni control multioperador.

## Comprobaciones

La máquina de estados ejecuta autopruebas C++ sin GPIO en cada arranque: rearme, rechazo sin habilitación, caducidad, sesión vieja, inversión y límite de pulso. Si fallan, no se inicia el banco. El USB publica `SELFTEST_PASS` y `LUMI_WIFI_AP_READY` al estar listo. Esto no equivale a verificar conexión de la app, niveles eléctricos ni parada física.

Después de cargar, confirmar por USB que arranca desarmado y a PWM cero. Comprobar API en seco antes de autorizar ensayos físicos. Registrar pruebas reales y sus condiciones en [registro de trabajo](../../docs/trabajo/banco-wifi-motores.md).

Historial de primera entrega del 2026-11-19: firmware compilado y cargado; arranque verificado por USB con autopruebas y red listas, desarmado y PWM cero. APK 0.4 firmado. Conexión y UX en teléfono, prueba de API por Wi-Fi y ensayos físicos pendientes. Ver registro de trabajo.

## Diagnóstico desde versión 0.4.2

Los ACK de habilitación/movimiento incluyen la misma instantánea de estado que GET, permitiendo actualizar epoch/seq sin esperar al siguiente sondeo. La app descarta GET antiguos frente a ACK nuevos y estima tránsito usando RTT/2. Un RTT de 250 ms o más impide emitir órdenes. No se ampliaron vigencias ni se aumentó PWM.

La causa de parada se conserva aunque llegue después una orden de una generación vieja. ultimo_rechazo distingue rearme_antiguo, secuencia_repetida, reinicio_o_dispositivo y orden_vencida. El USB expone epoch, seq, gap_ms y rechazo. Estas medidas ayudan al diagnóstico, no garantizan rendimiento de Wi-Fi ni reemplazan pruebas físicas.

Regresión de sesión Java, desde raíz, indicando una carpeta temporal de salida fuera de Git:

```sh
javac -d CARPETA_TEMPORAL software/panel_movil/android/MotorSessionClock.java pruebas/software/android/MotorSessionClockTest.java
java -cp CARPETA_TEMPORAL cl.lumi.panel.MotorSessionClockTest
```

## Actualización 0.4.4

HTTP 409 significa que el comando llegó y fue rechazado; leer fallo/ultimo_rechazo. Se observó caducidad seguida de rearme_antiguo. Se habilitó TCP_NODELAY en conexiones del servidor y renovación Android a 50 ms, sin ampliar la vigencia de 250 ms ni aumentar PWM. La app muestra el detalle de rechazo y el último intervalo. Es necesario volver a comprobar en teléfono y luego en hardware; las autopruebas y lecturas de estado no validan movimiento estable.
