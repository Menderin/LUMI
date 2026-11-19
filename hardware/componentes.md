# Inventario y diseño físico preliminar

Estado actualizado el 2026-11-18. Fotografías aportadas por el usuario, inspección USB local y ficha del L298. Los datos no visibles se mantienen pendientes.

| Elemento | Conocido | Pendiente |
| --- | --- | --- |
| Chasis | Estructura metálica de cuatro ruedas propuesta | Dimensiones, masa y montaje |
| Motores | Cuatro DC declarados. Foto de XD-37GB520, 12 V, salida 30 rpm; etiqueta del motor ZYTD520, 12 V, 5000 r/min | Usuario observó 1–4 A a tensión inferior a 12 V frenando la rueda a mano; no es rango nominal ni máximo a 12 V. Fuente de 5 A; caracterizar arranque/carga sin frenado manual. Confirmar que los cuatro son iguales, torque y encoders |
| Puentes H | Un módulo fotografiado compatible visualmente con L298N, dos canales, disipador y diodos | Leer marcado del integrado y regulador; verificar jumpers, corriente y disipación. Descartado para cuatro motores con los consumos declarados de 1–4 A por motor |
| Computador | Raspberry Pi 3 Model B fijada por usuario el 2026-11-19 por presupuesto; 1 GB RAM | Preparar Ubuntu Server 24.04 arm64, validar cámara, alimentación, consumo y rendimiento del pipeline |
| Cámara | Obligatoria para percepción de cuerpo completo | Modelo, interfaz, óptica, posición y FPS |
| Microcontrolador | ESP32-S3 QFN56 rev. 0.2 confirmado por esptool; 240 MHz, flash 16 MB, PSRAM 8 MB. USB Serial/JTAG COM7 en descarga; foto de placa de dos USB con adaptador de bornes | Confirmar revisión exacta del PCB/adaptador y serigrafía; en modo normal anterior enumeraba COM6 VID 303A/PID 4001 |
| Batería/alimentación | Operación móvil | Química, capacidad, regulación, fusibles y transitorios |
| Proximidad | Ultrasonido, ToF o IR candidatos | Rango, campo de visión, luz, zonas ciegas y cobertura lateral |
| Encoders | Recomendados para velocidad realimentada | Disponibilidad, resolución e interfaz |
| Parada y mando de enrolamiento | Propuesta de interacción/protección | Botón físico, cableado, rearme y comportamiento |
| IMU / batería | Opciones para giro, diagnóstico y energía | Justificar necesidad; no son compras aprobadas |

No seleccionar sensores por nombre genérico: verificar rango útil, frecuencia y comportamiento sobre superficies y condiciones reales. Un ToF/ultrasonido frontal mide lo que encuentra en su haz, no identifica personas. Un IR de proximidad no reemplaza cámara ni identificación.

Validar el puente H frente a la corriente combinada de los motores que alimenta. Separar y proteger alimentación de lógica y potencia según diseño real, incluyendo masas e interfaces. La lista es una base de análisis, no autorización para adquirir componentes.
