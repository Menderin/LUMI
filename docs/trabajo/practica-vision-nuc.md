# Práctica de cámara y reconocimiento en el NUC

La práctica abre la Logitech en Ubuntu Desktop y dibuja recuadros de personas con HOG. El seguimiento se muestra en pantalla. La referencia de identidad es una galería de recortes de la sesión, comparados por histograma HSV y distancia de Bhattacharyya.

## Preparación en Ubuntu

Comprueba el sistema y Git con `cat /etc/os-release` y `git --version`. Si faltan paquetes, `sudo apt update` actualiza el índice y `sudo apt install git python3-venv v4l-utils` instala Git, la herramienta de entornos Python y el inventario de cámara.

Si aún no existe una copia en tu carpeta personal, `git clone https://github.com/Menderin/LUMI.git ~/LUMI` la crea. Si ya existe, usa `git status -sb` y `git remote -v` para revisar su estado y origen antes de actualizarla. Selecciona la revisión que incluya la práctica.

Conecta la cámara. `v4l2-ctl --list-devices` lista sus nodos y `v4l2-ctl -d /dev/video0 --list-formats-ext` lista los formatos del nodo 0. Sustituye el número si corresponde. Cierra otras aplicaciones que estén usando la cámara.

Desde la raíz del repo:

```bash
python3 -m venv .venv-practica
source .venv-practica/bin/activate
python -m pip install -r software/percepcion/requirements-practica.txt
python -m software.percepcion.practica --camara 0
```

Usa un entorno aparte del banco sin interfaz, porque los dos paquetes OpenCV comparten el módulo cv2. Si el nodo falla, comprueba que anuncia formatos de captura y que la cuenta puede abrirlo. Si la cámara no acepta el formato solicitado, revisa el que anuncia al iniciar y ajusta `--ancho`, `--alto` y `--fps`.

## Sesión de práctica

1. Monta la cámara a la altura prevista. Comprueba encuadre a 1,2 m, 1,5 m y 1,8 m. Con la persona sola a unos 1,5 m, pulsa **E** para capturar 10 segundos mientras gira de manera continua y pausada. El programa salta fotogramas sin una única detección útil. Requiere 8 recortes y conserva hasta 12.
2. Revisa el vídeo anotado y las miniaturas. Comprueba identidad y cobertura de frente, espalda y ambos perfiles. **Enter** aprueba la galería y solicita seguir a la persona si hay una coincidencia vigente. **R** descarta el intento y vuelve a espera. Cada inicio de captura cuenta, hasta cinco por sesión. Los vídeos de intentos fallidos o descartados quedan como evidencia local.
3. Si el objetivo desaparece, se rechaza o es ambiguo, deja de resaltarse. Cuando reaparece con una coincidencia clara, pulsa **Enter** para volver a marcarlo. **R** permite empezar un nuevo enrolamiento y **Esc** termina la sesión. **V** inicia o finaliza un clip sin anotaciones, incluso antes de enrolar.
4. Graba con **V** clips independientes de calibración y evaluación. Prueba objetivo solo, escena vacía, distractor solo, cruces, oclusión y transiciones interior/exterior. Usa consentimiento e IDs pseudónimos. Las capturas, recortes y decisiones por fotograma quedan en `datos/enrolamientos/` y están excluidos de Git.

## Evaluación

- Los AVI de prueba conservan un fotograma por iteración. Su reproducción usa el FPS nominal del archivo y puede ser más rápida que la captura real si HOG reduce el rendimiento. El tiempo real está en `decisiones.csv`, que enlaza cada decisión a un fotograma de clip mediante un índice desde cero. El resumen reporta FPS efectivos y latencia local p50/p95 desde lectura hasta composición de la imagen, sin incluir el retraso de pantalla.
- Anota en el clip de calibración qué recuadros pertenecen al objetivo y cuáles son distractores. Usa las distancias registradas para fijar `--umbral` y `--margen`, priorizando evitar confusiones. Los valores iniciales de 0,45 y 0,08 son provisionales. Congela los valores antes de medir los clips de evaluación. Si reinicias el proceso, vuelve a enrolar y registra cuál fue la galería de esa sesión.
- En evaluación, informa por clip el número de fotogramas con objetivo visible, pérdidas del detector, rechazos con recuadro disponible, falsas aceptaciones y sustituciones. La revisión de identidad es manual. Los conteos automáticos del resumen describen decisiones del programa.
- Para comparar HOG con el mismo vídeo de cuerpo entero usa `python -m software.percepcion.practica --video ruta/al/clip.avi`. Guarda un CSV por resolución y un informe con FPS, latencia y cantidad de recuadros. Revisa los recuadros contra anotaciones para estimar recuperación real. Si HOG pierde perfiles, espalda o personas a distancia, repetir con el detector ONNX previsto en la [evaluación de IA](../evaluacion-ia.md).
- PCA Euclídea, PCA Mahalanobis y redes quedan en la comparación offline. OpenVINO se considera cuando haya un encoder alternativo para medir. El histograma es sensible a ropa similar e iluminación.

Referencia de gestión: [HU de Vicente](https://trello.com/c/zU5nasgb). La verificación con la Logitech en el NUC se registra después de la práctica.
