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
