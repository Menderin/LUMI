# Revision electrica: ESP32-S3, L298N y BTS7960

Fecha: 2026-11-23. Revision del PDF Diagrama_Conexiones_Vehiculo_Robotico_ESP32.pdf aportado por el equipo (5 paginas), contrastado con fuentes de fabricantes. No se inspecciono el montaje fisico ni se energizo hardware. No se modifico firmware, app ni ROS. El compañero preparara codigo independiente de banco.

## Dictamen

El esquema no permite aprobar todavia el montaje completo de cuatro motores. Dibuja un solo motor en BTS7960 y omite alimentacion ESP32 y todas las conexiones de control/motores del L298N. Usuario aclara que hay dos motores por driver y ambos del nuevo modulo comparten su salida. Modelo y revision del modulo azul deben confirmarse fisicamente, no solo por el rotulo BTS7960 del PDF.

## Correcciones y condiciones

1. **Potencia fuera de protoboard.** Paginas3-5 llevan +12V y retorno de B+/B- por sus rieles, contradiciendo la advertencia de pagina5. Sustituir por borneras/distribucion y cables dimensionados para arranque. Ninguna corriente de motor debe pasar por protoboard, Dupont ni masa de la ESP. Retornos de potencia a distribucion; GND logico con referencia comun por ramal propio.
2. Fuente+12V a entrada de potencia de ambos drivers; en BTS7960 B+ positivo y B- retorno. VCC logico5V separado de potencia. M+/M- son salidas conmutadas, no masa fija. No unir las salidas de diferentes drivers.
3. Dos motores pueden compartir M+/M- en paralelo si pertenecen al mismo lado mecanico y el modulo/cableado soporta la suma de corrientes de ambos. Cada motor se conecta entre ambos bornes. Ajustar polaridad de cada motor segun avance fisico; no inferirla del color. No conectarlos en serie para repartir12V. La cifra43A del BTS7960 no certifica43A continuos de cualquier modulo.
4. **L298N sigue siendo el limite pendiente.** Maximo absoluto DC2A por canal del integrado; no corriente de trabajo garantizada del modulo. Dos motores en un solo canal suman corrientes; uno por cada canal distribuye la carga pero no elimina excesos individuales. Las medidas previas1-4A por motor y pico4A impiden aprobarlo para carga sin caracterizacion. Fuente5A total no protege individualmente cada canal.
5. Para banco, ESP por USB y GND comun; no unir ademas el5V del driver al5V/USB de la placa sin verificar el circuito de alimentacion. Nunca12V en GPIO/3V3. Salida5V del modulo rojo a VCC azul solo tras verificar jumper/regulador y tension/capacidad bajo carga. No conectar dos salidas reguladas5V entre si. Un regulador5V independiente es alternativa, no instalacion ya validada.
6. GPIO17/RPWM,16/LPWM,15/R_EN,7/L_EN son compatibles con GPIO generales del chipESP32-S3, sujetos al PCB y a no reutilizarlos para L298N. La advertencia generica GPIO6-11 reservados en ESP32 clasico no debe trasladarse al S3. En modulo azul confirmar compatibilidad real3.3V; si incorpora74HC244 alimentado5V no presumir margen garantizado como si fuese74HCT244. Identificar buffer/revision y acondicionar niveles si hace falta. R_IS/L_IS quedan sin conectar durante esta prueba; no asumir salida segura para ADC3.3V.
7. Codigo de prueba: arranque con PWM0 y habilitaciones bajas, mantener apagado durante reinicio/desconexion; comprobar polarizacion externa de EN para no flotar. Para invertir, llevarPWM a0 y dejar detener antes de invertir. Fusibles por ramal dimensionados con corriente medida y cableado; corte de potencia accesible, ruedas elevadas y limite de corriente definido antes de ensayo. No frenar ruedas con la mano.

## Pendientes para cerrar revision

- Foto nitida de ambas caras del nuevo modulo, bornes y marcado del buffer/integrados.
- Ubicacion de cada motor por lado y conexion exacta de ambos motores del L298N (uno por canal o dos en uno).
- GPIO L298N, jumpers ENA/ENB/5V y alimentacion real ESP32.
- Seccion/capacidad cables, borneras, protecciones, corriente de arranque/carga por motor y pareja.

## Fuentes primarias

- [L298: limites absolutos y canales, ST](https://www.st.com/resource/en/datasheet/l298.pdf).
- [BTS7960, Infineon](https://www.infineon.com/assets/row/public/documents/10/57/infineon-bts7960-ds-en.pdf).
- [Modulo BTS7960 de referencia, Handson](https://www.handsontec.com/dataspecs/module/BTS7960%20Motor%20Driver.pdf). Referencia de modulo, no identificacion del ejemplar del equipo.
- [GPIO ESP32-S3, Espressif](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/gpio.html).
- [74HC244/74HCT244, Nexperia](https://assets.nexperia.com/documents/data-sheet/74HC_HCT244.pdf).
