# Ensayo de dos drivers, sin ROS ni Wi-Fi

Solo para banco con ruedas elevadas. Sustituye temporalmente el firmware de la ESP; la app y los programas anteriores no controlan este ensayo. No usar el firmware viejo con esta distribucion nueva sin adaptar sus pines.

## Cableado confirmado y cambio pendiente

| Driver | Funcion | GPIO ESP32-S3 |
| --- | --- | --- |
| BTS7960 derecho, dos motores en paralelo M+/M- | RPWM / LPWM |17 /16 |
| BTS7960 | R_EN / L_EN |15 /7 |
| L298N izquierdo, motor entre OUT1-OUT2 | IN1 / IN2 / ENA |4 /5 /6 |
| L298N izquierdo, motor entre OUT3-OUT4 | IN3 / IN4 / ENB |18 /8 /9 propuesto |
| Boton BOOT | Pulsacion activaLOW |0 |

**ENB aun tiene jumper segun el operador.** Con fuente apagada: confirmarGPIO9 libre y expuesto en la placa, retirar jumperENB, identificar pin de señalENB (no el otro pin5V) y conectarlo aGPIO9. Pull-down10kOhm de señalENB aGND. Mantener ENA sin jumper con su pull-down10kOhm. Verificar polarizacion baja deR_EN/L_EN en reset con la placa BTS real; agregar pull-downs si no existen y confirmar que no haya pull-ups incompatibles. No alimentar GPIO a5V.

Fuente y retornos de motores por cables/borneras adecuados, nunca protoboard/Dupont; GND comun sin pasar corriente de motores por la ESP. ESP soloUSB para cargar, sin unir5V del driver. Fusibles, limite de corriente de fuente y consumo real por canal pendientes de caracterizacion. El software no mide ni limita corriente:60%PWM no aprueba el L298N para motores de4A. Leer [revision electrica](../../../docs/trabajo/revision-conexiones-esp32s3-dos-drivers.md).

## Compilar

PlatformIO espressif32 fijado6.12.0, Arduino-ESP32 2.0.17. El sketch usa API LEDC de2.x, no compilar sin adaptar enArduino3.x/4.x. USB Serial/JTAG activado por la configuracion del proyecto; seleccionar puerto real de la ESP.

```bash
pio run -d firmware/controlador/ensayo_dos_drivers -e ensayo
```

Solo despues de confirmar fuente de motores apagada, USB como unica alimentacion ESP y cableado revisado:

```bash
pio run -d firmware/controlador/ensayo_dos_drivers -e ensayo -t upload --upload-port COM_REAL
pio device monitor -p COM_REAL -b115200
```

Sustituir COM_REAL por puerto observado; no existe un puerto fijado para este ensayo. No se ha cargado esta version en la placa.

## Operacion por terminal serie

- Al encender/reiniciar: todo detenido y desarmado, lado derecho seleccionado. No esperar movimiento ni conectar la app.
- Enviar **?** para ayuda; **D** selecciona derecho o **I** izquierdo. Seleccionar detiene y desarma.
- Esperar al menos1s desde la ultima parada. **H** habilita logicamente el ensayo sin mover. **F** solicita un unico pulso adelante; **B** un unico pulso atras. Perfil inicial:500ms,60% (153/255),PWM1kHz/8bits. F/B no se almacenan para invertir luego.
- Al cumplir500ms, apaga PWM y deshabilita. Para otro pulso: esperar1s y enviarH yF/B otra vez. La orientacion adelante depende de las polaridades fisicas; si un motor gira contrario, parar/cortar fuente antes de corregir cableado.
- **S**, espacio o pulsar **BOOT durante el pulso**: parar y desarmar. BOOT detenido cambia el lado tras30ms antirrebote; nunca inicia movimiento. GPIO0 no debe mantenerse pulsado al reset si se desea arranque normal.
- Desconectar USB/terminal detectable porSerial provoca desarme; no sustituye corte fisico ni tiempo maximo de pulso.

Para pruebas iniciales observar un lado por vez, consumo y parada; no apoyar el robot en el suelo ni frenar ruedas con las manos. Salidas deshabilitadas permiten rueda libre, no garantizan frenado mecanico. BOOT depende del lazo de software y no es parada de emergencia certificada.

## Verificacion

Compilacion y revision del codigo no verifican corrientes, direccion real ni tiempos fisicos. Primera carga soloUSB/fuente apagada: comprobar que arranque, reinicio y ausencia de orden no generan consigna, y que el programa no pertenece al bancoWi-Fi/ROS anterior. Despues, con responsable del laboratorio, medir arranque/carga y confirmar polaridades y corte antes de ampliar tiempo oPWM.
