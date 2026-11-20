# Recuperación del canal de datos y frescura de tokens — Android 0.6.1

Fecha: 2026-11-19. Corrección solicitada explícitamente: recuperar comunicación tras pérdida de conexión sin cerrar el canal de datos. No cambia firmware ni se habilita canal B/cuatro motores.

## Fallos identificados

App 0.6.0 aún cerraba el socket al terminar la ventana de ACK o recibir NACK, aunque un rechazo de control no implica un socket roto. Además, MotorBankSession ignoraba el tiempo original del envío y MotorSessionToken contaba frescura desde recibir la respuesta. Un ACK retrasado podía aportar un ticket ya antiguo y ser tratado como nuevo; ESP rechazaba token_vencido y luego rearme_antiguo. El intervalo entre órdenes (por ejemplo 2 ms) no mide edad del ticket ni RTT.

## Canal persistente y recuperación

PersistentDatagramEndpoint separa la vida del socket del resultado del mando. Timeout, silencio de confirmaciones y NACK suspenden el permiso de movimiento, pero conservan socket/puerto de la red actual. Un SocketException real o un cambio de Network Android recrea y enlaza el endpoint automáticamente. La aplicación no puede conservar un socket utilizable de una interfaz destruida; lo recupera sin obligar a reiniciar la app. Al cerrar la Activity se liberan recursos.

Se mantiene el sondeo HTTP de estado. Después de fallo, al recuperar estado la app realiza PING UDP (sin habilitación) con reintento espaciado al menos 750 ms mientras está visible. No cambia ajustes Wi-Fi ni obliga a Android a asociarse a un AP: cuando el usuario/sistema vuelve a LUMI-BANCO, recupera la ruta local, sin desviar paquetes a datos móviles. Primero valida estado y canal; si encuentra la ESP armada sin permiso local, solicita parada y sincroniza el ACK. Entonces muestra canal de datos disponible y permite que el usuario pulse Habilitar. No rearma ni repite gestos automáticamente.

Los rechazos incluyen su estado estructurado y se incorporan a la sesión inmediatamente; el ACK de parada también actualiza epoch/seq. El mando local se invalida antes de intentar la parada, para impedir que se sigan encolando renovaciones durante recuperación. La UI distingue mando suspendido de estado remoto desconocido y ofrece reintentos automáticos de datos. Solo la respuesta a una habilitación explícita puede dar permiso de movimiento.

## Tokens y ACK retrasados

DriveAckWindow conserva el instante original de envío de cada request admitido, además del RTT. MotorDatagrams adjunta ese instante como metadato local de respuesta (no se envía al robot). MotorSessionToken usa:

edad superior del ticket = RTT completo + tiempo local desde recepción.

La ESP emite el ticket entre envío y recepción, por lo que el RTT es una cota conservadora de su edad inicial. No se estima ni convierte el reloj ESP. Movimiento exige cota menor de 200 ms: reserva exploratoria de 50 ms frente al límite de 250 ms del firmware. Habilitar usa presupuesto distinto de 900 ms frente al límite ESP de 1000 ms. El margen no garantiza que el próximo envío tarde menos de 50 ms; la ESP conserva la comprobación final y puede parar si la red no cumple.

Cuando hace falta refrescar durante un gesto, se envía un PING de solo lectura con la misma ventana corta (hasta 45 ms), bajo nombre interno refrescar. En red sigue siendo action=ping: firmware V2 no necesita actualizarse. Conserva seguimiento acotado de solicitudes recientes; puede recoger un ACK anterior y sincronizar su estado/tiempo real. Si no hay ticket con margen, no envía una orden de movimiento con token viejo. Mientras espera se muestra estado fresco pendiente. Si la ESP se detuvo o cambió de epoch/boot, suspende y requiere habilitación manual. No utiliza un ping bloqueante de 600 ms dentro del gesto activo.

Se conservan hasta cuatro esperas fallidas o 200 ms sin confirmación, solicitudes nuevas sin retransmitir movimiento viejo y el máximo de 5 s. Una respuesta tardía no revive la ventana agotada. Ping inicial/rearme pueden esperar 600 ms; parada conserva 180 ms. Firmware sigue PWM 60 %, 1 kHz, máximo 5 s, watchdog 250 ms desde última recepción válida y canal B apagado. No se amplía vigencia de tickets en la ESP.

## Pruebas observadas

- PersistentDatagramEndpointTest: UDP loopback real, pérdida de respuesta y recuperación con el mismo socket/puerto; un NACK representado por error de protocolo y suspensión no cierran endpoint; cambio de ruta y socket roto recrean; tras fallo de bind puede recuperarse. Esta prueba usa el helper real de ciclo de vida del socket, sin Android ni ESP.
- MotorSessionTokenTest: reproduce ticket recibido tras 180 ms de tránsito y utilizado 30 ms después; ahora bloquea por falta de margen y acepta el ticket nuevo de una consulta rápida. Comprueba preservación de secuencia, epoch, reinicio, respuesta vieja, wrap de uptime, caché vacía, RTT inválido y presupuesto distinto de habilitación.
- DriveAckWindowTest: pérdida de uno/dos ACK, respuestas tardías, captura del instante original de envío, mismo puerto, requests nuevos sin retransmisión, blackout acotado y ausencia de reactivación por ACK viejo.
- JoystickLinkTest: geometría/entrada inválida y diagnóstico de enlace previos, correlación de respuestas y transporte UDP original.
- APK 0.6.1/código 13 compilado y firmado con clave existente; SHA256 CD2467F978E7852DC721910FE993720BF6CC25C828211DBD1736A6FF641D0FB3.

Las pruebas pasan en Windows con loopback habilitado. No se ejecutó Android en móvil/emulador por el agente, ni roaming Android real, ni comandos al robot. La compilación y los helpers no prueban todos los tiempos del teléfono. Prueba final de campo pendiente.

## Prueba solicitada al usuario

Actualizar APK a 0.6.1; no cargar firmware. Primero con fuente de motores apagada: conectar ESP y verificar canal disponible. Desconectar Wi-Fi y volver a LUMI-BANCO manteniendo la app abierta. Debe mostrar recuperación, obtener estado/canal y volver a permitir Habilitar, sin pulsar Conectar otra vez ni reiniciar aplicación. Debe seguir sin permiso de movimiento hasta esa pulsación y un gesto nuevo. Probar también pérdida durante gesto lógico con fuente apagada: no reanudarlo al reconectar. Registrar mensajes si continúa fallando.

## Reproducción de pruebas nuevas

Desde la raíz, salida temporal fuera de Git:

```sh
javac -encoding UTF-8 -d CARPETA_TEMPORAL software/panel_movil/android/PersistentDatagramEndpoint.java software/panel_movil/android/DatagramRoundTrip.java pruebas/software/android/PersistentDatagramEndpointTest.java
java -cp CARPETA_TEMPORAL cl.lumi.panel.PersistentDatagramEndpointTest
javac -encoding UTF-8 -d CARPETA_TEMPORAL software/panel_movil/android/MotorSessionToken.java pruebas/software/android/MotorSessionTokenTest.java
java -cp CARPETA_TEMPORAL cl.lumi.panel.MotorSessionTokenTest
```

Fuentes de contexto: GitHub sin issues abiertas y HU hardware de Trello en To Do al consultar. Sin modificación de servicios externos ni commit/push. La documentación anterior de error pendiente queda superada por esta implementación, pero la validación en móvil sigue pendiente.
