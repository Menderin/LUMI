# Drivers de mayor corriente para LUMI

Consulta: 2026-11-19. Preselección técnica; no compra ni integración aprobada. Arquitectura Raspberry/ROS 2 → USB → ESP se conserva.

## Criterio de selección

Cuatro motores DC 12 V, dos por lado. Se necesitan dos canales bidireccionales si cada pareja se conecta en paralelo y cumple la corriente conjunta admisible; cuatro canales si se controla cada motor individualmente. La corriente por canal debe dimensionarse con la suma de ambos motores, tanto en régimen como arranque y bloqueo, contemplando duración y temperatura. El pico de 4 A indicado por la fuente durante el ensayo no es una medida verificada de bobinado ni demuestra la corriente de bloqueo.

Comparar módulos completos con corriente documentada, no solo amperios del transistor. Entrada lógica compatible con ESP 3,3 V, corriente continua y transitoria con duración, protecciones, disipación, fusibles/cableado, alimentación y disponibilidad local. No se verificaron precios finales ni disponibilidad en Chile.

## Opciones con documentación del fabricante

| Módulo | Alimentación de motor | Canales | Corriente anunciada por canal | Interfaz y ventajas | Condiciones |
| --- | --- | --- | --- | --- | --- |
| [Cytron MDD10A Rev2](https://my.cytron.io/p-10amp-5v-30v-dc-motor-driver-2-channels) | 5–30 V | 2 | 10 A continua; 30 A pico hasta 10 s | PWM/DIR, lógica 3,3/5 V, PWM hasta 20 kHz | Confirmar Rev2; original anterior limitada a 25 V. No protección de polaridad inversa. No atribuirle las protecciones activas del MDD20A. |
| [Cytron MDD20A](https://my.cytron.io/p-20amp-6v-30v-dc-motor-driver-2-channels) | 6–30 V | 2 | 20 A continua; 60 A pico | PWM/DIR, lógica 1,8/3,3/5/12 V, PWM hasta 20 kHz; protección de sobrecorriente con limitación activa, temperatura y subtensión | No se verificó aquí duración admisible del pico de 60 A: no usarlo como corriente sostenida. No protección de polaridad inversa. El límite del driver no equivale a protección específica de cada motor. |
| [Pololu Dual VNH5019, producto 2507](https://www.pololu.com/product/2507) | 5,5–24 V | 2 | Hasta 12 A continua y 30 A pico | Compatible con señales 3,3 V; corriente analógica aprox. 140 mV/A; PWM hasta 20 kHz; protecciones de temperatura, tensión y cortocircuito según guía | La [guía](https://www.pololu.com/docs/0J49/all) explicita dependencia de refrigeración y duración real: 12 A unos cinco minutos en su muestra, no promesa para todo montaje. La interfaz de lectura de corriente requiere revisar el máximo admisible del ADC ESP. Arduino no es obligatorio para controlar esta placa. |

Los valores son especificaciones del fabricante y no aceptación experimental para los cuatro motores LUMI. Todos admiten 12 V de alimentación nominal; falta considerar regeneración/transitorios y capacidad de la fuente para el sistema completo.

## Recomendación preliminar

Preseleccionar MDD20A por margen y protecciones, y MDD10A como alternativa de menor margen que debe evaluarse con corriente real y cotización. Pololu Dual VNH5019 interesa cuando la medida de corriente resulta prioritaria. Una placa dual puede gestionar un lado por canal y dos motores por lado solamente si la demanda conjunta entra en su capacidad y las protecciones están dimensionadas. La compra queda pendiente de presupuesto y medidas, no se garantiza suficiencia por el nombre del producto.

No son sustituciones de cableado a ciegas: revisar tabla de control, apagado/parada, alimentación lógica y estados de arranque; adaptar firmware antes de conectar. Para Cytron, documentar PWM/DIR frente a IN1/IN2/ENA actual. Elegir driver más potente no resuelve por sí mismo batería/fuente, protección de motor, cableado, corte y distribución de corriente.

## BTS7960 / IBT-2

Alternativa a investigar si se presenta un módulo concreto con proveedor/esquema. [Infineon BTS7960](https://www.infineon.com/dgdl/Infineon-BTS7960-DS-v01_01-en.pdf?fileId=db3a304412b407950112b43945006d5d) es un semipuente, no una placa dual completa. Los módulos IBT-2 suelen formar un puente con dos semipuentes: no asumir dos canales independientes. El número comercial 43 A está relacionado con características del integrado/protección y no certifica 43 A continuos en cualquier placa genérica. Validar chips, buffer lógico (3,3 V), pistas, bornes y disipación de la unidad real. No se le asigna aquí una corriente continua del módulo sin documentación.

## Estado de ensayo actual

Usuario pidió pasar el máximo de pulso de 0,5 s a 5 s conservando 60 % y citó ensayos anteriores. Se preparó y compiló el cambio a BANK_MAX_PULSE_MS=5000; no implica que L298N haya sido dimensionado para 4 A en el único puente activo. Rearme y watchdog de 250 ms desde recepción válida siguen vigentes; 5 s es un máximo mientras se mantiene el mando con renovaciones, no movimiento automático de cinco segundos. Carga y arranque deben registrarse en el documento del ensayo, sin confundir build con actuación física.
