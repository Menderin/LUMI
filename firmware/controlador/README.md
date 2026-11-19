# Base ESP32-S3 de LUMI

Primer banco C++ con ESP-IDF 5.5 mediante PlatformIO espressif32 6.12.0. Hardware identificado por esptool: ESP32-S3 rev. 0.2, flash 16 MB y PSRAM 8 MB. No se usa PSRAM en este programa.

La configuración `banco` compila con `LUMI_ENABLE_POWER=0`: acepta órdenes de prueba, pero dirección y PWM permanecen a cero. No activar potencia hasta verificar el puente, las corrientes, la polaridad y el paro físico. No hay encoders, botón físico, sensores ni LED de enrolamiento integrados todavía.

Desde esta carpeta, con PlatformIO instalado en un entorno Python 3.12:

```sh
pio run -e banco
pio run -e banco -t upload --upload-port /dev/ttyACM0
```

En Windows usar el COM que enumere la placa. El USB nativo utiliza Serial/JTAG, no el protocolo del USB-UART alternativo. BOOT mantenido + RESET y soltar BOOT permite volver al cargador si la aplicación anterior impide la detección. No conectar un monitor serie y el puente simultáneamente.

Consultar [protocolo y ejecución ROS](../../software/comunicacion/README.md), [conexiones](../../hardware/conexiones/banco-esp-l298n.md) y [registro de trabajo](../../docs/trabajo/base-esp32s3.md).

## Salidas propuestas

| Función L298 | GPIO S3 |
| --- | --- |
| IN1 | 4 |
| IN2 | 5 |
| ENA | 6 |
| IN3 | 7 |
| IN4 | 15 |
| ENB | 16 |

Son números GPIO, no posiciones físicas del conector. Confirmar la serigrafía del adaptador. Estos GPIO están expuestos en la [referencia DevKitC-1](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.0.html). Verificar que la placa concreta sigue ese pinout.

El programa limita la magnitud a 200/1000, no implica límite de corriente. En el banco, el bloqueo de potencia impide toda salida distinta de cero. Un firmware futuro con potencia requerirá ensayo eléctrico independiente. No confundir el estado lógico `armed` ni la orden `left/right` con movimiento medido. `left_pwm/right_pwm` son consignas internas aplicadas, no mediciones eléctricas.

El lazo revisa caducidad cada 5 ms y no bloquea esperando telemetría USB. EN deshabilitado corresponde a rueda libre en el puente, no a frenado mecánico garantizado. El código no sustituye el corte de potencia ni las resistencias de polarización durante reset.

## Banco Wi-Fi temporal

Consultar [red, app y pruebas de canal A](../../hardware/conexiones/banco-wifi-motores.md). Los entornos wifi_banco y wifi_banco_seco agregan SoftAP, HTTP de estado y UDP de control (protocolo 2) separados del banco serie. wifi_banco permite potencia tras rearme, con PWM fijo 15% y límite de pulso de 2 s; el build banco anterior mantiene potencia bloqueada. La integración final con Raspberry/ROS no cambia.


En banco Wi-Fi, actualizar firmware y app 0.5.0 juntos. Contrato vigente, semántica del watchdog y pruebas: [protocolo V2](../../docs/trabajo/banco-protocolo-v2.md).
