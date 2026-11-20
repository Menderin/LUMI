# Ensayo solicitado: PWM 60 %, máximo 5 segundos

Fecha: 2026-11-19. Usuario pidió ampliar 0,5→5 s y buscar drivers con mayor corriente, informando ensayos anteriores de esa duración. Cambia solo BANK_MAX_PULSE_MS de 500 a 5000. Se mantienen PWM 60 %, frecuencia 1 kHz, canal A OUT1–OUT2, canal B a cero, tickets, rearme, watchdog 250 ms desde recepción válida y bloqueo de inversión directa.

Cinco segundos es el máximo de un gesto con órdenes renovadas, desde la primera orden válida de movimiento: soltar/cancelar sigue parando antes; no inicia una secuencia autónoma de cinco segundos. Al agotar pulso, desarma; soltar y rearmar para otro intento. App 0.5.2 publica el valor del firmware sin reinstalar. La ventana inicial de 5 s después de habilitar es un temporizador distinto del máximo de movimiento.

## Condiciones y riesgo conocido

Dos motores en paralelo por canal A, fuente Pro’sKit TE-5305 declarada a 12 V/CV, limitación aún sin verificar. Usuario informó funcionamiento y pico indicado de 4 A durante perfil anterior. No se midió corriente de bobinas, duración del pico ni temperatura. El usuario pidió expresamente continuar; esta implementación no valida L298 para esa corriente ni operación continua. Fuente apagada/ESP USB confirmado antes de carga. El agente no mandó órdenes de motores.

Durante ensayo manual: ruedas elevadas, sin carga y corte accesible; observar corriente durante giro frente al pico de arranque y calentamiento. Cortar si permanece una lectura elevada, se calienta, se limita la fuente o se reinicia. El watchdog no es protección de sobrecorriente. Antes de integración física continua, dimensionar driver/fuente/protecciones para la pareja real.

## Verificación observada

Compilación wifi_banco correcta, 861741 bytes de aplicación. Flash con hashes verificados; la reenumeración USB tras reset ocasionó aviso de puerto desaparecido de esptool. Cuatro estados USB posteriores con uptime creciente: pwm_limit=60, max_pulse_ms=5000, selftest=true, http_test=true (12 GET), udp_ready=true, udp_test=true, armed=false, pwm=0, epoch=1 y seq=0. Autopruebas de control en memoria incluyen renovación hasta el límite de cinco segundos y parada al alcanzarlo, además de caducidad, sesión/rearme, inversión, token y valor inválido. Red de arranque: GET/PING sin movimiento.

Logs locales datos/procesados/base-wifi/2026-11-19/pwm60-5s/. GitHub sin issues abiertas; HU hardware Trello sigue To Do. Sin commit/push ni cambios externos. Movimiento físico del nuevo perfil sigue pendiente de reporte del usuario.

## Comparación de reemplazos

Ver [drivers de mayor corriente](../../hardware/drivers-mayor-corriente.md). Candidatos documentados MDD10A (10 A/canal), MDD20A (20 A/canal y limitación activa/temperatura) y Pololu Dual VNH5019 (hasta 12 A/canal, lectura analógica de corriente). Todos son duales y compatibles con señales 3,3 V según fabricante. Preselección MDD20A por margen/protecciones, condicionada a mediciones y presupuesto; no se compra ni se cambia cableado/firmware de interfaz en esta tarea. No asumir 43 A continuos en módulo genérico IBT-2 solo por publicidad del BTS7960.
