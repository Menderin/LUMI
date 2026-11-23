# Banco independiente: L298N izquierdo y BTS7960 derecho

2026-11-23. Solicitud: revisar/corregir el sketch del compañero antes del flasheo. El usuario confirma un motor en OUT1-OUT2 y otro en OUT3-OUT4, mas dos motores en paralelo en M+/M- del BTS7960. ENB conserva jumper actualmente. No hay permiso para asumir ese jumper retirado ni GPIO9 conectado; verificar antes de cualquier carga con potencia.

GitHub feat/pipeline-percepcion en aa4bfe4 y tablero Trello consultados antes de implementar. Ensayo de hardware independiente; no integrar ROS ni app. El codigo previo mueve al arrancar, bloquea lectura BOOT durante6s y aplica PWM solo al canalA mientras B esta siempre habilitado.

## Propuesta acotada

Sketch Arduino separado bajo firmware/controlador/ensayo_dos_drivers/. ENB propuesto enGPIO9, libre en el sketch recibido (disponibilidad en PCB pendiente). Retirar jumperENB antes de unir GPIO y agregar pull-down10kOhm de señalENB aGND; ENA ya usaGPIO6 con jumper retirado. Nunca unir el GPIO al5V del jumper. No reutilizarGPIO5: pertenece aIN2. No tocar jumper regulador5V confundiendo su funcion conENA/ENB.

Arranque y reinicio detenidos. Habilitacion explicita por terminal serie; cada F/B solicita un pulso nuevo de500ms al60por ciento, un lado por vez, sin repeticion automatica. Intervalo minimo entre pulsos1s. BOOT cambia lado detenido y aborta/desarma si esta activo. S/espacio paran y desarman. Sin delays de segundos ni cambio de sentido durante pulso. Reiniciar, pulsar BOOT, cambiar lado o perder USB exige habilitar otra vez. BOOT no es una parada fisica certificada: depende del firmware. Requiere resistencias externas para mantenerEN bajos durante reset.

El60por ciento es un perfil de banco, no limitacion de corriente ni aprobacion del L298N. Las corrientes previas exigen caracterizar carga y arranque por canal con el responsable del laboratorio. Fuente con limitacion definida, fusibles/cableado apropiados, nada de potencia por protoboard, ruedas elevadas y corte accesible. Mantener firmware antiguo fuera de la nueva distribucion: usaba GPIO7/15/16 para otros fines.

## Comprobacion pendiente

Compilar paraESP32-S3, verificar logica con GPIO simulados, luego fuente apagada/ESP soloUSB para cargar y comprobar arranque sin habilitacion. Sin pruebas fisicas ni certificacion de corriente hasta ejecutar mediciones. No se ha flasheado nada.
