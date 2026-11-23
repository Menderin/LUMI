# Enrolamiento seleccionado desde Android y NUC

Estado: implementado y verificado con datos sinteticos y emulador; pendiente de prueba real movil/NUC. Autorizacion del usuario 2026-11-23: implementar seleccion sobre video en app; NUC levanta Wi-Fi; movimiento restringido.

## Contrato y alcance

- NUC posee camara, detector, seleccion temporal, captura de 12 segundos, 24 recortes, revision y galeria. Reutilizar modulos existentes, sin ROS/ESP/motores en este servidor.
- Android nativo horizontal: video a la izquierda, acciones en barra lateral; conexion Wi-Fi del NUC, enrolar despliega pasos, tocar recuadro selecciona persona. Movimiento visible como no disponible, sin peticiones de movimiento. Referencia visual: pantalla nativa ya existente, conservar paleta y distribucion. Mostrar carga, desconexion, seleccion, captura, revision, error y listo sin depender solo de colores.
- Snapshot atomico imagen+frame_id+cajas. Toque refiere a ese frame, caduca, se comprueba contra la escena actual. Seguimiento IoU conservador de seleccion; al perderla o superponerse personas se cancela captura. Esto no garantiza identidad en cruces y exige revision humana de los recortes.
- Sesion compartida: cuenta regresiva 3 segundos, intento maximo cinco, captura 12 segundos, extraccion hasta24 con minimo20, revision manual antes de aprobar. Confirmar solo deja Listo. Seguimiento exclusivamente visual con accion separada y reencuentro.
- API HTTP local versionada; JPEG en JSON junto a recuadros para evitar seleccionar sobre otro fotograma. Android usa especificamente la red Wi-Fi aunque no tenga internet. NUC no necesita internet para operar con pesos descargados. No crear ni alterar hotspot automaticamente.
- Conservar video original, metadatos con seleccion y recortes en datos/enrolamientos; datos fuera de Git. No publicar APK ni datos automaticamente.

GitHub feat/pipeline-percepcion y HU https://trello.com/c/zU5nasgb consultados; HU en Doing. La app y este servidor constituyen banco de vision, no integracion de movimiento ni aceptacion final del robot.

## Verificacion prevista

Pruebas de toque caducado, candidato inexistente, coordenadas/letterbox Android, ambiguedad, perdida, captura multpersona seleccionada, confirmacion y movimiento denegado por servidor. Compilar APK con firma local existente y verificar; camara y movil reales pendientes de operador.

## Arranque en el NUC

El NUC ya administra el punto de acceso Wi-Fi, segun el operador. Este servicio utiliza esa red y no configura ni cambia NetworkManager. Cerrar la practica de camara anterior y cualquier servidor previo que ocupe el puerto 8080. No ejecutar dos capturadores sobre la Logitech.

Despues de sincronizar esta version de feat/pipeline-percepcion:

```bash
cd /home/lumi/Desktop/Lumi
source .venv-practica/bin/activate
python -m pip install -r software/percepcion/requirements-openvino.txt
python -m software.percepcion.servidor_movil --camara 0 --host 0.0.0.0
```

Por defecto, detector OpenVINO person-detection-0202 y reconocimiento por histograma, con umbral provisional .45 y margen .08. Dos hilos CPU y tope de proceso 10 FPS, camara solicitada 640x480 a15. Agregar --descargar-modelo si faltan los pesos del detector. Puede ejecutarse por SSH porque no abre ventanas.

Para comprobar CNN con parametros de la ultima bateria:

```bash
python -m software.percepcion.servidor_movil --camara 0 --metodo cnn_reid --parametros auto
```

Agregar --descargar-cnn si faltan sus pesos. Las reglas de importacion y transferencia de umbrales son las de [CNN Re-ID](cnn-reid.md): un nuevo enrolamiento no queda validado automaticamente por un umbral anterior. Para histograma tambien puede usarse --parametros auto.

## Android 0.8.0

La actividad de inicio pasa a VisionActivity. MainActivity del banco ESP permanece como historial de codigo sin actividad registrada: no se puede iniciar desde esta version. El boton de movimiento esta deshabilitado, no hay joystick ni habilitacion de canales. No se usa UDP ni se envian ordenes a ESP. Mismo paquete cl.lumi.panel y versionCode15; instalar sobre la anterior si esta firmada con la misma clave local. Solo se transfiere el APK, no idsig ni archivos de compilacion.

1. Instalar LUMI-Vision-0.8.0.apk. Elegir Wi-Fi del NUC abre los ajustes de Android; seleccionar la red del NUC y regresar.
2. Conectar al NUC usa http://10.42.0.1:8080 inicialmente. Si el hotspot tiene otra IP, cambiarla en Direccion del NUC (consultar `ip -4 addr` en Ubuntu). El nombre de red no determina su direccion IP. HTTP se vincula especificamente a Wi-Fi, aunque Android tenga datos moviles activos.
3. Enrolar persona despliega acciones y prepara seleccion. Tocar dentro del recuadro deseado; tambien hay Seleccionar por numero como alternativa. Las personas deben mantenerse separadas durante todo el giro.
4. Comenzar captura inicia tres segundos de preparacion y doce de giro pausado. Puede haber otra persona en el encuadre, pero no debe cruzarse ni superponerse con la elegida.
5. Ver recortes muestra la hoja numerada de hasta24. Revisar que TODOS sean de la persona elegida y que cubran frente, espalda y perfiles. Solo despues se habilita Confirmar enrolamiento. Nuevo enrolamiento descarta la seleccion/galeria activa y vuelve a seleccionar; Cancelar vuelve a espera.
6. Confirmar deja Listo. Iniciar seguimiento visual es otra accion. Si se pierde al objetivo, el banco sigue intentando reconocer y requiere tres coincidencias para recuperarlo; esto sigue siendo simulacion sin motores.

La vista Android solicita snapshots como maximo aproximadamente5 por segundo, sin colas de cuadros ni consultas simultaneas del mismo lector. No implica que detector/identificador corran a5 FPS: en NUC el limite sigue en10. Imagen, cajas y frame_id llegan en la misma respuesta, se dibujan con la misma transformacion FIT_CENTER. El toque en bandas negras se ignora. Los indices Persona1/2 son propios de cada fotograma, no identidades permanentes.

Al perder la red la pantalla invalida la imagen y deshabilita acciones; reintenta automaticamente y vuelve a recibir el estado del NUC cuando regresa el servicio. No reenvia comandos anteriores. Al mandar la app al fondo se desconecta el cliente; la captura del NUC puede continuar y al reconectar se consulta su estado. Si el NUC pierde la camara, no sirve la imagen congelada como activa. Verificar `/api/estado` en el navegador del movil si hay problemas de direccion/puerto; en una red de laboratorio mantener el servicio solo en la LAN del robot. Este banco HTTP no incluye autenticacion.

## Estado y API

| Ruta | Metodo | Funcion |
| --- | --- | --- |
| /api/estado | GET | Contrato lumi-vision-nuc-v1, fase, mensaje, metodo, FPS y movimiento_habilitado=false |
| /api/vision/frame | GET | JPEG base64, dimensiones, frame_id, cajas, seleccionado, objetivo reconocido y distancias |
| /api/vision/revision | GET | Hoja numerada de recortes aprobables |
| /api/vision/seleccionar | POST | frame_id y candidato entero de la imagen mostrada |
| /api/enrolamiento | POST | accion: iniciar, capturar, confirmar, cancelar, repetir, iniciar_seguimiento o reanudar |
| Cualquier otra ruta de orden | POST | 403, movimiento restringido |

El toque caduca en1.5s y las peticiones en cola tambien caducan antes de ejecutarse. No se cambia la seleccion durante captura. En seguimiento el reconocimiento usa galeria fija y no depende del indice previo del detector.

IoU de seleccion >=.30, margen entre asociaciones >=.15 y rechazo de superposicion si interseccion/area menor >.15. Son valores iniciales conservadores de este banco, no criterios validados. Una perdida durante preparacion o captura hace fallar el intento: no se adquiere automaticamente otra persona. IoU por si solo no garantiza identidad si dos personas intercambian lugar entre cuadros; la separacion fisica y revision humana siguen siendo necesarias. No es una implementacion de identidad robusta en cruces.

## Datos y responsabilidades

Sesion nueva en datos/enrolamientos/movil-FECHA/, excluida de Git. Conserva enrolamiento-N.avi, .captura.json (recuadro seleccionado y todos los de la escena), .extraccion.json, galeria-N/PNG y representaciones, configuracion.json, decisiones-movil.jsonl, acciones-movil.json y acciones.json. El video contiene la escena completa; solo el recuadro seleccionado entra a extraccion. Los intentos fallidos conservan su video de diagnostico sin crear galeria aprobada. Los logs moviles no sustituyen las anotaciones de calibracion/evaluacion del banco offline. Los videos se guardan para revision posterior; esta app muestra la hoja de recortes, no un reproductor de video grabado.

La ESP no participa en este servicio. ROS sigue siendo la integracion futura del robot; este adaptador HTTP es la interfaz de laboratorio del NUC con la app y no publica ordenes ROS ni controla pines.

## Evidencia, 2026-11-23

- GitHub y HU de Vicente consultados; HU Doing. Sin cambios remotos de gestion.
- 58 pruebas Python pasaron con pesos CNN reales disponibles, incluidos seleccion entre dos, cambio de orden de detecciones, recortes solo del elegido, perdida/ambiguedad, caducidad, confirmacion separada y endpoint de movimiento403.
- Geometria Java FrameMapping verificada con imagen letterbox horizontal/vertical y toque en bandas.
- APK compilado y firma verificada con Android SDK/JDK locales. Prueba en emulador API37: conexion por Wi-Fi, video atomico, toque selecciona, captura habilitada solo al seleccionar, captura de12s, hoja de24 y confirmacion recibida por NUC simulado dejando Listo. Margenes de barras Android corregidos tras inspeccion visual.
- Fallo inicial de prueba HTTP por restriccion local de sockets: repetida con acceso permitido, paso. No es fallo de la API.
- No habia movil fisico conectado al PC. Pendiente: instalar APK en el telefono, ejecutar servidor en NUC con Logitech, comprobar ambas personas separadas, fallar intento al cruzarse y verificar recursos reales. No se ha cambiado Wi-Fi, firmware ni motores de equipos reales.

Comprobacion final de interfaz: APK final instalado en emulador, barras Android sin tapar contenido; recuperacion automatica al reiniciar servidor sintetico observada (vuelve a espera y muestra ambas personas). Firma v1/v2/v3 verificada; paquete cl.lumi.panel versionCode15, actividad de inicio VisionActivity.
