# Preparación de cuatro motores: topología y límites del banco

Fecha: 2026-11-19. Esquema para revisión con fuente apagada, no validación de la capacidad eléctrica del L298N. Firmware actual V2 solo canal A, PWM 60 %, máximo 5 s; canal B continúa a cero. No se modificó firmware ni se habilitaron cuatro motores durante esta documentación.

## Respuesta sobre OUT3 / OUT4

Como referencia equivalente a OUT1/OUT2: conectar el terminal que se usará como positivo de avance de cada motor del segundo lado a OUT3, y el otro terminal a OUT4. No son positivos/negativos permanentes: con IN3 alto, IN4 bajo y ENB habilitado, OUT3 es el lado alto y OUT4 el bajo; al invertir entradas se invierte polaridad. Ver [ST L298: pines y tabla de control](https://www.st.com/resource/en/datasheet/l298.pdf).

Marcar A en cada motor como el terminal que, al recibir positivo, produce avance en la posición real del chasis. Las ruedas de ambos lados están montadas en espejo: el color rojo original no garantiza el sentido de avance. Si una rueda gira al contrario dentro de su pareja, con fuente apagada intercambiar solo los dos cables de ese motor. El usuario ya informó dos inversiones necesarias, sin identificación final por posición.

```text
LADO A                                      LADO B

OUT1 ──┬── A de motor A delantero            OUT3 ──┬── A de motor B delantero
       └── A de motor A trasero                     └── A de motor B trasero

OUT2 ──┬── B de motor A delantero            OUT4 ──┬── B de motor B delantero
       └── B de motor A trasero                     └── B de motor B trasero
```

Cada pareja está en paralelo. Cada motor se conecta entre las dos salidas de su canal, nunca de OUT a GND de alimentación. No unir OUT1 con OUT3, ni OUT2 con OUT4, para este esquema de control independiente por lados. Una regleta solo distribuye conexiones: no incrementa capacidad de fuente ni driver.

## Señales ESP32-S3 previstas

| ESP | Módulo L298N | Situación |
| --- | --- | --- |
| GPIO4 | IN1 | Canal A actual |
| GPIO5 | IN2 | Canal A actual |
| GPIO6 | ENA, pin de señal | PWM actual |
| GPIO7 | IN3 | Reservado para canal B; hoy bajo |
| GPIO15 | IN4 | Reservado para canal B; hoy bajo |
| GPIO16 | ENB, pin de señal | Reservado para PWM B; hoy bajo |
| GND | GND | Referencia común |

Son números GPIO, no posiciones del cabezal ni nombres D de otra placa. Antes de conectar GPIO16 a ENB, retirar jumper que une ENB a 5 V y añadir pulldown 10 kohmios ENB–GND como el instalado en ENA. Verificar serigrafía: no usar pin 5 V del par de jumper como señal. Retirar jumper ENA también si no estaba ya retirado. No conectar nunca el 5 V de ese par a un GPIO.

```text
GPIO6  ────── ENA          GPIO16 ────── ENB
              │                          │
            10 kΩ                      10 kΩ
              │                          │
GND común ────┴──────────────────────────┘
```

## Alimentación (conservar separación del ensayo)

```text
Fuente +12 V ── protección/corte dimensionados ── VCC / +12 V del módulo
Fuente negativo ──────────────────────────────── GND del módulo
ESP GND ──────────────────────────────────────── GND común
PC / Raspberry USB ───────────────────────────── ESP
```

Conservar configuración de lógica 5 V del módulo ya comprobada; función exacta/revisión de JP1 sigue sin esquema confirmado. No unir el 5 V del driver con el 5 V de la ESP mientras esta recibe USB. No sustituir GND común por un terminal de salida del puente. Regletas, cables y bornes de potencia deben estar dimensionados para corriente conjunta; protoboard/Dupont son para señales, no corriente de motores.

## Qué falta antes de activar ambos lados

1. Corregir y validar identidad/frescura de sesión en comunicación; no rearmar automáticamente ante token vencido ni pérdida real.
2. Elegir/controlar driver para demanda combinada y verificar fuente. L298 tabla 1: 2 A continuos por puente es máximo absoluto del integrado, no garantía térmica de módulo. Usuario reportó pico de 4 A en fuente con una pareja; no es caracterización de corriente de bobinas, pero tampoco valida cuatro motores. Fuente TE-5305 máximo nominal 5 A puede limitar con cuatro motores: medir, no inferir que basta.
3. Implementar explícitamente PWM/dirección B y comprobaciones de parada antes de ensayos. El firmware actual inicializa GPIO7/15/16 a cero y no genera PWM B: conectar cables no lo habilita.
4. Ensayar cada lado con ruedas elevadas y revisar sentido real; luego combinar solo con alimentación, driver y protección adecuados. [Drivers alternativos](../drivers-mayor-corriente.md).

## Error de token y arquitectura

Usuario reporta token vencido, rearme antiguo e intervalo 2 ms en app 0.6.0. Lectura USB pasiva: fault=token_vencido, rejection=rearme_antiguo, epoch=55, seq=470, gap_ms=91, PWM=0, desarmado y teléfono asociado. El intervalo es separación entre recepciones, no RTT ni edad del token; 2 ms puede corresponder a una ráfaga tras retraso.

Inspección: MotorSessionToken guarda received con el momento de recibir y MotorBankSession ignora started. La ventana DriveAckWindow admite ACK retrasados de hasta 200 ms, pero la sesión no descuenta ese tránsito de la vigencia de 250 ms impuesta por ESP. Esto identifica una limitación real que puede reutilizar un ticket antiguo; no se capturó la trayectoria exacta del paquete del teléfono para cuantificar el retraso. No ocultar el fallo ampliando watchdog ni permitir rearme automático. La corrección de frescura y recuperación de estado queda pendiente; esta documentación no entrega otro APK ni afirma resuelta la comunicación.

Wi-Fi es el enlace de radio, UDP el transporte que usa el banco. Cambiar a TCP/Bluetooth no sustituye validar secuencia, antigüedad y rearme. Mantener la arquitectura final Android→Wi-Fi→Raspberry/ROS 2→USB→ESP. Reconectar/consultar estado no autoriza reanudar movimiento automáticamente.


Actualización app 0.6.1: se implementó corrección de frescura y recuperación del canal en [registro correspondiente](../../docs/trabajo/recuperacion-canal-datos.md). Pruebas locales correctas; validación del teléfono pendiente. No se actualizó firmware ni se habilitó canal B/cuatro motores.
