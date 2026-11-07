# Inventario y diseño físico preliminar

Estado: información declarada por el usuario, sin inspección ni fichas técnicas verificadas.

| Elemento | Conocido | Pendiente |
| --- | --- | --- |
| Chasis | Estructura metálica de cuatro ruedas propuesta | Dimensiones, masa y montaje |
| Motores | Cuatro DC, dos por lado | Modelo, reducción, tensión, corriente nominal/bloqueo y encoders |
| Puentes H | Actuación por lados prevista | Número de módulos/canales, corriente, disipación y protecciones |
| Computador | Pi 5 4 GB o mini PC i3 candidatos | Modelo, disponibilidad, consumo, refrigeración y SO |
| Cámara | Obligatoria para percepción de cuerpo completo | Modelo, interfaz, óptica, posición y FPS |
| Microcontrolador | Necesario en arquitectura propuesta | Placa y compatibilidad de enlace |
| Batería/alimentación | Operación móvil | Química, capacidad, regulación, fusibles y transitorios |
| Proximidad | Ultrasonido, ToF o IR candidatos | Rango, campo de visión, luz, zonas ciegas y cobertura lateral |
| Encoders | Recomendados para velocidad realimentada | Disponibilidad, resolución e interfaz |
| Parada y mando de enrolamiento | Propuesta de interacción/protección | Botón físico, cableado, rearme y comportamiento |
| IMU / batería | Opciones para giro, diagnóstico y energía | Justificar necesidad; no son compras aprobadas |

No seleccionar sensores por nombre genérico: verificar rango útil, frecuencia y comportamiento sobre superficies y condiciones reales. Un ToF/ultrasonido frontal mide lo que encuentra en su haz, no identifica personas. Un IR de proximidad no reemplaza cámara ni identificación.

Validar el puente H frente a la corriente combinada de los motores que alimenta. Separar y proteger alimentación de lógica y potencia según diseño real, incluyendo masas e interfaces. La lista es una base de análisis, no autorización para adquirir componentes.
