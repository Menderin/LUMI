# Registro de decisiones técnicas

Actualizado: 2026-11-19. Confirmado significa respaldado por petición o fuente indicada; no significa implementado ni validado experimentalmente.

| ID | Decisión o hipótesis | Estado y origen | Motivo / condición para cerrar |
| --- | --- | --- | --- |
| D-01 | Separar software, firmware, hardware, pruebas, modelos, docs y Agents | Confirmado por usuario | Organización del repositorio |
| D-02 | MVP en superficies lisas, sin cargas significativas ni escaleras | Base documental del Charter | Validar funciones antes de escalar |
| D-03 | Procesamiento local sin API externa de IA | Restricción explícita del usuario | Operación autónoma local |
| D-04 | Cuatro ruedas/motores, dirección diferencial por lados | Diseño declarado por usuario; inventario pendiente | No implica orugas físicas ni driver ya dimensionado |
| D-05 | Python para IA | Orientación explícita del usuario | Facilitar experimentación; versiones pendientes |
| D-06 | ROS 2 en Raspberry; C++/ESP-IDF en ESP32-S3 | Arquitectura acordada; firmware de banco presente | ROS y percepción en Raspberry todavía pendientes de desplegar |
| D-07 | Comparar PCA Euclídea/Mahalanobis y autoencoder; Re-ID como referencia candidata | Propuesto | Resolver divergencia entre documentos con mediciones |
| D-08 | Parar ante pérdida/ambigüedad; sin búsqueda móvil por defecto | Propuesta de seguridad compatible con HU de Trello | Acordar tiempos, reacquisición y rearme |
| D-09 | USB serie para Raspberry–ESP; sin micro-ROS en primera integración | Seleccionado para banco e integración | Wi-Fi directo de ESP es solo un modo temporal de ensayo de motores |
| D-10 | CMake/ament/colcon; Conan solo si aporta dependencia externa | Propuesta | No instalar una segunda cadena de paquetes sin necesidad |
| D-11 | Instrucciones modulares y flujo ODD local | Solicitado por usuario; adaptación para revisión | AGENTS.md enruta; no instala Gentle AI/Engram/RDD |

## Cómo actualizar

Conservar ID, fecha, fuente, alternativas y motivo de cualquier cambio relevante. Una prueba puede invalidar una hipótesis sin ampliar el alcance. Cambios de funciones o compromisos requieren acuerdo; correcciones documentales rutinarias no necesitan aprobación adicional.

## D-12: Datos propios y enrolamiento

Estado: organización documental solicitada por el usuario. Separar herramientas de construcción del dataset, lógica de enrolamiento y almacenamiento local de datos. Propuesta: comenzar capturas con cámara en soporte a geometría prevista y repetir validación en el robot montado. Volumen, cámara y protocolo final pendientes. Este apartado conserva el acuerdo inicial de organización; consultar docs/construccion-dataset.md y el código de dataset/experimentos para el estado posterior. La existencia de herramientas no demuestra que haya un dataset humano construido y validado.

## Consolidación del 2026-11-19

Las decisiones siguientes reflejan las revisiones del chat técnico. Acordado no significa probado en el robot completo. Las cifras de ensayo son configuraciones iniciales, no criterios físicos certificados.

| ID | Decisión | Estado, evidencia y documento de referencia |
| --- | --- | --- |
| D-13 | Raspberry Pi 3 Model B, 1 GB, sustituye Pi 5 por presupuesto | Confirmado por usuario. NUC/Pi 5 quedan como referencias históricas. [Arquitectura](plan-arquitectura-raspberry-esp.md) e [inventario](../hardware/componentes.md) |
| D-14 | Ubuntu Server 24.04 arm64 + ROS 2 Jazzy ros-base; operación por consola/SSH | Usuario informa que instaló Ubuntu Server; versión/arquitectura aún por comprobar en la placa. GUI Xfce/LXQt opcional, no requisito de cámara. [Instalación](instalacion.md) |
| D-15 | Una captura de cámara compartida por ROS; web_video_server como primer candidato integrado de visualización | Dirección aceptada para preparar piloto; falta cámara, driver y medición. uStreamer es referencia separada, no otro capturador concurrente. MediaMTX/H.264 y GStreamer se consideran si las medidas lo justifican. [Vídeo](video-ros-pi3.md) |
| D-16 | Iniciar piloto de vídeo con un canal lógico 640×480 a 10 FPS si está soportado | Configuración de ensayo, no garantía. Medir después a 15 FPS con IA activa. Sin latencia prometida por protocolo. Raw local permitido; red comprimida. [Vídeo](video-ros-pi3.md) |
| D-17 | Conservar Android nativo y contrato de snapshots /foto.jpg al integrar ROS inicialmente | Aplicación presente. Adaptador cámara ROS/gateway pendiente; MJPEG/RTSP/WebRTC no se decodifican automáticamente en el APK. [Vídeo](video-ros-pi3.md) |
| D-18 | La Raspberry decide movimiento y es único publicador /base/cmd_vel; ESP conserva parada por caducidad | Plan de integración, sin sistema final desplegado. [Responsabilidades](plan-arquitectura-raspberry-esp.md) |
| D-19 | Banco temporal Android→Wi-Fi ESP, solo canal A OUT1–OUT2 | Solicitado y aprobado por usuario. Firmware y APK presentes, lectura HTTP externa verificada por usuario; movimiento estable aún pendiente. [Banco Wi-Fi](../hardware/conexiones/banco-wifi-motores.md) |
| D-20 | Banco: PWM 15%, 1 kHz, pulso máximo 2 s, rearme explícito y watchdog de 250 ms desde recepción válida (V2) | Límites de software de ensayo, no límite de corriente ni validación del driver. [Registro de banco](trabajo/banco-wifi-motores.md) |
| D-21 | Conservar originales, particiones independientes y galería fija; entrenamiento offline en servidor con dos RTX A5000 | Contexto del usuario y plan acordado. No depender de IA remota en operación. [Percepción](plan-percepcion.md) y [tratamiento de imágenes](tratamiento-imagenes.md) |
| D-22 | Dimensionar potencia con mediciones; L298N no aprobado por los consumos observados | 1–4 A se observaron a tensión reducida y frenando a mano, no son máximos a 12 V. Fuente de 5 A. Opinión del docente y giro sin carga no sustituyen caracterización. [Circuito](../hardware/conexiones/banco-esp-l298n.md) |

No se borró la instalación anterior de la Raspberry desde este chat, no se formateó una unidad desde herramientas y no se ejecutaron pruebas físicas de movimiento por el agente. Conservar evidencias, revisar cambios y distinguir las pruebas de software de la validación física del MVP.

## D-23: Corrección del transporte de banco, 0.5.0

Tras persistir HTTP 409/caducidad en 0.4.4, se reemplaza la estimación de reloj y el control HTTP de la app por tickets ESP y datagramas UDP con ACK. Solo afecta al banco temporal; ROS/USB final se conserva. Watchdog 250 ms desde recepción válida, ticket de movimiento menor de 250 ms, sin prometer parada a 250 ms desde generación. PWM/pulso/rearme no cambian. [Contrato y evidencia](trabajo/banco-protocolo-v2.md). Compilación, pruebas lógicas y arranque verificados; mando en teléfono y actuación física pendientes.


## D-24: Diagnosticar el enlace del teléfono antes del ensayo físico

App 0.5.1 incorpora prueba de PING sin habilitación, informe de RTT/pérdidas y separación de gesto/TX/ACK. Se solicita WifiLock de baja latencia sin garantizar soporte. Se reemplaza espera de ACK 100 ms por 180 ms en movimiento/parada y 600 ms en ping/rearme, conservando límites ESP V2. Hipótesis de ahorro energético pendiente de medición real. [Evidencia y pruebas](trabajo/diagnostico-joystick-enlace.md). No implica validación física ni cambia arquitectura ROS/USB.


## D-25: Perfil de ensayo solicitado PWM 20 % / 500 ms

Después de pitido sin giro a 15 %, se autoriza ajuste limitado a 20 % y se reduce el pulso de 2 s a 500 ms. Usuario mantiene dos motores en OUT1–OUT2; fuente declarada 12 V/CV, límite real no verificado. No valida corriente ni capacidad del L298. Se conservan parada por caducidad, tickets, rearme y canal B a cero. [Implementación y evidencia](trabajo/ensayo-pwm20.md). Sustituye cifras iniciales de D-20 para este perfil de banco; validación física pendiente.
