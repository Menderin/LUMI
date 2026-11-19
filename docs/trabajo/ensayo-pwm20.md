# Ensayo de arranque: PWM 20 %, corte a 500 ms

Fecha: 2026-11-19. Perfil de banco para canal A; no cambia arquitectura ROS/USB ni protocolo V2.

## Datos aportados y alcance

Usuario: dos motores en paralelo OUT1–OUT2, solo pitido, indicador de fuente 0,5 A. Fuente a 12 V en tensión constante; cree que el límite supera 4 A, pero después aclara que la fuente no muestra el máximo ajustado. No hay límite de corriente verificado ni medida de picos de bobinado. La opinión del profesor de haber usado este driver no certifica margen con esta pareja y montaje.

Se propuso primero un motor y límite exploratorio de 1 A. El usuario pidió mantener ambos; no se aplicó ni se confirmó ese ajuste de 1 A. Se conserva la pareja para el ensayo solicitado, con incremento limitado 15→20 % y reducción del máximo de pulso 2000→500 ms. El usuario confirmó la fuente apagada antes de cargar. No se enviarán órdenes físicas desde herramientas.

La ficha oficial [ST L298](https://www.st.com/resource/en/datasheet/l298.pdf), tabla 1, especifica 2 A en continua por canal como máximo absoluto del integrado, no corriente de servicio garantizada del módulo. La disipación y la corriente conjunta siguen sin caracterizar. La indicación de fuente bajo PWM no determina los picos por motor; el 20 % no es un limitador de corriente. No se aprobó el L298 para carga, cuatro motores ni operación prolongada.

## Implementación

Una única constante BANK_PWM_PERCENT=20 define la consigna (+/-200 en escala por mil), el filtro de órdenes y el límite publicado. BANK_MAX_PULSE_MS=500 fija corte aunque se mantenga el joystick o sigan llegando renovaciones. Telemetría USB publica pwm_limit y max_pulse_ms; HTTP/UDP publican limite_pwm y max_pulso_ms.

Sin impulso de arranque al 100 %, rampas nuevas ni ajuste remoto de potencia. Frecuencia 1 kHz, tickets de movimiento menores de 250 ms, watchdog de 250 ms desde recepción válida, rearme inicial de 5 s, parada al soltar e inversión bloqueada se conservan. Canal B queda a cero.

App 0.5.2/código 11 solo actualiza la presentación del perfil: lee PWM máximo y duración de la ESP, en vez de mostrar 2 s fijos. La 0.5.1 conserva compatibilidad de órdenes con firmware V2, pero muestra texto histórico de 2 s; el corte real lo impone firmware a los 500 ms. La app no modifica esos límites.

## Verificación y prueba pendiente

Compilación de firmware y APK correcta; firma APK verificada con clave existente. Autopruebas C++ en memoria cubren ambos intervalos de renovación (105/151 ms), caducidad, conservación del fallo inicial, rearme, secuencia repetida, inversión, ticket vencido, wrap de reloj, rechazo de consignas fuera del valor permitido y corte del pulso. Pruebas HTTP/UDP al arrancar son GET/PING solamente.

Tras carga, comprobar USB con selftest/udp_test/http_test correctos, pwm_limit=20, max_pulse_ms=500, desarmado y PWM cero. Evidencia local en datos/procesados/base-wifi/2026-11-19/pwm20-500ms/.

Ensayo del usuario: ruedas elevadas, sin carga y corte accesible. Conectar app, alimentar potencia, habilitar y realizar un único pulso; firmware corta como máximo a 0,5 s. Soltar y revisar corriente, tensión y temperatura antes de repetir. Si continúa pitido sin giro, aparece limitación de fuente, calentamiento o reinicio, cortar alimentación y revisar alimentación/corriente/cableado; no aumentar automáticamente PWM ni la corriente disponible. La reducción de duración limita exposición, pero no garantiza protección del driver ni frenado mecánico.

No afirmar giro, velocidad, par suficiente, corriente segura o parada física por el hecho de compilar/cargar firmware. Registrar el resultado físico cuando el usuario lo comunique.


Verificación observada después de cargar: cuatro estados USB con uptime creciente, selftest=true, http_test=true (12 GET), udp_ready=true, udp_test=true, pwm_limit=20, max_pulse_ms=500, armed=false, pwm=0, epoch=1, seq=0 y fallo inicio. Escritura con hashes verificados; reinicio reenumeró USB. Sin órdenes de motores desde herramientas. SHA256 APK 0.5.2: CBEFA32A6DD30182EB6614F80B57483A6F12477C7A8347E1C7621AA59D0B6188.
