# Fluidez de video Android 0.8.1

Solicitud autorizada, 2026-11-23: NUC indica10FPS/33ms pero movil lento. Acercar visualizacion a10FPS antes de continuar experimentos. GitHub y HU de Vicente consultados; HU Doing.

Estado: implementado y verificado localmente; pendiente de telefono real/NUC. Mantener contrato con servidor_movil0.8.0, imagen+recuadros+frame_id atomicos y movimiento restringido. La app actual hace dos GET secuenciales y espera200ms despues: frecuencia real inferior a5FPS. Cambiar a un GET del frame (ya incorpora estado), periodo objetivo100ms contando tiempo de descarga/decodificacion, sin acumular callbacks UI ni repetir frames como si fueran nuevos. Medir frames unicos dibujados en movil, conservar FPS/proceso del NUC y mostrar tiempo de carga de imagen; no presentarlo como latencia captura-pantalla.

Criterios: mismo Wi-Fi explicito aun sin Internet, validacion de contrato en estado embebido, reconexion con espera acotada ante error, galeria/revision intactas, pruebas de ritmo de peticiones y entrega de ultimo frame, compilar/firmar APK0.8.1. No cambiar inferencia. La mejora completa requiere actualizar tambien el servidor para habilitar HTTP/1.1 persistente y TCP_NODELAY; la API JSON permanece compatible. Rendimiento fisico del telefono se mide en laboratorio.

## Hallazgo durante verificacion

El primer ajuste de ritmo por si solo no alcanzo10FPS en el emulador: se observaron1.9FPS y carga aproximada530ms. Instrumentacion separada mostro cabeceras515-542ms y cuerpo8-45ms; la respuesta local en PC tardo aproximadamente15ms para18.7KB. Se identifico coste recurrente de peticiones nuevas, no JSON ni inferencia, en este ensayo. No extrapolar estos tiempos al telefono del usuario.

Se habilito HTTP/1.1 con Content-Length ya existente y TCP_NODELAY en el servidor. Android deja disponibles para reutilizacion las conexiones cuyo cuerpo ya leyo/cerró; solo fuerza disconnect en respuestas incompletas. Conserva el mismo objeto Network cuando sigue siendo la misma Wi-Fi para mantener su pool, sin pasar a datos moviles. Ante cambio de red o error vuelve a seleccionar Wi-Fi y reconecta. El servidor cierra conexiones inactivas tras10s y conexiones de POST rechazadas sin cuerpo consumido.

La captura y reconocimiento siguen a10FPS; no se han aumentado hilos, resolucion ni carga de inferencia. El movimiento permanece restringido.

## Resultado de la prueba sintetica

Con Android emulado y servidor de cuadros sinteticos, tras HTTP persistente se observaron9.4FPS unicos dibujados y carga9ms en la captura de pantalla. Logs en regimen: cabeceras3-6ms, cuerpo3-8ms, JSON0ms redondeado; primera conexion512ms de cabeceras. La mejora observada corresponde a esta configuracion local: no garantiza iguales FPS en la red y movil fisicos. La pantalla se inspecciono visualmente con metricas NUC/App separadas, sin superposiciones de texto y recuadros sobre la misma imagen. La accion Enrolar se recibio en el servidor y el movimiento permanecio deshabilitado; la seleccion completa ya estaba cubierta por las pruebas de banco y geometria.

Pruebas Java pasadas: periodo100ms descontando carga, sin espera adicional si se excede presupuesto; espera de reintento; conteo de cuadros unicos dibujados (no contar redibujos/repetidos), caducidad de ventana FPS; entrega de ultimo resultado cuando UI se retrasa; geometria FIT_CENTER. Cuatro pruebas Python de banco movil pasaron, incluida conexion HTTP/1.1 reutilizada sobre el mismo socket y bloqueo de movimiento. APK compilado y firma verificada.

## Actualizar y probar en laboratorio

1. Instalar LUMI-Vision-0.8.1.apk encima de0.8.0 (misma firma). Conserva direccion del NUC guardada, puerto8080 y flujo de enrolamiento.
2. Subir/sincronizar los cambios del repositorio, incluidos servidor_movil.py y archivos Android. Detener el servidor anterior con Ctrl+C; iniciar otra vez con el mismo comando:

```bash
cd /home/lumi/Desktop/Lumi
source .venv-practica/bin/activate
python -m software.percepcion.servidor_movil --camara 0
```

3. Conectar app al Wi-Fi del NUC y http://10.42.0.1:8080 (o IP real). Mantener la regla de firewall que ya se verifico en laboratorio. No requiere Internet ni cambios de puertos, pesos, firmware o permisos de motores.
4. Leer NUC FPS/proceso frente a App FPS/Carga. App FPS cuenta imagenes distintas dibujadas en ventana2s. Carga incluye peticion HTTP y decodificacion de la imagen; no mide captura-pantalla ni movimiento fisico. Esperar2s para estabilizar indicador. La cifra App puede quedar por debajo de10 por enlace, telefono o fuente.
5. Probar tocar recuadro, ver recortes y confirmar; movimiento sigue deshabilitado. Si Carga se aproxima o supera100ms, registrar sus valores para localizar el limite restante.

La app optimizada conserva compatibilidad de API con servidor anterior, pero sin actualizarlo se siguen cerrando conexiones por cuadro y la mejora puede ser insuficiente. Primera conexion/reconexion puede ser mas lenta que las siguientes; el ajuste reduce coste repetido, no promete eliminar el de arranque.

## Revision de picos y banda Wi-Fi, 2026-11-23

Usuario observa retrasos esporadicos, luego estabilizacion. La banda fisica del hotspot no se ha medido desde este chat. Ejecutar en NUC `iw dev wlo1 info` para canal/frecuencia y `sudo iw dev wlo1 station dump` para clientes, senal, tasas y retransmisiones. Estas consultas no cambian la conexion. Anotar App FPS/Carga y NUC FPS/ms en estable y durante pico, y si ocurre al capturar/confirmar o durante seguimiento normal.

Hardware AX201 soporta2.4/5GHz como radio segun Intel, pero iwlwifi documenta AP2.4 sin soporte AP5GHz en iwlmvm por LAR. No asumir que `nmcli ... band a` habilita un hotspot5GHz; puede fallar. Primero comprobar capacidades/regulacion reales; no cambiar region ni forzar canales prohibidos. Un router/AP5GHz existente con ambos equipos como clientes permitiria comparar radio sin exigir al Intel actuar como AP5GHz. Es una opcion de prueba si esta disponible, no una compra propuesta ni nueva arquitectura aceptada.

Fuentes: https://www.intel.com/content/www/us/en/products/sku/130293/intel-wifi-6-ax201-gig/specifications.html ; https://wireless.docs.kernel.org/en/latest/en/users/drivers/iwlwifi.html ; https://networkmanager.dev/docs/api/1.44.4/nm-settings-nmcli.html (powersave2 deshabilita ahorro, previo a considerar ajustes reales del perfil).

Hallazgos de codigo y propuestas aun NO implementadas:

- La llamada BancoVision.procesar corre bajo banco.lock; extraer video y confirmar/crear identificadores ocurren en ese flujo. GET frame adquiere el mismo lock: puede esperar durante esos trabajos. Separar trabajo pesado/publicacion es una mejora candidata, con estados ocupados explicitos y pruebas de concurrencia. No atribuir esos picos automaticamente a Wi-Fi.
- Android readTimeout5000ms puede dejar una carga de imagen en curso varios segundos. El buzon de ultimo frame evita acumular cuadros ya recibidos pero no interrumpe la transferencia TCP en curso. Evaluar descarte por antiguedad/presupuesto total del cuadro, diferenciando conexion inicial de regimen para evitar reconexiones perpetuas.
- JPEG via base64 agrega aproximadamente un tercio de bytes frente al JPEG binario, mas JSON. Proponer JPEG binario/multipart con metadatos del MISMO frame_id, conservando seleccion atomica. No cambiar a MJPEG separado con cajas de otro instante ni migrar a WebRTC/UDP antes de medir necesidad.
- Permitir calidad JPEG de visualizacion ajustable (referencia actual75) y comparar75 frente60 sin cambiar resolucion ni datos de reconocimiento. Galeria24 y videos de entrenamiento/evaluacion conservarian calidad de origen; no mezclar esta variable con resultados de identidad.
- Comparar canal menos ocupado y ahorro de energia del enlace con configuracion registrada, despues de inspeccionar el perfil activo; no modificarlo automaticamente desde este codigo.

Prioridad: medir picos y contexto; abordar bloqueo de publicacion si coincide con captura/confirmacion; si sube Carga mientras NUC sigue estable y hay reintentos Wi-Fi, probar condiciones de radio/menor carga de bytes. La medicion actual Carga no equivale a latencia captura-pantalla. No se instalaron modelos, alteraron motores ni cambiaron hotspot/firewall durante esta revision.

## Medicion real del enlace aportada por operador

2026-11-23, NUC hotspot Lumi, wlo1 tipoAP: canal1,2412MHz,20MHz. Cliente asociado22s; senal instantanea-36dBm, media-51dBm; txbitrate72.2Mbit/s; rxbitrate1Mbit/s; txbytes7521423, txpackets860, txretries2, txfailed0, rxdropmisc0. Se omite MAC de cliente.

Interpretacion: banda2.4confirmada, senal favorable y muy pocas retransmisiones observadas en esta ventana. El contador TX desde NUC es la direccion relevante del video; RX1Mbit/s no representa la capacidad global de transferencia del video y puede corresponder a la ultima recepcion de un paquete lento. Las tasas de enlace no son rendimiento util de aplicacion. Aproximadamente2.7Mbit/s medios TX en22s si el intervalo de contadores coincide con tiempo de asociacion; no usarlo como medicion exacta de la carga JPEG ni de picos. No demuestra ausencia de interferencias intermitentes.

Prioridad: medir Carga/NUC durante los picos y desacoplar trabajo pesado del candado de publicacion, antes de cambiar hardware/banda. Esta medicion no justifica por si sola migrar a5GHz ni reducir precision/resolucion de reconocimiento.

## Iteracion0.8.2: retraso en vista normal, sin enrolamiento

El operador aclara que los picos ocurren en vista normal y no probo enrolamiento: en ese ensayo se descarta el trabajo pesado de galeria como causa directa. Preparar ajuste de transporte manteniendo detector10FPS y controles restringidos.

Implementacion prevista: reutilizar ControlWifiPower (baja latencia Android29+, alto rendimiento anteriores) solo mientras conectado y en primer plano; nuevo endpoint frame.jpg con JPEG binario y metadatos ASCII JSON en cabecera del MISMO cuadro; API JSON anterior conservada; app detecta404 y vuelve al formato previo si servidor no actualizado. Reducir espera de lectura de video frente a5s, dejando el tiempo de ordenes separado. Validar JPEG/metadata atomicos, conexion persistente, fallback y geometria. No prometer eliminar picos ni medir efecto radio con emulador. Fuente Android: https://developer.android.com/reference/android/net/wifi/WifiManager#WIFI_MODE_FULL_LOW_LATENCY y https://source.android.com/docs/core/connect/wifi-low-latency . GitHub y HU consultados antes de modificar.

### Uso de0.8.2

Instalar LUMI-Vision-0.8.2.apk sobre0.8.1. Reutiliza mismo paquete, firma, direccion y puerto. Actualizar servidor_movil.py en NUC y reiniciar con el mismo comando para obtener JPEG binario. La app comprueba primero GET /api/vision/frame.jpg: recibe image/jpeg y X-Lumi-Metadata (JSON ASCII, estado y frame_id del mismo JPEG). El servidor mantiene GET /api/vision/frame JSON/base64 para clientes anteriores. Si frame.jpg responde404, la app cambia una vez al formato anterior durante esa conexion.

En la pantalla aparece JPEG binario o JPEG/JSON y Baja latencia solicitada / Alto rendimiento solicitado / no disponible. Solicitado no garantiza que firmware/hardware apliquen el modo: solo indica que Android acepto el WifiLock. Se libera al desconectar, mandar la app al fondo o destruir la actividad; no cambia ajustes globales ni banda/canal. Puede consumir mas energia durante uso activo; en esta pantalla la app ya mantiene pantalla encendida.

El timeout de lectura de imagen pasa de5s a1.2s; conexion inicial sigue con2s, ordenes/revision con5s. Este es un timeout de lectura, no una garantia de latencia total ni un descarte completo por antiguedad. La conexion puede reintentarse si se atasca, sin reproducir ordenes. Todavia no se ha implementado un timestamp de sensor ni medido captura-pantalla real.

El JPEG entregado es identico al que codifica el servidor para JSON, calidad75 y640x480: cambia envoltorio de transporte, no camara, modelo, datos guardados ni resolucion. El cuerpo JPEG binario es aproximadamente25por ciento menor que su representacion base64; cabeceras y metadatos tambien consumen bytes y deben contarse al medir trafico total. En el servidor actual se conserva base64 para compatibilidad y se decodifica al servir binario; no se presume ahorro de CPU del NUC. El movil evita decodificar base64 y elimina payload JPEG de la metadata retenida tras crear Bitmap.

### Evidencia0.8.2

Cuatro pruebas Python del banco pasaron: los bytes JPEG son iguales a los del endpoint anterior, metadata conserva frame_id/cajas y no incluye payload base64, y HTTP persistente/movimiento bloqueado se mantienen. APK compilado, firma v1/v2/v3 verificada, versionCode17.

En emulador, JPEG binario mostro9.4FPS dibujados, carga7ms en captura de pantalla, cuerpo aproximado13.6KB frente18.7KB del JSON previo en datos sinteticos comparables (incluye diferencia de metadatos en envoltorio). Logs en regimen: cabeceras3-5ms, cuerpo0-5ms, JSON0-1ms redondeados. Pantalla indico Baja latencia solicitada; no mide el efecto radio de ese modo. Se comprobo tambien fallback automatico al volver a servidor simulado sin frame.jpg: imagen visible y formato JPEG/JSON. Camara, red y telefono reales pendientes; no se afirma que se hayan eliminado los picos del usuario.

## Regresion fisica0.8.2 y alternativa propuesta

Operador reporta picos peores de hasta2500ms en vista normal. La mejora sintetica no reprodujo el telefono/red reales; no considerar0.8.2 una mejora validada ni atribuir los picos a la banda. Se cambiaron simultaneamente modo Wi-Fi, envoltorio de imagen y timeout: la causa no queda aislada. Si2500ms corresponde a Carga, es tiempo de peticion/recepcion/decodificacion, no latencia captura-pantalla ni tiempo del detector. El timeout de lectura1200ms no es plazo total; conectarse tiene otro timeout, y lectura por tramos/pool/reconexion pueden acumular mas tiempo. La app invalida Network ante todo fallo, lo que tambien pierde reutilizacion y puede aumentar coste de reconectar. Hay que separar reconexion de red de fallo de un frame en una comparacion controlada.

Evaluacion de siguiente transporte (propuesta, sin implementar):

- WebRTC video local via MediaMTX/encoder: candidato principal para una solucion de video tiempo real con manejo de jitter/congestion y decodificacion de video en Android. No garantiza latencias concretas. Preferir transporte de medios UDP en LAN y colas acotadas; verificar encoder disponible y costeCPU en NUC. App seguiria nativa con receptor WebRTC, no Electron/webapp.
- RTP/UDP con GStreamer: candidato de banco para controlar latencia de jitterbuffer y descartar tarde. Requiere integracion nativa Android, codec y recuperacion de perdidas; no enviar JPEG gigante en un datagramaUDP.
- MJPEG continuo HTTP: migracion mas simple de JPEG por peticion a un flujo; conserva TCP y no elimina bloqueos por retransmisiones. No presentarlo como solucion garantizada a picos.

Arquitectura de prueba propuesta: un solo productor de camara alimenta detector actual y encoder de visualizacion; no abrir Logitech desde dos procesos. Empezar640x480/10FPS sin audio, medir CPU y captura-pantalla con referencia visual independiente. Control de enrolamiento/estado permanece HTTP8080 y movimiento restringido. La seleccion de persona debe conservar imagen y cajas del mismo instante: para primer prototipo WebRTC, mostrar recuadros incrustados en el video y usar snapshot atomico al entrar en seleccion, o alinear metadatos con timestamps reales de video; no superponer cajas actuales sobre video retrasado. Mantener revision de24recortes y galeria fija.

WebRTC local no requiere inferencia en Internet, pero cambia puertos de medios/senalizacion y hay que definir excepciones del firewall del NUC antes de probar. No recomendar abrir todo UDP ni desactivar firewall. Implementacion y eleccion definitiva pendientes: primero describir pipeline/codec/cliente concretos y prueba A/B en mismo telefono/NUC. Conservar0.8.1 como referencia de comportamiento; Android no permite instalar sin mas un APK con versionCode inferior sobre el actual, asi que una comparacion requiere un build de diagnostico con versionCode nuevo o un procedimiento explicito, no aconsejar downgrade directo.

Fuentes primarias consultadas: https://mediamtx.org/docs/read/web-browsers ; https://mediamtx.org/docs/read/webrtc ; https://gstreamer.freedesktop.org/documentation/rtpmanager/rtpjitterbuffer.html . No se implemento ni verifico WebRTC/RTP en esta revision.


La propuesta anterior queda implementada para probar en [WebRTC nativo0.9.0](webrtc-movil-nuc.md). Se eligio aiortc integrado en lugar de MediaMTX para compartir la captura existente. Mantener el reporte fisico de0.8.2 como regresion sin causa aislada.
