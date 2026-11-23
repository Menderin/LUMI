# WebRTC nativo para NUC y Android

Estado: implementacion local; validacion NUC/telefono pendiente. Solicitud autorizada 2026-11-23: implementar WebRTC para probar video mas fluido, despues de regresion0.8.2 con picos2500ms en telefono real. No modificar modelos ni actuacion.

## Contrato de implementacion

- Unico capturador OpenCV actual alimenta IA, datos de enrolamiento y una publicacion de ultimo cuadro para WebRTC. No abrir camara dos veces. Video de prueba640x480/10FPS, sin audio, con recuadros incrustados para visualizacion.
- Backend WebRTC integrado aiortc y codecVP8 porCPU para evitar procesos MediaMTX/FFmpeg/capturas duplicados en este primer prototipo. Evaluar codificacion/CPU y latencia reales en NUC antes de adoptar. Esta version fija VP8.
- Android conserva app nativa, receptor org.webrtc con SurfaceViewRenderer. HTTP8080 para estado, enrolamiento y seÃ±alizacion; medios DTLS/SRTP porUDP negociado ICE. Sin STUN/TURN externos, operacion local sin Internet despues de instalar dependencias.
- Vista WebRTC y snapshots de seleccion son modos separados: tocar Enrolar muestra snapshots atomicos JPEG+frame_id+cajas de la API existente; no usar coordenadas de video WebRTC para seleccionar sobre cajas de otro instante. Revision24 intacta. Confirmar no inicia seguimiento.
- Mantener JPEG como alternativa explicita para diagnostico, sin migracion silenciosa que oculte un fallo WebRTC. Movimiento restringido en ambos modos, sin enviar ESP/ROS.
- Colas de video acotadas a ultimo cuadro, publicar sin esperar clientes lentos. Gestionar conexiones/cierre/reintento y registrar diagnostico de ICE/puertos. No afirmar que un timeout de lectura sea latencia total ni usar emulador como validacion del telefono.

GitHub feat/pipeline-percepcion y HU Vicente https://trello.com/c/zU5nasgb consultados. Fuentes: https://aiortc.readthedocs.io/en/latest/api.html ; https://github.com/webrtc-sdk/android . Dependencias nativas y pesos fuera de Git; conservar versiones y checksums. Validaciones de esta entrega: oferta/respuesta real, recepcion VP8, ultimo cuadro, seleccion atomica, API bloquea motores, APK nativo compilado/firmado, prueba en emulador si viable. NUC/movil reales pendientes de operador.


## Arranque en el NUC

Actualizar la rama feat/pipeline-percepcion solo despues de que el equipo publique estos cambios. Los datos locales no se borran. Detener el servidor anterior con Ctrl+C; no ejecutar dos capturadores.

```bash
cd /home/lumi/Desktop/Lumi
source .venv-practica/bin/activate
python -m pip install -r software/percepcion/requirements-webrtc.txt
python -m software.percepcion.servidor_movil --camara 0 --webrtc
```

Conserva las opciones --parametros/--metodo que se estuvieran evaluando si corresponde. Instalar dependencias requiere Internet una vez; la transmision funciona localmente. Se mantienen OpenVINO CPU, dos hilos y limite de10FPS de procesamiento. VP8 se codifica por software (aiortc usa un hilo de encoder para640x480); hay coste adicional que debe medirse en el NUC. No se usa la GPU ni se presume aceleracion H.264.

### Firewall del hotspot

En este NUC la cadena INPUT bloqueaba conexiones entrantes. Si ya existe la regla TCP8080 no duplicarla. Para WebRTC permitir tambien UDP solo desde el hotspot privado:

```bash
sudo iptables -I INPUT 1 -i wlo1 -s 10.42.0.0/24 -d 10.42.0.1 -p udp --dport 50000:50009 -j ACCEPT
```

La regla TCP que ya resolvio HTTP sigue siendo necesaria:

```bash
sudo iptables -I INPUT 1 -i wlo1 -s 10.42.0.0/24 -d 10.42.0.1 -p tcp --dport 8080 -j ACCEPT
```

Adaptar interfaz/subred solo si cambia el hotspot. Las reglas son temporales salvo que el administrador las guarde con el gestor existente. No vaciar reglas ni desactivar firewall. El loop dedicado limita binds UDP efimeros mediante create_datagram_endpoint publico de asyncio; no modifica aioice ni otros procesos. ICE anuncia direcciones locales y puertos del rango, sin STUN/TURN externo.

### App0.9.0

Instalar el APK nuevo sobre la version anterior (mismo paquete/firma). Conectar a Lumi, direccion http://10.42.0.1:8080, dejar **Video: WebRTC** y tocar Conectar. La etiqueta indica FPS recibidos/decodificados por el receptor y estado ICE; no mide latencia captura-pantalla. Estado y acciones siguen HTTP8080. La app reintenta negociacion cuando falla o deja de recibir video; no reproduce acciones de enrolamiento.

**Enrolar persona** muestra temporalmente JPEG con sus recuadros/frame_id atomicos, para que el toque seleccione a la persona de esa imagen. WebRTC se mantiene recibiendo, con render pausado. Al comenzar captura vuelve al video continuo. Revisar recortes y confirmar permanece igual; confirmar solo deja Listo, iniciar seguimiento es otra accion. Todos los controles de movimiento siguen restringidos.

El boton **Video: JPEG** desconecta y selecciona explicitamente el transporte anterior para una comparacion A/B. Pulsa Conectar otra vez. No hay fallback silencioso: si el servidor no tiene --webrtc, la pantalla lo indica. En WebRTC no se solicita el WifiLock de baja latencia agregado en0.8.2; queda enJPEG para aislar este ensayo de aquella regresion. No se ha identificado cual de los cambios de0.8.2 causo los picos.

### Diagnostico y prueba de laboratorio

```bash
curl http://127.0.0.1:8080/api/webrtc/estado
```

Sin cliente debe mostrar habilitado:true y clientes:[]; conectado debe mostrar estado:connected e ICE completed/connected. Si HTTP responde pero ICE no conecta, revisar la regla UDP y que el movil este en Lumi. Una sola conexion movil activa; una oferta nueva reemplaza la anterior para no mantener encoders abandonados.

Comparar WebRTC yJPEG durante60s cada uno, con misma escena/luz y sin enrolar. Anotar FPS NUC, FPS receptor, CPU/RAM del proceso y congelaciones. Para medir demora real, apuntar la camara a un cronometro y fotografiar a la vez original y pantalla movil; la diferencia aproxima captura-pantalla. Ni procesamiento_ms ni el GET de estado son esa demora. Despues probar seleccionar entre dos personas, capturar, revisar, confirmar sin seguimiento automatico y arrancar seguimiento aparte.

## Dependencias y recompilacion

Servidor opcional: aiortc1.14.0, aioice0.14.0, av16.1.0 en requirements-webrtc.txt. El servidor sin --webrtc no importa estas dependencias.

Android: io.github.webrtc-sdk:android:150.7871.08 desde Maven Central, SHA256 05f20dac7586b99e148258d43fb1cecb6c308a888de1621e473cc12f5e09109f. compilar.ps1 descarga/verifica el AAR en build/deps, empaqueta sus clases y librerias nativas para ARM/x86, y agrega avisos BSD/terceros y MIT de android/licenses dentro de assets/licenses. No versionar AAR/APK/cache/clave. Avisos obtenidos del repositorio webrtc-sdk/android; WEBRTC.md SHA256 d1f9382c6878ac024155fd6d44a5977329108bb8b0a01cea40e4a2f1d7de252e.

```powershell
pwsh -File software/panel_movil/android/compilar.ps1
```

## Evidencia local

- Suite Python:63 pruebas,62 correctas y1 omitida preexistente. Incluye intercambio SDP real, recepcion/decodificacion VP8 de640x480, puertos50000-50009, cuadros recientes sin repetir el anterior, cierre de sesion/hilo, API sin WebRTC responde503 y bloqueo de motores403.
- APK0.9.0 compilado y firmado con la clave de laboratorio existente. Android emulado recibio VP8 a8.5-9.2FPS con fuente sintetica10FPS; log de renderer:37/37 cuadros dibujados,0 descartes en4s (9.2FPS). No usar esta cifra como latencia ni validacion de radio.
- En Android se selecciono por toque aPersona1 entre dos candidatos, se capturaron24recortes, se abrio la revision y se confirmo: servidor devolvio Listo y movimiento_habilitado:false. Se ajusto el SurfaceView para mostrar640x480 completo con bandas, sin recortar el cuerpo. Las pruebas Java de ritmo/FPS/ultimo cuadro y mapeo de toques tambien pasaron.
- La prueba local no reproduce radio, camara ni carga real del NUC. No afirmar que desaparecieron los picos de2500ms antes de que el operador lo mida.

- Recuperacion comprobada en Android emulado: cerrar la sesion desde la API interrumpio el video; sin tocar Conectar la app negocio una sesion distinta y volvio a estado connected/ICE completed. Esto no reproduce cambiar de hotspot ni una perdida real de radio.
