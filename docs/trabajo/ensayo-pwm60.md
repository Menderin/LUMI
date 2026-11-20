# Ensayo solicitado: PWM 60 %, máximo 500 ms

Fecha: 2026-11-19. Sustituye el perfil de ensayo 20 %/500 ms; protocolo V2 y arquitectura ROS/USB no cambian.

## Petición y condiciones

El usuario pidió expresamente subir a 60 % tras observar 0,7 A en la fuente con PWM 20 %. Identificó Pro’sKit TE-5305 0–30 V/0–5 A, uso a 12 V/CV; límite de corriente aún sin verificar y sin carga de prueba disponible. Tras explicar las limitaciones de corriente de L298 y la diferencia entre indicador de fuente/picos de motor, el usuario reiteró proceder, citando ensayos previos. Se mantienen los dos motores en paralelo OUT1–OUT2 para la prueba pedida. No se certificó capacidad eléctrica del módulo ni se ajustó la fuente desde software.

El usuario confirmó fuente apagada antes de cargar, en respuesta a indicación de ESP solo USB y 5 V del driver separado. El agente no envió órdenes de movimiento.

## Cambio y límites

BANK_PWM_PERCENT pasa de 20 a 60, consigna normalizada +/-600 por mil. La constante compartida actualiza validación de órdenes, GPIO y límites publicados. Se conservan máximo 500 ms por pulso, 1 kHz, watchdog 250 ms desde recepción válida, tickets, rearme explícito y bloqueo de inversión directa. Canal B queda apagado. No hay impulso automático al 100 % ni cambios en la fuente.

App 0.5.2 lee limite_pwm y max_pulso_ms del firmware y muestra el perfil actualizado, sin recompilar/reinstalar. App 0.5.1 también conserva compatibilidad de órdenes, aunque su rótulo de duración era fijo. El firmware controla el corte real.

## Evidencia observada

Build wifi_banco correcto, 861733 bytes de aplicación. Escritura y hashes verificados; al reiniciar se reenumera USB y esptool informa desaparición del dispositivo después de verificar. Cuatro estados USB posteriores, uptime creciente: pwm_limit=60, max_pulse_ms=500, selftest=true, http_test=true, http_requests=12, udp_ready=true, udp_test=true, armed=false, pwm=0, epoch=1, seq=0, fallo inicio. Pruebas de red de arranque: solo GET/PING. Autopruebas de control en memoria, sin GPIO.

GitHub consultado sin issues abiertas; HU de hardware en Trello sigue To Do. No se cambió el estado externo ni se hizo commit/push. Logs locales: datos/procesados/base-wifi/2026-11-19/pwm60-500ms/.

## Pendiente

Usuario reconecta Wi-Fi tras el reinicio y ejecuta un solo pulso con ruedas elevadas y corte accesible; después registra giro, tensión, corriente indicada, modo CV/CC y calentamiento. Cortar alimentación si continúa sin giro, calienta, hay limitación o reinicio. El tiempo acotado no es protección de corriente ni prueba de que L298 soporte la pareja. No hay movimiento físico verificado por el agente, ni métricas de velocidad/corriente por firmware.


## Resultado informado y revisión del marcado

El usuario informó después que funciona y que el pico indicado llegó a 4 A, y solicitó investigar marcado L298N CZOPBb17 VW CZ MAR. Giro es un resultado informado por el usuario; duración, temperatura y corriente de bobinas no fueron verificadas. Se revisaron producto/datasheet ST y referencias de trazabilidad: no hay evidencia de otra versión de mayor corriente; 4 A es cifra total del integrado y no por canal A. [Inventario y fuentes](../../hardware/componentes.md). Se recomienda caracterizar corriente y disipación antes de repetir. No se alteró firmware ni se enviaron órdenes físicas durante la búsqueda.
