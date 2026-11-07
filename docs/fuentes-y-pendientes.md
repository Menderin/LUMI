# Fuentes, estado y decisiones pendientes

Consulta: 2026-11-07. Esta fotografía no sustituye consultar nuevamente las fuentes antes de implementar.

## Referencias locales y externas

- [Project Charter](Project%20Charter%20Robot%20seguidor.pdf), fechado 7 de noviembre de 2026: alcance, métricas, entregables y roles. Se conserva intacto.
- [Análisis tecnológico](Analisis_Arquitectura_Tecnologica_Inicial.pdf): comparación preliminar sin inventario verificado. Puntajes conceptuales, no benchmarks.
- Conversación técnica del usuario de esta fecha: chasis de cuatro ruedas/motores, cómputo local, alternativas PCA/autoencoder, preferencia ROS 2 y Python para IA.
- [GitHub](https://github.com/Menderin/LUMI): búsqueda de issues/PR sin resultados; HEAD local 1f0e196, estructura y PDFs aún sin commit al comenzar esta actualización.
- [Trello](https://trello.com/b/nIFw6wUM/gesti%C3%B3n-proyectos-ia): arquitectura inicial en Doing; backlog, alcance, consolidación de reunión y riesgos de I1 en Done; I2–I4 en Backlog. No se modificaron tarjetas.

## Discrepancias por resolver

| Tema | Evidencia | Tratamiento |
| --- | --- | --- |
| Identificador | Charter favorece YOLO + Re-ID; análisis favorece PCA con otra distancia; usuario propone PCA y autoencoder | Opciones experimentales; arquitectura no seleccionada |
| Autonomía | Should en MoSCoW; mínimo 30 min en aceptación | Conservar meta y confirmar obligatoriedad |
| Responsables | Charter: Víctor hardware/Vicente software; Trello reparte tarjetas de ambas áreas | No reasignar: rol general y responsabilidad de tarjeta son niveles distintos |
| Tablero | Charter propone columna Pruebas/Validación; Trello actual no la tiene | No crearla sin coordinar con gestión; documentar evidencia por tarjeta |
| Distancia | Charter: 1,5 m ±0,3; tarjetas antiguas dicen por validar | Incorporar valor con fuente; falta protocolo y ratificación operacional |
| Plataforma | Usuario: Pi 5 4 GB o i3; análisis también menciona N100/Jetson | Limitar candidatos actuales a Pi/i3; otros no están seleccionados |
| Sensores y seguridad | Sensores Should; Trello exige evitar colisiones | Definir nivel de protección y criterio antes de pruebas con movimiento |

## Datos necesarios antes de cerrar arquitectura

1. Inventario: computador exacto, SO, cámara, placa, motores, drivers, batería y sensores disponibles.
2. Corrientes de bloqueo, canales, alimentación, masa, dimensiones, ruedas y encoders.
3. Detector y esquema de enrolamiento, datos, duración e interacción física.
4. Método de distancia al usuario y asociación entre cámara y proximidad.
5. Velocidad máxima, tiempos de parada, comando caducado, obstáculo y reanudación.
6. Recorrido, repeticiones y condiciones para medir los criterios del Charter.

## Fuentes técnicas consultadas

- [ODD, Gentle AI](https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/usage.md#organic-driven-development-odd): origen del enfoque; adaptación local en Agents/ODD.md, sin instalar el producto.
- [ROS 2 Jazzy en Ubuntu](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html): combinación candidata, no instalación validada del robot.
- [diff_drive_controller](https://control.ros.org/jazzy/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html): interfaces de velocidades y parada por timeout.
- [micro-ROS](https://github.com/micro-ROS/micro_ros_setup): soporte de firmware que depende de placa y plataforma.
- [Conan build/host](https://docs.conan.io/2/tutorial/consuming_packages/cross_building_with_conan.html): perfiles para construir y ejecutar en arquitecturas distintas; no sustituye compilador.
- Referencias de PCA, covarianza y autoencoder en evaluacion-ia.md.

## Aclaraciones posteriores a la consulta

El usuario confirmó que el nombre anterior Juan Villegas fue un error al hablar. Se conserva Dr. Juan Bekios Calfa, grafía del Charter, como stakeholder. La discrepancia deja de estar pendiente.

Se incorpora la necesidad de datos propios desde la geometría de cámara baja y se documenta en [construcción del dataset](construccion-dataset.md). No se afirma inexistencia de datasets públicos adecuados ni que ya haya capturas disponibles.
