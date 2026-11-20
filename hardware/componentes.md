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


## L298N: marcado informado y ensayo al 60 % (2026-11-19)

El usuario informa que los motores funcionan con el perfil de ensayo 60 %/500 ms y que observó un pico indicado de 4 A; lo llamó pico de voltaje, pero la unidad A corresponde a corriente. No se capturó la forma de onda ni la duración del pico ni se verificó medición directa en el motor. Se conserva como resultado informado, no una caracterización completa ni certificación del driver.

Transcripción de integrado por usuario: `L298N CZOPBb17 VW CZ MAR`. No se confirmó por fotografía nueva ni se resolvieron caracteres ambiguos O/0/B/b. La referencia funcional es L298N, encapsulado Multiwatt15 según [producto oficial ST](https://www.st.com/en/motor-drivers/l298.html). No se encontró una variante de mayor corriente identificada por esa cadena completa.

Las líneas restantes son compatibles con códigos de fabricación/trazabilidad; esto es una inferencia, no descodificación oficial completa del lote. ST usa MAR para Marruecos en ejemplos de marcado de [AN926, Brand traceability](https://community.st.com/ysqtg83639/attachments/ysqtg83639/stm32-mcu-products-forum/113186/1/%5BATT%5D11502.pdf); esos ejemplos corresponden a otros encapsulados y no autorizan asignar cada carácter de este L298N. Un [moderador técnico de ST](https://community.st.com/others-hardware-and-software-57/what-does-mar-marking-mean-on-tda7294-package-151635) también identifica MAR como marcado interno relacionado con país en otro integrado. No afirmar fecha, fábrica o aumento de potencia por CZOPBb17/VW/CZ ni autenticidad del chip solo por la transcripción.

La [ficha oficial L298, DS0218 Rev 5](https://www.st.com/resource/en/datasheet/l298.pdf) publica 4 A totales del integrado. Tabla 1: por canal, máximos absolutos 2 A en continua; 2,5 A repetitivos bajo condición 80 % ON/20 % OFF con ton=10 ms; 3 A no repetitivos para t=100 ms. No trasladar esos límites a otros tiempos ni tratar máximos absolutos como corriente de trabajo garantizada para el módulo. Las pérdidas de saturación, disipación y demás componentes de la placa condicionan el uso real.

En el banco actual, ambos motores en OUT1–OUT2 comparten un único puente A. El canal B está deshabilitado: no se suman automáticamente sus capacidades. Los 4 A totales del producto no son una especificación de 4 A por OUT1–OUT2. Que gire brevemente no demuestra margen de corriente/temperatura. Si los 4 A fueron observados en la fuente, no equivalen directamente a una medida de corriente instantánea en bobinas debido al PWM/recirculación/condensadores y al muestreo del indicador; tampoco prueban otro modelo de driver.

Siguiente paso recomendado: pausar ensayos repetidos bajo esa indicación y verificar corriente por canal, duración de arranque y temperatura con instrumentación y el encargado del laboratorio; dimensionar el controlador para la pareja real. La búsqueda no cambia PWM, firmware, cableado ni estado de habilitación. No se ejecutaron movimientos desde herramientas.


## Preselección de drivers de mayor corriente

Búsqueda solicitada por usuario: [Cytron MDD10A/MDD20A, Pololu Dual VNH5019 y observaciones sobre IBT-2](drivers-mayor-corriente.md). Comparación con fuentes oficiales, corriente por canal e interfaz. Sin compra ni selección definitiva: medir cada pareja, corriente de arranque/bloqueo y requisitos de alimentación/protección antes de integrar.

## Equipo oficial confirmado el 2026-11-20

NUC con código transcrito RNUCC11PAHi30Z01. Confirmación por usuario de Ubuntu Desktop instalado y conservación de todos los datos existentes. La referencia de familia NUC11PAHi3 corresponde a Core i3-1115G4 según ASUS https://www.asus.com/gr/support/faq/1052636/ . Verificar la cadena de etiqueta, CPU real, RAM y discos desde Ubuntu antes de cerrar inventario. Acceso a cuenta pendiente. Raspberry queda como alternativa histórica.
