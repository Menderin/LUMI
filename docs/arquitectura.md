# Arquitectura preliminar

Estado: propuesta para revisión; sin interfaces implementadas. Basada en el Charter, el análisis tecnológico y el contexto del usuario del 2026-11-07.

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
