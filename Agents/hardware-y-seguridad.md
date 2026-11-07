# Hardware, actuación y seguridad

## Diseño e inventario

La base descrita tiene cuatro ruedas, cuatro motores DC y dirección diferencial por lados (skid-steer). No inferir que lleva orugas físicas. Documentar dimensiones, masa, radio de rueda y separación efectiva antes de calcular o calibrar velocidades.

Dos motores por lado no implica que cualquier puente H soporte ambos. Verificar tensión, corriente nominal y de bloqueo, disipación, protecciones y número de canales con fichas técnicas antes de seleccionar o conectar. No inventar pines, batería o límites eléctricos.

## Propuesta de protección por capas

El programa principal debe inhibir movimiento ante objetivo perdido o ambiguo y medidas inválidas. El firmware debe poder detenerse ante comunicación caducada sin depender de Python ni del detector. Parada física, rearme y estado de arranque requieren diseño y pruebas explícitas; no son funcionalidades ya implementadas.

Ensayar primero sin energizar motores, después con ruedas elevadas y finalmente a velocidad limitada en zona despejada y supervisada. Un cambio documental no autoriza energizar ni mover hardware. No iniciar movimiento físico sin que la ejecución de la prueba esté autorizada.

La propuesta por defecto ante pérdida es parar y buscar visualmente desde posición detenida. Girar o desplazarse para buscar y reanudar automáticamente requieren acuerdo específico. El objetivo de continuidad nunca anula una parada de seguridad.

Evaluar alimentación de cómputo regulada y protegida frente a transitorios de motores; separación de líneas no implica omitir masa común cuando la interfaz la requiera. Definirlo con el diseño eléctrico real.
