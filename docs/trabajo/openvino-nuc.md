# Piloto OpenVINO en NUC

## Equipo confirmado por el usuario

Intel NUC11PAHi3 / NUC11PABi3, Core i3-1115G4 con 2 nucleos y 4 hilos, 8 GiB RAM instalados (7,41 GiB utilizables), SSD 223,57 GiB e Intel UHD integrada. Ubuntu 24.04.5 LTS, GNOME 46, kernel 6.17.0-14-generic. Camara USB Logitech C925e, 046d:085b. Al obtener el inventario habia 3,84 GiB de memoria usada, swap casi vacia y CPU a 39 C. Son datos aportados, sin benchmark de inferencia realizado.

## Implementacion y perfil inicial

Detector person-detection-0202 FP16 de Open Model Zoo, ejecutado con OpenVINO CPU. Entrada BGR float32 0..255, 1x3x512x512, resize directo segun el modelo. Salida SSD normalizada 1x1x200x7, clase persona 0. Se filtran candidatos por confianza 0,6 y se devuelve el recuadro en coordenadas de captura. Conservar HOG como alternativa de comparacion.

Se solicitan dos hilos de inferencia, un stream, modo LATENCY y CPU pinning desactivado. OpenCV usa un hilo. Es un limite de trabajadores de inferencia, no una cuota garantizada de CPU ni una reserva de nucleos para GNOME. La captura empieza a 640x480/15 FPS y la iteracion completa tiene tope solicitado de 5 Hz. Si tarda mas de 200 ms, funciona mas despacio. Inferencia sincrona, una peticion a la vez. Se solicita buffer de camara de un frame, cuyo soporte depende del backend. Las medidas locales no incluyen el tiempo interno de exposicion o buffers de la camara.

No se instala PyTorch ni se entrena en el NUC. La iGPU se deja como futura comparacion por su competencia con GNOME y drivers pendientes de validar.

## Instalacion y ejecucion

En el entorno de la practica, desde la raiz del repositorio actualizado:

```bash
source .venv-practica/bin/activate
python -m pip install -r software/percepcion/requirements-openvino.txt
python -m software.percepcion.practica --camara 0 --detector openvino --descargar-modelo
```

La descarga explicita obtiene XML y BIN del repositorio Intel 2023.0 y los conserva en modelos/pesos/person-detection-0202/, excluidos de Git. Tras la primera descarga se puede omitir --descargar-modelo. El programa registra SHA256 de ambos archivos, version OpenVINO, hilos y streams efectivos. Referencia/licencia del modelo en su repositorio oficial. Si la descarga falla, reejecutar el comando. Los archivos incompletos se eliminan.

Las teclas de enrolamiento y revision siguen en la guia de practica. Instalar por SSH es posible. Ejecutar la vista desde el escritorio del NUC.

## Medicion y decisiones del piloto

recursos.csv registra cada segundo CPU total del sistema, CPU del proceso normalizada sobre todos los procesadores logicos, RSS del proceso, RAM disponible, swap usada y temperatura maxima expuesta por los sensores. CPU total del proceso antes de normalizar puede alcanzar 400 % con cuatro hilos. La frecuencia limitada reduce trabajo entre iteraciones, sin garantizar una carga especifica.

Durante cinco minutos probar vista y escena vacia, luego persona de frente, perfiles, espalda y dos personas. Comprobar escritorio utilizable, memoria disponible estable, sin crecimiento sostenido de swap y sin avisos termicos. Si se vuelve lento, cerrar la prueba con Esc y reintentar --hilos 1 --fps-proceso 3. Registrar el cambio de perfil. Estos son ajustes de piloto y no criterios oficiales de aceptacion ni temperaturas garantizadas. Comparar tres corridas por perfil antes de recomendar.

La confianza del detector --confianza es independiente del umbral de identidad --umbral. El histograma de identidad sigue siendo experimental. Un detector mejor no garantiza evitar sustituciones.

Los AVI usan el menor entre FPS reportado y tope de proceso, pero pueden reproducirse acelerados cuando el procesamiento real es mas lento. Los tiempos reales quedan en decisiones.csv. Guardar los registros de la prueba para evaluar latencia, consumo y calidad de recuadros. La comparacion offline --video sigue siendo especifica de HOG y no implica que se haya medido OpenVINO.

## Fuentes

- https://docs.openvino.ai/2023.3/omz_models_model_person_detection_0202.html
- https://docs.openvino.ai/2024/notebooks/person-tracking-with-output.html
- https://docs.openvino.ai/2024/openvino-workflow/running-inference/inference-devices-and-modes/cpu-device.html
- https://github.com/openvinotoolkit/open_model_zoo/blob/master/models/intel/person-detection-0202/README.md

## Verificacion en el entorno de desarrollo

Se comprobaron la conversion de coordenadas normalizadas a 640x480, rechazo de clases distintas, baja confianza, NaN y cajas invertidas. Pasaron las pruebas existentes de revision, reconocimiento, grabacion y benchmark HOG. La inferencia real con los pesos Intel y las mediciones en el NUC quedan pendientes. El paquete OpenVINO se intenta instalar en un entorno local aislado; esa instalacion no constituye una prueba en el robot.

Tambien paso la prueba de una iteracion completa con camara simulada, CSV de recursos y liberacion de captura. Se tolera ausencia de contadores swap de Windows. Se omitio la prueba que requiere el runtime OpenVINO por no estar instalado al verificar.
