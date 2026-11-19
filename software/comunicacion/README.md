# Puente ROS 2 y protocolo de banco

ROS se ejecuta en Raspberry/NUC con Linux. La ESP ejecuta [firmware C++/ESP-IDF](../../firmware/controlador/README.md). Esta implementación usa USB serie, no micro-ROS. Android y percepción todavía no están conectados a este puente.

## Protocolo L1

ASCII delimitado por `\n`, hasta 120 caracteres por trama antes del salto. Ejemplo estructural, no una trama con CRC calculado:

```text
L1 boot seq deadline_ms modo izquierda derecha CRC16
```

`boot` es un identificador aleatorio publicado por la ESP en cada arranque. `seq` aumenta estrictamente, uint32 sin vuelta dentro de una sesión. `deadline_ms` es tiempo de la ESP, uint32, debe quedar entre 1 y 250 ms por delante al recibirlo. El cliente estima ese reloj desde la telemetría y da 180 ms de vigencia. Se admite la vuelta del contador de tiempo, no la de secuencia.

Modo 0 deshabilita. Modo 1 rearma con ambas magnitudes cero. Modo 2 solicita movimiento, solo si existe rearme vigente. Magnitudes enteras en milésimas de duty, limitadas a ±200 para banco. Un valor positivo es el sentido definido por IN1/IN3 alto, que aún debe contrastarse con la orientación de montaje. Las órdenes no expresan m/s ni corriente medida.

CRC-16/CCITT-FALSE, inicial 0xFFFF, polinomio 0x1021, sin reflexión ni XOR final. Se calcula sobre todos los bytes anteriores al espacio del CRC, sin ese espacio ni el salto final. `protocolo.frame` genera tramas válidas. No introducir espacios adicionales.

La ESP publica JSON a 20 Hz: versión, boot, secuencia aceptada, uptime, armado, dry_run, consignas izquierda/derecha, PWM aplicado y motivo de parada. Trama inválida/excesiva, sesión incorrecta, secuencia repetida, deadline inválido o caducidad desarman. No renovar el watchdog con bytes inválidos. La caducidad es el primero entre el deadline de la orden y 250 ms sin orden válida. La ausencia de enlace nunca rearma.

## Banco USB sin ROS

Desde la raíz del repo, con pyserial 3.5 instalado:

```sh
python -m software.comunicacion.probar_base_usb --port /dev/ttyACM0 --output datos/procesados/base-usb/resultado.json
```

En Windows usar `--port COM7` o el puerto actual. La prueba se niega a enviar consignas si el firmware no declara `dry_run=true`. Comprueba rearme, órdenes sin rearme, giro lógico con PWM cero, replay, deadlines vencidos, CRC inválido, trama excesiva, sesión incorrecta y caducidad. No energizar motores durante esta prueba.

## Nodo ROS 2

En Ubuntu con ROS 2 Jazzy instalado, desde raíz, `python3-serial` disponible y acceso al puerto:

```sh
source /opt/ros/jazzy/setup.bash
python3 -m software.comunicacion.puente_ros --ros-args -p port:=/dev/ttyACM0 -p separation_m:=ANCHO_MEDIDO -p wheel_reference_mps:=VELOCIDAD_CALIBRADA
```

Sustituir ambos marcadores por números en metros y m/s medidos. Se rechaza el arranque con valores cero o no finitos. La velocidad de referencia relaciona m/s con duty en lazo abierto; sin encoders esto no es control cerrado de velocidad. No inventar esos valores para una prueba física. Para el ensayo de comunicación usar el banco USB anterior.

Suscribe `/base/cmd_vel` (`geometry_msgs/TwistStamped`), publica `/base/estado` (`std_msgs/String`, JSON anterior), y ofrece `/base/habilitar_banco` (`std_srvs/SetBool`). Solo acepta linear.x y angular.z, comandos con timestamp creciente y antigüedad menor de 150 ms. Mezcla diferencial, saturación proporcional al 20% y envío a 20 Hz. Validar esta frecuencia con hardware antes de cualquier prueba física.

Tras recibir telemetría:

```sh
ros2 service call /base/habilitar_banco std_srvs/srv/SetBool '{data: true}'
ros2 topic echo /base/estado
ros2 service call /base/habilitar_banco std_srvs/srv/SetBool '{data: false}'
```

La respuesta positiva del servicio confirma envío, no rearme físico. Confirmar `armed` en el feedback. Hasta una primera consigna, el puente conserva cero. Tras comenzar, una consigna caducada deshabilita y exige un nuevo servicio de rearme. Un reinicio de la ESP detiene el nodo y exige reiniciarlo y rearmarlo; no hay reconexión con movimiento automático.

La decisión de autorizar seguimiento pertenece al futuro nodo de control: debe usar identidad válida, modo y seguridad. Este servicio es de banco y no sustituye ese arbitraje. La integración Android, los LED, los sensores, el botón y ROS en equipo destino siguen pendientes. No hay odometría ni velocidad medida.
