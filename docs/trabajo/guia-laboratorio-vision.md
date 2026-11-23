# Guia de laboratorio: app y experimento E1

Preparada 2026-11-23 para la proxima sesion del equipo. Los cambios locales de app y experimento deben subirse/sincronizarse antes de ejecutar en NUC; git pull no transfiere archivos sin commit/push.

## Antes de comenzar

- NUC conectado a alimentacion, webcamLogitech disponible, movil conectado a la red Wi-Fi que levanta el NUC. ESP/motores fuera del flujo y movimiento restringido.
- Instalar LUMI-Vision-0.8.0.apk sobre la app anterior si conserva la misma firma. No hace falta otro APK por E1.
- En la copia del repo comprobar `git status -sb` antes de actualizar. No sobrescribir archivos editados localmente ni borrar datos para resolver un pull.
- Cerrar practica.py/guiada.py y otros servidores antes de tomar camara o puerto8080. Una sola captura activa.

## 1. Comprobar la app

```bash
cd /home/lumi/Desktop/Lumi
source .venv-practica/bin/activate
python -m pip install -r software/percepcion/requirements-openvino.txt
python -m software.percepcion.servidor_movil --camara 0
```

Este arranque utiliza histograma como referencia. En app: Elegir Wi-Fi del NUC, Conectar al NUC, Enrolar persona, tocar su recuadro, Comenzar captura. Ambos pueden estar en escena separados; no cruzarse durante el giro de12s. Ver los24recortes y confirmar que sean solo del elegido. Confirmar deja Listo; iniciar seguimiento visual es una accion aparte. Verificar que Movimiento no disponible sigue deshabilitado.

Casos a comprobar: seleccionar cada persona en intentos separados; cancelar; repetir; perder seleccion durante captura debe fallar sin mezclar recortes; confirmar sin iniciar seguimiento; perder y recuperar al usuario durante seguimiento visual. Observar mensajes y FPS. Si falla conexion, comprobar http://10.42.0.1:8080/api/estado en navegador; usar la IP real del hotspot si es otra y guardarla en Direccion del NUC. Para detener servidor, Ctrl+C.

Guia completa y contrato: [enrolamiento movil](enrolamiento-movil-nuc.md). El software no crea ni modifica el punto de acceso. No enviar movimiento para comprobar red.

## 2. Ejecutar E1 con los datos anteriores

Detener el servidor anterior para medir recursos sin otra carga simultanea. Mantener el entorno activado:

```bash
python -m software.percepcion.guiada --continuar datos/enrolamientos/guiada-20261120-172419-823225 --cnn --comparar-galeria
```

No vuelve a capturar ni repetir etiquetas existentes. Guardar la ruta INFORME que imprime. Revisar informe.md, comparacion.csv y comparacion-galeria.csv: histograma contra histograma_mediana3; CNN contra cnn_reid_mediana3. Comprobar que la galeria y denominadores sean iguales y que decisiones_equivalentes siga True. No hay ganador de identidad en el piloto solo.

## 3. Captura nueva con el companero

Si app y E1 funcionan, ejecutar guiada sin --solo y sin --continuar para escenas nuevas de calibracion/evaluacion con distractor. En esa interfaz el objetivo se enrola solo en cuadro; el acompanante entra despues siguiendo indicaciones. Ver [protocolo E1](experimento-agregacion-galeria.md). No abrir guiada al mismo tiempo que servidor_movil.

Registrar condiciones de luz, ropa, altura/inclinacion de camara y fallos por detector frente a identidad. Mantener resultados anteriores y galeria24. No entrenar modelos ni aumentar recortes para este experimento. Los archivos personales permanecen en datos/, fuera de Git.

## Evidencia a traer de vuelta

Ruta de sesion movil, captura del mensaje de fallo si aparece, directorio del informe E1 y contenido de informe.md/comparacion-galeria.csv. Si hay un error de ejecucion, conservar traceback completo y comando. No hace falta transferir videos personales para la primera revision de metricas.
