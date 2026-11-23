# Panel móvil de laboratorio

Abrir desde la raíz con Python 3. En el mismo equipo, ejecutar `python -m software.panel_movil.server` y abrir http://127.0.0.1:8080. La pantalla incluye el estado de prueba aunque no haya cámara.

Para el teléfono, conectar ambos equipos a una red privada de laboratorio y ejecutar:

~~~sh
python -m software.panel_movil.server --host 0.0.0.0 --camara 0
~~~

Abrir http://IP-DEL-ROBOT:8080 desde Android. Permitir el puerto en el firewall de la red privada si hace falta. El modo cámara usa OpenCV y abre un canal local. Si el dispositivo no está en el índice 0, cambiarlo. Reservar la cámara para este proceso mientras dure la prueba. El panel local no tiene autenticación. Mantenerlo en una red privada y cerrarlo al terminar.

El botón prueba la transición de enrolamiento con la máquina de estados existente. Tras diez segundos termina sin muestras, porque aún no recibe recortes del detector. La imagen es en vivo y el LED mostrado es lógico. El servidor no está conectado a GPIO, ROS 2 ni motores.

Contrato para integrar después: GET /api/estado devuelve el estado autorizado por percepción, GET /foto.jpg sirve la copia comprimida de la imagen publicada por cámara y POST /api/enrolamiento solicita al nodo de percepción iniciar una captura. Reemplazar el acceso directo a cámara por el suscriptor de ROS 2 cuando exista el nodo de cámara. El nodo de control conserva la autoridad de movimiento y el ESP32 recibe órdenes del puente serie.
## Aplicación Android nativa

Instalar el APK de laboratorio en Android 6 o posterior. Para recompilar en Windows con JDK y Android SDK ejecutar `pwsh -File software/panel_movil/android/compilar.ps1`. Si el SDK está en otra ruta, pasar `-Sdk`. El APK de prueba queda en la carpeta build. La clave de prueba también queda allí, fuera de Git.

Desde la raíz, usando el Python que tenga OpenCV instalado:

~~~powershell
python -m software.panel_movil.server --host 0.0.0.0 --camara 0 --banco-android
~~~

Conectar el teléfono a la misma red privada, ingresar `http://IP-DEL-EQUIPO:8080` y tocar Conectar. El APK usa HTTP para esta prueba en LAN. La aplicación muestra JPEG consecutivos de la cámara local. El estado de mando y enrolamiento proviene de la simulación. Mantener pulsado un botón de dirección y comprobar que el estado vuelve a parar al soltar. El servidor vence la orden tras 500 ms sin renovaciones. El enrolamiento de prueba se aprueba a los diez segundos y se puede confirmar o cancelar. Confirmarlo no activa seguimiento. ROS 2, el reconocimiento real y la telemetría del ESP32 requieren el adaptador del robot.

### Conexión desde la app horizontal

1. Tocar **Elegir Wi-Fi de LUMI** y seleccionar la red del robot en el panel de Android.
2. Volver a LUMI y tocar **Conectar al robot**. El destino inicial es 10.42.0.1:8080. Este atajo funciona si el punto de acceso se configuró con esa IP y el servidor escucha en el puerto 8080.
3. Si el servidor corre en Windows, un NUC u otra dirección, guardar su IP y puerto en **Ajustes de conexión**.

**Control manual** despliega un joystick de cuatro direcciones. Suelta el dedo o vuelve al centro para parar. **Enrolar** muestra las opciones de la sesión. Al cambiar de sección, el joystick vuelve al centro.

## Versión 0.4: motores por Wi-Fi de ESP

Consultar [banco temporal](../../hardware/conexiones/banco-wifi-motores.md). Conectar ESP · motores selecciona 192.168.4.1:8080. El modo se identifica desde la API, oculta enrolamiento/cámara y habilita solo adelante/atrás en canal A después del rearme explícito. La simulación anterior se conserva para el servidor de computador.


Banco motores vigente: app 0.5.0 y firmware protocolo 2 deben actualizarse juntos. Control UDP 8082 con ACK/tickets ESP; HTTP 8080 para estado. [Contrato y pruebas](../../docs/trabajo/banco-protocolo-v2.md). No usa MotorSessionClock V1 para órdenes.


App de banco vigente 0.5.1 compatible con firmware V2 ya cargado: prueba de enlace sin motores, indicador de gesto y ACK, solicitud de Wi-Fi de baja latencia. [Diagnóstico y prueba del móvil](../../docs/trabajo/diagnostico-joystick-enlace.md). La referencia 0.5.0 anterior registra el cambio de protocolo.


App vigente 0.6.0: [tolerancia acotada de ACK perdidos](../../docs/trabajo/tolerancia-ack-udp.md). Requiere instalar APK nuevo; firmware V2 existente compatible. No ampliar watchdog ni eliminar rearme para resolver pérdida de paquetes.


Historial **0.6.1**: [recuperación del canal y tokens retrasados](../../docs/trabajo/recuperacion-canal-datos.md). Actualizar APK, conservar firmware V2. Al volver la Wi-Fi local recupera datos automáticamente, sin rearme ni repetición del gesto anterior. Prueba inicial con fuente apagada.


La app de banco vigente es **0.7.0**. Usa [firmware protocolo 3](../../docs/trabajo/banco-protocolo-v3.md).

## Banco de vision movil en NUC (2026-11-23)

La app 0.8.0 selecciona una persona sobre video y controla enrolamiento en el NUC, que administra su Wi-Fi. Movimiento restringido tanto en app como en este servidor, sin conexion ESP/ROS de actuacion. Leer [contrato, arranque y verificacion](../../docs/trabajo/enrolamiento-movil-nuc.md). La nueva entrada es python -m software.percepcion.servidor_movil, distinta del servidor de simulacion anterior.
