# Mejoras controladas sobre los PCA existentes

Solicitud del usuario, 2026-11-23: evaluar mejoras comunes en los PCA actuales y despues compararlos con CC-PPCA. No sustituir las referencias originales ni afirmar que una transformacion mejora sin medirla.

## Primera comparacion implementada

| Variante | Tratamiento | Proyeccion y distancia |
| --- | --- | --- |
| histograma | HSV original, sin cambios | Bhattacharyya |
| euclidea | Gris original | PCA y Euclidea |
| mahalanobis | Gris original | La misma PCA anterior y Mahalanobis regularizada |
| euclidea_eqhist | Gris con ecualizacion global | Nueva PCA y Euclidea |
| mahalanobis_eqhist | Gris con ecualizacion global | La misma PCA ecualizada y Mahalanobis regularizada |
| cc_ppca, si hay otra galeria | Gris original | Dos PPCA de clase y regla del articulo |

Los PCA conservan 128x64 (alto x ancho), proporcion del recorte y hasta ocho componentes, limitados por rango numerico. La ecualizacion se aplica despues del redimensionado y antes del relleno negro. Se transforma tanto enrolamiento como consultas. No ecualizar el descriptor HSV. CC-PPCA queda sin ecualizacion en esta primera comparacion para separar el cambio de modelo del cambio de tratamiento.

La ecualizacion puede modificar contraste y amplificar ruido; no garantiza invariancia a iluminacion, pose o ropa. No se implementan aun mascaras, alineamiento corporal ni eliminacion del fondo. Tamano y numero de componentes son configurables en perfiles, pero no se ejecuta una busqueda masiva por defecto.

## Reutilizar la sesion existente

Desde la raiz del repositorio, con el entorno activado y esta version del codigo:

```bash
python -m software.percepcion.guiada --continuar datos/enrolamientos/guiada-20261120-172419-823225 --mejorar-pca
```

Se reutilizan galeria, videos y etiquetas ya guardadas. La revision omite frames ya anotados. Crea otra carpeta bateria-guiada bajo datos/procesados con comparacion.csv, informe.md, decisiones, umbrales y representaciones. No sobrescribe resultados anteriores. Para CC-PPCA agregar --galeria-negativa RUTA a una galeria aprobada de otra persona, independiente de calibracion y evaluacion. Los PCA ordinarios no requieren esa segunda galeria.

Si solo se dispone de una cache completa (sin videos originales), se puede ampliar sin volver a detectar ni etiquetar:

```bash
python -m software.percepcion.comparar_sesion con-mejoras-pca RUTA_CACHE CACHE_NUEVA
python -m software.percepcion.comparar_sesion calibrar CACHE_NUEVA UMBRALES_NUEVOS.json
python -m software.percepcion.comparar_sesion evaluar CACHE_NUEVA UMBRALES_NUEVOS.json RESULTADOS_NUEVOS
```

En un piloto sin distractores, agregar --permitir-sin-distractores al comando calibrar. Revisar --help para las opciones disponibles. El flujo guiado conserva automaticamente la condicion solo del piloto.

## Comparacion y limites

Usar exactamente la misma galeria, recortes detectados y referencias humanas. Ajustar un umbral y margen propios por variante usando solo calibracion y congelarlos antes de evaluar. El perfil forma parte de la firma de calibracion: los umbrales antiguos no sirven para la cache ampliada. Se guardan tratamiento, componentes y proyeccion con cada representacion.

Comparar primero original frente a ecualizado dentro de cada distancia y despues frente a CC-PPCA. Conservar histograma como referencia. Mantener criterios de falsas aceptaciones, sustituciones, rechazo del objetivo y rendimiento descritos en evaluacion-ia.md. Un piloto sin distractores no elige ganador de identidad.

Los videos cuyos resultados ya vimos son datos de desarrollo: repetirlos sirve para diagnosticar cambios. Despues de elegir configuracion hay que capturar una evaluacion nueva e independiente, con otra persona, oclusiones y cambios de luz, sin ajustar parametros mirando esa prueba.

## Verificacion

Pruebas automatizadas con imagenes sinteticas: relleno negro fuera de la ecualizacion, referencias originales conservadas, PCA compartida entre distancias de cada perfil, rechazo de umbrales antiguos y pipeline ampliado con informe. Falta medir estas variantes con las capturas reales en el NUC.
