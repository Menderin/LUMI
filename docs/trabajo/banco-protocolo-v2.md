# Corrección del control de banco 0.5.0 (protocolo 2)

Fecha: 2026-11-19. Solo banco Android → ESP; la arquitectura final Raspberry/ROS 2 → USB → ESP no cambia.

## Perfil físico vigente: PWM 20 % y corte a 500 ms

Perfil de ensayo solicitado después de pitido sin giro a 15 %. Firmware cargado y arranque verificado; no hay movimiento físico comprobado por el agente. Consultar [ensayo y limitaciones eléctricas](ensayo-pwm20.md). App 0.5.2 lee estos límites; 0.5.1 conserva compatibilidad de protocolo. Las cifras 15 %/2 s inferiores describen el perfil previo.

## Diagnóstico de app desde 0.5.1

El usuario volvió a reportar timeout con 0.5.0. Firmware V2 se mantiene. La app solicita baja latencia Wi-Fi, identifica gesto y ACK por separado y agrega prueba de enlace sin motores. Espera de ACK: 180 ms en movimiento/parada y 600 ms en ping/rearme; los 100 ms del diseño original inferior son historial. No cambian watchdog, PWM ni pulso. Leer [diagnóstico y comprobaciones](diagnostico-joystick-enlace.md) antes de reintentar el mando.

## Motivo

El usuario volvió a observar HTTP 409, caducidad y rearme_antiguo incluso con intervalo 105 ms. Lectura USB previa: caducidad, epoch 9, seq 33, gap 252 ms, PWM cero. Las correcciones 0.4.2–0.4.4 no resolvieron el síntoma. El último intervalo entre recepciones no es la edad de una orden ni mide toda la cadena. La estimación Android del reloj ESP dejaba una ventana frágil; HTTP compartía consultas y control. No se atribuye a insuficiente potencia un rechazo de protocolo.

## Contrato vigente

- HTTP 8080 conserva GET /api/estado para diagnóstico. Publica banco.protocolo_control=2 y banco.ticket.
- La app 0.5.0 usa UDP 8082 para el banco. Envía JSON con action y request (uint32). Acciones ping, habilitar, adelante, atras, parar. Cada respuesta confirma request, ok y una instantánea banco. Ping no habilita ni renueva el watchdog.
- Habilitar/adelante/atras requieren boot, epoch, seq y ticket. La ESP emite y conserva 16 tickets recientes; comprueba su edad usando exclusivamente su reloj. Habilitar admite ticket de menos de 1000 ms; movimiento exige menos de 250 ms. No son credenciales de autenticación.
- Android obtiene un ticket fresco por ping antes de habilitar y cuando la instantánea tiene 100 ms o más. Usa los tickets de los ACK posteriores. No calcula deadline ni convierte relojes. Descarta estados HTTP anteriores a un ACK.
- Un intercambio UDP en vuelo, request correlacionado, espera máxima local de 100 ms tras enviar y sin retransmisión de movimiento. La cadencia nominal del mando sigue siendo 50 ms, sujeta a planificación/red. Ante error, la app intenta parar y bloquea el gesto; no rearma automáticamente.
- Watchdog: **250 ms desde la recepción de la última orden válida**. Cambia la semántica V1 de deadline absoluto estimado. Un datagrama con ticket todavía vigente puede llegar retrasado y renovar por otros 250 ms: no prometer parada a 250 ms desde que Android generó el gesto. La edad admisible del ticket y el watchdog pueden sumar casi 500 ms desde su emisión, más la planificación del lazo de salida (nominal 5 ms). La parada de la app se intenta inmediatamente al soltar. Medir parada física por separado.
- Se conservan PWM fijo 15%, 1 kHz, máximo 2 s por pulso, 5 s de espera inicial, bloqueo de inversión directa y canal B apagado. El control revisa caducidad fuera de tareas de red. Parar invalida epoch incluso si ya estaba desarmado; desconectar Wi-Fi también. Un mensaje viejo no puede rearmar tras esa parada.
- POST HTTP se conserva para diagnóstico con contrato V2 (ticket, no deadline); la app nueva no lo usa para los motores. **Actualizar firmware y APK juntos**. Versiones 0.4.x no son compatibles con el contrato nuevo.

## Archivos y pruebas

Firmware: firmware/controlador/src/control_banco.hpp y wifi_banco.cpp. App: software/panel_movil/android/MotorSessionToken.java, MotorBankSession.java, MotorDatagrams.java, EspWifiRoute.java y MainActivity.java.

Regresión Java desde la raíz (salida temporal fuera de Git):

```sh
javac -encoding UTF-8 -d CARPETA_TEMPORAL software/panel_movil/android/MotorSessionToken.java pruebas/software/android/MotorSessionTokenTest.java
java -cp CARPETA_TEMPORAL cl.lumi.panel.MotorSessionTokenTest
```

Cubre secuencia, epoch, reinicio, respuestas antiguas, expiración de caché local, limpieza y vuelta del uptime. La clase MotorSessionClock y su prueba conservan la implementación histórica V1; no intervienen en control V2.

Autoprueba C++ en memoria antes de configurar GPIO: órdenes sin rearme, renovaciones separadas 105/151 ms, caducidad a 250 ms desde recepción, causa inicial conservada, token vencido, inversión, repetición, pulso de 2 s y vuelta del reloj. En arranque se ejecutan además 12 GET HTTP y tres PING UDP locales, nunca habilitación ni movimiento real. Estas pruebas no sustituyen la Wi-Fi del móvil ni verifican el pin o el driver.

## Prueba pendiente con el usuario

1. Con fuente de motores apagada, instalar APK 0.5.0 y reconectar LUMI-BANCO tras el reinicio. Verificar que aparece versión 0.5.0.
2. Conectar ESP, habilitar canal A y mantener el joystick arriba menos de 2 s. Debe mostrar PWM ordenado 15%, sin 409/caducidad prematura. Soltar debe deshabilitar. Para otro gesto, habilitar de nuevo.
3. Verificar atrás con nuevo rearme, límite de 2 s y pérdida de red. Registrar texto y telemetría si falla. No subir PWM ni relajar watchdog para ocultar latencia.
4. Solo después, ensayos físicos supervisados con ruedas elevadas, fuente limitada, corte accesible y revisión de consumo/driver. La generación del APK y el arranque correcto no demuestran movimiento estable.
