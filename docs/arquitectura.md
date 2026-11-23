# Arquitectura preliminar

Estado actualizado el 2026-11-19: existen interfaces de banco en código, sin integración física validada. El [plan Raspberry + ESP32-S3](plan-arquitectura-raspberry-esp.md) consolida responsabilidades, contratos vigentes, etapas y preparación de la Raspberry. Ese plan prevalece sobre las alternativas históricas de este documento. La base conceptual siguiente conserva el contexto del 2026-11-07.

## Separación física y lógica

Flujo propuesto: cámara → detección corporal → recorte normalizado → identificación del enrolado → seguimiento temporal → estimación lateral/distancia → control con inhibición de seguridad → comunicación → firmware → puentes H → motores.

Los sensores aportan medidas a control y/o firmware según latencia e interfaz. Una lectura frontal de proximidad puede pertenecer a un obstáculo y no al usuario: no sustituye por sí sola la distancia a la persona identificada.

| Capa | Responsabilidad | Tecnología y estado |
| --- | --- | --- |
| Cómputo principal | Percepción y coordinación | Pi 5 de 4 GB o mini PC i3, por seleccionar |
| IA | Detección, enrolamiento, identidad y asociación | Python; OpenCV/scikit-learn candidatos; detector y modelo pendientes |
| Integración | Mensajes, lanzamiento, diagnóstico y control | ROS 2 preferido; distribución y SO pendientes |
| Control | Convertir error de distancia/lateral en velocidades limitadas | Python o C++ por medir; PID es candidato, no elección cerrada |
| Enlace | Comandos con vigencia y telemetría | Serie simple o micro-ROS, por decidir |
| Firmware | PWM, dirección, sensores y parada por caducidad | C/C++, placa pendiente |
| Potencia | Actuación por lados y alimentación protegida | Cuatro motores DC; canales y drivers por dimensionar |

ROS 2 se ejecuta en Linux, no reemplaza el firmware. micro-ROS solo se evalúa tras conocer placa, memoria y soporte. No introducir navegación global, SLAM, nube ni Nav2 para el seguimiento básico sin una necesidad acordada.

## Dirección diferencial de cuatro ruedas

Dos ruedas por lado reciben la actuación de su lado; el giro es por diferencia de velocidades, incluso contrarrotación. Se denomina skid-steer: no requiere orugas físicas. La aproximación inicial es v_izq = v − ω·b/2 y v_der = v + ω·b/2, en m/s, con b como separación efectiva entre lados. Convertir a velocidad angular de rueda exige radio conocido.

El deslizamiento lateral en giros impide asumir odometría ideal. Calibrar separación efectiva y respuesta de los motores sobre la superficie de prueba. Si no hay encoders, no afirmar control cerrado de velocidad ni odometría medida.

## Contratos propuestos

| Frontera | Datos mínimos | Invalidez y pendientes |
| --- | --- | --- |
| Percepción → control | Tiempo de captura, bbox, asociación, puntuación, validez; distancia si existe | Esquema, unidades y caducidad por fijar |
| Control → enlace | v en m/s, ω en rad/s, secuencia y vigencia | Saturación, frecuencia y timeout pendientes |
| Firmware → principal | Estado, último comando, fallos y sensores disponibles | No prometer batería/encoders si no existen |

No fijar aún tipos Twist/TwistStamped o protocolo binario: dependen del controlador ROS y versión seleccionados. Referencia candidata: [diff_drive_controller](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html), que ofrece conversión de velocidades y parada por timeout; adoptarlo requiere interfaz de hardware adecuada.

## Estados funcionales propuestos

Inicio detenido → espera → enrolamiento detenido → listo → seguimiento. Desde seguimiento: pérdida/ambigüedad, obstáculo o fallo → detenido con motivo. La observación visual puede continuar estando detenido; rearme, reacquisición y giro de búsqueda siguen pendientes. No reemplazar identidad con el candidato más cercano cuando la comparación falla.

## Despliegue

Inferencia y control operan localmente en CPU como restricción inicial. Entrenamiento experimental puede hacerse en otro PC local y exportarse si se acuerda; no depender de nube durante operación. Medir detector, identificador y transporte de imágenes como conjunto.

ROS 2 Jazzy con Ubuntu 24.04 de 64 bits es una combinación candidata con paquetes arm64/amd64; verificar cámara y placa antes de adoptarla. [Referencia oficial](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html). En un workspace ROS, usar ament/colcon; Conan es opcional para dependencias externas, no sustituye el ecosistema ROS ni compila por sí mismo.

## Adquisición de datos y enrolamiento

Las herramientas offline de captura y preparación se ubican en software/percepcion/dataset/; el módulo operativo de registro del usuario, en software/percepcion/enrolamiento/. Comparten trazabilidad y preprocesamiento cuando se implementen, pero el constructor de datasets no debe convertirse en dependencia obligatoria de cada arranque. Datos y galerías se almacenan localmente en datos/. Ver [protocolo de captura](construccion-dataset.md).

## Botón, enrolamiento y LED

El módulo `software/percepcion/enrolamiento/estado.py` recibe tiempo monotónico, flanco del botón, número de personas, recorte validado, confirmación de cobertura y coincidencia vigente. Emite permiso lógico de seguimiento y salidas verde/rojo/ámbar. El permiso no es un comando de motor.

Desde espera, pulsar inicia 10 s de giro pausado a 1,5 m. Ámbar fijo durante captura. Aceptar una sola persona, hasta 12 recortes separados por 0,8 s. El mínimo provisional es 8, configurable tras el piloto. El operador confirma las cuatro vistas. Tras fallo, ámbar intermitente y reintento por pulsación, hasta cinco intentos. Tras éxito, tres destellos verdes de 250 ms separados por 250 ms y luego apagado. Pulsar con coincidencia válida inicia seguimiento, verde fijo. Pérdida o ambigüedad corta permiso y enciende rojo. Recuperar identidad no rearma sin pulsación. Al iniciar una nueva sesión, crear un estado nuevo.

GPIO, antirrebote, validación de calidad de recortes y caducidad de detección corresponden al adaptador físico pendiente. Verificar patrones con motores deshabilitados antes de integrar control.

## Propuesta para el banco del 18 de noviembre

Usar un solo computador principal, Pi 5 o NUC i3, para cámara, IA y ROS 2. Para el primer banco usar el equipo que ya pueda leer la cámara y ejecutar Ubuntu 24.04 con ROS 2 Jazzy. Mantener enchufable el equipo para comparar ambos después. En el ESP32 ejecutar firmware C++ con ESP-IDF para PWM, dirección, botón, LED y sensores disponibles. Usar la placa disponible. ESP32-S3 es candidato si se requiere USB nativo o faltan periféricos en la placa actual.

| Nodo en el computador | Suscribe | Publica o ejecuta |
| --- | --- | --- |
| cámara | — | /camera/image_raw (sensor_msgs/Image). Abrir un canal RGB inicialmente. |
| percepción (Python) | /camera/image_raw, /base/boton | /percepcion/objetivo (mensaje propio con timestamp de captura, validez, error lateral normalizado y distancia válida en metros si existe), /percepcion/estado (estado de enrolamiento, listo, seguimiento o pérdida). Reusar detector e identificadores del banco. |
| control (Python inicialmente) | /percepcion/objetivo, /percepcion/estado, /base/estado | /base/cmd_vel (geometry_msgs/TwistStamped). Es el único publicador de movimiento. |
| puente serie | /base/cmd_vel, /percepcion/estado | /base/estado y /base/boton. Traduce a órdenes de rueda y LED y recibe telemetría del ESP32. |

Para imágenes, usar QoS de sensor y colas cortas. Para comandos, usar cola de un elemento y rechazar órdenes vencidas. El firmware conserva autoridad para cortar salida si caduca el enlace. Una observación inválida, ambigua, vencida o sin distancia fiable inhibe el avance autónomo. No usar la altura del recuadro como distancia sin calibración. El estado listo enciende los destellos ya acordados. Para iniciar o reanudar el seguimiento se exige pulsación con identidad vigente.

### Enlace y primer control

Conectar por USB serie mediante el puerto nativo o el puente de la placa. Preferirlo frente a GPIO directos para que el mismo diseño funcione en Pi y NUC. Si se usa UART físico, verificar voltajes y masa común con la placa apagada. USB alimenta la lógica según la placa. La potencia de motores requiere su propia alimentación dimensionada.

Para banco, usar mensajes de texto delimitados por salto de línea, versión y número de secuencia. Orden: versión, secuencia, habilitación, izquierda, derecha y estado LED. Respuesta: secuencia aceptada, estado, flanco de botón y fallos. Usar magnitudes normalizadas de -1 a +1 para banco sin encoders. Con encoders, migrar a setpoints y medidas en unidades físicas. Descartar tramas incompletas, inválidas o antiguas. Tras reinicio o reconexión, permanecer deshabilitado hasta un rearme explícito. Validar primero 20 Hz de comando y watchdog de 250 ms con motores deshabilitados. Son valores de ensayo, no límites validados para uso físico.

Probar primero la mezcla diferencial con salidas simuladas. Cuando se haya comprobado el driver y cableado, verificar signos por lado con ruedas elevadas. Usar C++ en firmware y Python con rclpy en el computador. Evaluar rclcpp solo si perfiles muestran retrasos atribuibles al nodo. CPython es el intérprete del computador. MicroPython se puede usar para exploración, pero el primer firmware de control usará ESP-IDF. micro-ROS es una alternativa al puente serie si se necesita que la placa participe en ROS mediante cliente y agente.

### Orden de trabajo en laboratorio

1. Identificar cámara, placa, drivers y encoders. Abrir el vídeo en el computador a altura real y grabar una secuencia corta. Confirmar puertos y geometría.
2. Probar el puente con motores deshabilitados. Simular avance/giro, desconexión, reinicio y comando inválido. Comprobar salida cero y que reconectar no rearma.
3. Integrar botón, LED y giro de 10 s con la cámara. Inspeccionar las muestras guardadas. Ensayar éxito, fallo, pérdida y rearme.
4. Con cableado verificado, probar polaridad y parada con ruedas elevadas. La prueba en suelo requiere distancia fiable, paro local y límites verificados.

### Interfaz de celular para evaluar después

Propuesta separada para revisión de alcance. Una web local en el computador serviría una vista RGB comprimida, estado y solicitud de enrolamiento. El mando manual tendría modo explícito y control de pulsación sostenida, retorno a cero al soltar o perder conexión, y prioridad de parada local. La interfaz envía solicitudes al mismo nodo de control. Este valida el modo y arbitra las órdenes, manteniendo un solo publicador de movimiento. Empezar por vista y estado si se aprueba. El botón físico sigue siendo el camino de laboratorio.

Referencias: [ROS 2 Jazzy en Ubuntu](https://repo.test.ros2.org/en/jazzy/Installation/Ubuntu-Install-Debs.html), [micro-ROS para ESP-IDF](https://github.com/micro-ROS/micro_ros_espidf_component), [USB serie del ESP32-S3](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/usb_serial_jtag.html).

Prototipo de banco disponible en [software/panel_movil](../software/panel_movil/README.md). El modo local muestra cámara y prueba la solicitud de enrolamiento. La integración con ROS y el mando de motores siguen pendientes.


## Banco Wi-Fi temporal, protocolo 2

Solo para ensayo Android→ESP: app 0.5.0 usa UDP 8082 con ACK/tickets ESP para canal A; HTTP 8080 entrega estado. Sustituye deadlines estimados de V1. Watchdog 250 ms desde última recepción válida, pulso máximo 2 s y rearme manual. No altera el futuro supervisor ROS ni el enlace USB. Ver [contrato y limitaciones temporales](trabajo/banco-protocolo-v2.md).

## Sesion de percepcion y direccion simulada, 2026-11-20

El NUC mantiene la sesion de enrolamiento. La ventana usa acciones iniciar, confirmar, cancelar, repetir, iniciar_seguimiento y reanudar. Confirmar deja Listo y no inicia seguimiento. La futura app invocara esas acciones sobre el mismo propietario. Las zonas 40-60 % con histeresis producen intenciones visuales; Alineado no autoriza avance ni mide distancia. Ver [flujo y contratos](trabajo/enrolamiento-comparable.md).

En el piloto visual, la recuperacion simulada continua tras perdida y reanuda con tres coincidencias consecutivas. Es un modo explicito de la practica, con busqueda visual y registro. El contrato de actuacion fisica requiere su validacion independiente. Ver el registro de enrolamiento comparable.

## Banco de vision movil en NUC (2026-11-23)

La app 0.8.0 selecciona una persona sobre video y controla enrolamiento en el NUC, que administra su Wi-Fi. Movimiento restringido tanto en app como en este servidor, sin conexion ESP/ROS de actuacion. Leer [contrato, arranque y verificacion](trabajo/enrolamiento-movil-nuc.md). La nueva entrada es python -m software.percepcion.servidor_movil, distinta del servidor de simulacion anterior.


## Video WebRTC nativo0.9.0

[Transporte, arranque y prueba A/B](trabajo/webrtc-movil-nuc.md): servidor de vision con --webrtc, app nativa VP8 y HTTP para estado/enrolamiento; UDP50000-50009 del hotspot. Comparacion explicita conJPEG. Camara unica y movimiento restringido. Validacion fisica NUC/telefono pendiente.
