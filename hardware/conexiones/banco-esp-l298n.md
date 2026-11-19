# Circuito de banco: ESP32-S3, L298N y motores de LUMI

Actualizado el 2026-11-18. [HU de hardware](https://trello.com/c/P9X0XPYL). Esquema preliminar ajustado a los componentes fotografiados. Falta validar corriente, alimentación lógica y montaje antes de energizar el conjunto.

## Componentes y estado observado

- Motor fotografiado: XD-37GB520, 12 V nominales, 30 rpm a la salida del reductor. Etiqueta del motor interior ZYTD520, 12 V, 5000 r/min, 160607/S. No confundir las dos velocidades. No hay especificación verificada de corriente nominal, bloqueo o torque. Confirmar que los cuatro motores corresponden a esta variante.
- El usuario probó el sentido y confirmó que necesita invertir los cables de dos motores. Aún falta identificar cuáles por posición del chasis.
- Módulo rojo compatible visualmente con L298N de dos canales. El marcado del integrado está oculto por el disipador. Dispone de diodos, VCC/GND/5V, ENA/ENB e IN1–IN4. La función exacta de JP1 y el modelo del regulador siguen pendientes.
- esptool 5.6.0 confirmó ESP32-S3 QFN56 revisión 0.2, 240 MHz, flash de 16 MB y PSRAM de 8 MB. USB Serial/JTAG en COM7 después de BOOT/RESET. Se respaldaron 16 MB de flash fuera de Git. El PCB parece DevKit de dos USB con adaptador de bornes; confirmar serigrafía.
- Hay fuente regulable con límite máximo de 5 A declarado por el usuario. Falta registrar modelo, tensión de cada ensayo y condición CV/CC.
- Existe código de firmware en modo banco, con potencia bloqueada, y puente ROS. La compilación y la carga están pendientes de finalizar y verificar. No se ha observado movimiento controlado desde la ESP.

## Capacidad del puente

La [ficha de ST del L298](https://www.st.com/resource/en/datasheet/l298.pdf), páginas 3 y 5, especifica 2 A DC por canal como máximo absoluto. No garantiza que el módulo soporte continuamente esa corriente. A 1 A, el chip presenta una caída total típica de 1,8 V y máxima de 3,2 V. Las entradas aceptan nivel alto a partir de 2,3 V.

El usuario aclaró que observó entre 1 y 4 A con tensión inferior a 12 V, frenando parcialmente la rueda con la mano. No son corriente nominal ni máxima a 12 V, ni una medición de bloqueo. La fuente disponible limita a 5 A. Faltan tensión exacta, duración y condición CV/CC. Evitar frenado manual en las próximas pruebas. Con esos valores, se descarta este L298N como controlador de los cuatro motores: cada pareja exigiría aproximadamente 2 A normalmente y hasta 8 A si ambos alcanzan 4 A simultáneamente. Si los cuatro consumieran simultáneamente 1 A o 4 A, sumarían 4 A o 16 A, respectivamente, sin electrónica. Estos cálculos ilustran la suma; no predicen el consumo a 12 V ni son máximos certificados. Incluso un motor por canal podría exceder el límite al alcanzar 4 A. No medir la carga combinada a través del L298N ni asumir que un segundo L298N resuelve el problema. No dimensionar usando solo la corriente sin carga. Si un motor por canal ya excede capacidad eléctrica/térmica, añadir otro L298N no resuelve esa insuficiencia. Seleccionar un driver con tensión, corriente y disipación adecuadas después de caracterizar los motores.

El esquema de cuatro motores siguiente expresa la topología deseada, no una aprobación eléctrica del módulo. Para caracterizar consumo, empezar con cada motor conectado directamente a la fuente limitada, con rueda elevada y sin driver. No avanzar a ensayos con carga mediante el L298N con los consumos declarados.

## Alimentación y masas

```text
Fuente regulable +12 V --- protección y corte --- VCC del módulo L298N
Fuente negativa -------------------------+----- GND del módulo L298N
                                         |
ESP32-S3 GND ----------------------------+

PC / Raspberry / NUC --- USB de datos/alimentación --- ESP32-S3

Lógica del L298: alimentación de 5 V según UNA de las opciones siguientes.
```

La protección, el corte y los cables se dimensionan tras conocer la corriente real. Llevar el retorno de motores directamente a la distribución de potencia, no a través de la ESP o de una protoboard. La unión de masas es para la referencia de señales.

El pin 5V del módulo no puede quedar sin resolver: la lógica necesita su alimentación. Hay dos configuraciones excluyentes, comunes en estos módulos, cuya correspondencia con JP1 debe verificarse en la placa real:

| Opción | Jumper del regulador | Pin 5V del módulo | Condición |
| --- | --- | --- | --- |
| Regulador integrado | Habilitado | Se deja sin conexión externa | Verificar regulador, jumper y que el fabricante permite 12 V de entrada. Comprobar aproximadamente 5 V en la lógica antes de conectar señales. |
| Fuente externa de lógica | Regulador deshabilitado conforme al esquema real | Entrada desde 5 V regulados externos, con masa común | Verificar que no se enfrentan dos salidas reguladas. No aplicar 12 V a este pin. |

Mantener la ESP alimentada por USB durante el banco. No unir el 5V del módulo con el 5V/3V3 de la ESP en este esquema. No conectar simultáneamente una fuente externa de 5 V y la salida del regulador habilitado.

La [documentación de SunFounder](https://docs.sunfounder.com/projects/3in1-kit-r4/en/latest/components/component_l298n_module.html) describe ambas funciones en su variante de módulo. Es una referencia para identificar el circuito, no una certificación de la placa fotografiada.

## Control desde la ESP32-S3

| GPIO ESP | Pin del módulo | Función |
| --- | --- | --- |
| 4 | IN1 | Dirección canal izquierdo |
| 5 | IN2 | Dirección canal izquierdo |
| 6 | ENA | PWM/habilitación canal izquierdo |
| 7 | IN3 | Dirección canal derecho |
| 15 | IN4 | Dirección canal derecho |
| 16 | ENB | PWM/habilitación canal derecho |
| GND | GND | Masa común |

Estos números son GPIO, no posiciones físicas del conector. Coinciden con el [firmware de banco](../../firmware/controlador/README.md). Comprobar la serigrafía del adaptador. GPIO19/20 quedan reservados para el USB nativo utilizado.

Con todo apagado, retirar los jumpers que unen ENA y ENB a 5 V antes de conectar los GPIO6/16. No confundirlos con el jumper del regulador. Añadir una resistencia de 10 kΩ entre cada EN y GND, comprobando que no queda una conexión fija a 5 V. Mantiene deshabilitado el puente mientras las salidas de la ESP no están configuradas. El software no sustituye esta condición durante reset.

## Motores por lado y polaridad

Marcar en cada motor dos terminales, A y B: al aplicar positivo a A y negativo a B, la rueda debe impulsar el robot hacia delante en su posición real del chasis. En los dos motores que necesitaron inversión, estas marcas quedarán intercambiadas respecto del color original. No se ha determinado si son ambos de un lado o están en posiciones diferentes.

Solo si el driver queda dimensionado para dos motores por canal:

```text
CANAL IZQUIERDO
OUT1 ----+---- A de motor izquierdo delantero
         +---- A de motor izquierdo trasero
OUT2 ----+---- B de motor izquierdo delantero
         +---- B de motor izquierdo trasero

CANAL DERECHO
OUT3 ----+---- A de motor derecho delantero
         +---- A de motor derecho trasero
OUT4 ----+---- B de motor derecho delantero
         +---- B de motor derecho trasero
```

Las parejas se conectan en paralelo. Cada motor usa dos salidas del puente, no una salida y GND. No unir OUT1 con OUT3 ni mezclar los canales. Para la primera prueba de canal, omitir el segundo motor de cada pareja.

| Acción | Canal izquierdo | Canal derecho |
| --- | --- | --- |
| Avance | Adelante | Adelante |
| Retroceso | Atrás | Atrás |
| Giro sobre el eje hacia la izquierda | Atrás | Adelante |
| Giro sobre el eje hacia la derecha | Adelante | Atrás |
| Deshabilitar | ENA bajo | ENB bajo |

El puente invierte electrónicamente la polaridad. Deshabilitar EN deja rueda libre, no garantiza frenado mecánico. No invertir bruscamente el sentido bajo carga.

## Primer ensayo

1. Registrar qué motores necesitan inversión y las corrientes sin carga observadas. No bloquear a mano los ejes para medir corriente.
2. Con todo apagado, revisar continuidad, masas, posición de jumpers, tensión de lógica y GPIO. Mantener potencia separada de señales.
3. Probar firmware y comunicaciones por USB sin potencia de motores. El build `banco` mantiene PWM a cero incluso tras rearme y órdenes.
4. Tras dimensionar el canal y preparar firmware con potencia para una prueba autorizada, conectar un motor, elevar ruedas y ensayar avance, parada, retroceso y desconexión del enlace. El código de banco actual no hará girar motores.
5. Evaluar carga combinada y temperatura antes de añadir el segundo motor por canal. No derivar suficiencia de una prueba de giro libre.

Para probar directamente un motor con fuente: 12 V es su valor nominal, no un rango certificado. Con salida apagada, empezar a 0 V y límite exploratorio de 0,2 A, rueda elevada, subir gradualmente sin superar 12 V en ese ensayo. Si no arranca y la fuente limita, apagar. 0,2 A no es una especificación del fabricante. La corriente ajustada en la fuente es un límite, no una corriente impuesta al motor. Hace falta ficha o caracterización supervisada para fijar otro límite.

No pasar potencia de motores por protoboard ni cables Dupont. Reservarlos para señales y componentes pequeños; usar cables y bornes dimensionados para potencia.

## Referencias para el equipo

- [ST: ficha oficial L298](https://www.st.com/resource/en/datasheet/l298.pdf). Base para límites, tabla de control y alimentación del integrado.
- [Makers Pet: ESP32 + L298N, esquemas y cableado](https://makerspet.com/blog/how-to-connect-l298n-motor-driver-to-esp32/). Ejemplo del propio fabricante de un robot diferencial. No copiar sus pines o configuración de firmware sobre LUMI.
- [Robojax: control de motores con ESP32 y L298N, vídeo](https://www.youtube.com/watch?v=Olq8NXgNySA&t=304s). Cableado desde 5:04. Referencia de montaje con otros motores y ESP32; no valida corriente ni distribución ROS de LUMI.
- [SunFounder: módulo L298N y jumper de 5 V](https://docs.sunfounder.com/projects/3in1-kit-r4/en/latest/components/component_l298n_module.html).
- [Espressif: pinout de referencia ESP32-S3 DevKitC-1](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.0.html).

Pendiente de registrar: modelo/corriente máxima de fuente, corriente de arranque/bloqueo de cada motor, función de JP1, revisión del módulo, sección de cables, protección/corte y geometría del chasis. No se eligió un fusible ni un driver alternativo sin esos datos.
