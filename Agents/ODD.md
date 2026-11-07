# ODD en LUMI

## Enfoque y procedencia

Se interpreta ODD como Organic Driven Development de Gentle AI, por su correspondencia con la descripción del usuario. No es un estándar universal. Referencia consultada el 2026-11-07: [guía original](https://github.com/Gentleman-Programming/gentle-ai/blob/main/docs/usage.md#organic-driven-development-odd). La rama main puede cambiar.

El enfoque adapta el proceso al trabajo: explorar, ejecutar lo autorizado y verificar proporcionalmente. Un cambio pequeño puede quedar explicado por el diff; uno difícil de retomar necesita un documento que preserve intención, tareas y evidencia. Los cambios de requisitos afectan solo al trabajo relacionado.

## Adaptación local

Esta guía no instala Gentle AI, Engram ni revisión RDD. Tampoco exige subagentes, commits automáticos, límites artificiales de líneas o aprobación repetida para trabajo ya autorizado. Kanban continúa gestionando prioridades; ODD organiza la ejecución técnica.

1. Identificar el resultado solicitado y comprobar alcance y fuentes vigentes.
2. Explorar los archivos afectados e investigar incertidumbres concretas.
3. Para trabajo sustancial, crear un registro en docs/trabajo/ usando la plantilla enlazada antes de modificar comportamiento. Para cambios pequeños basta el diff y la explicación final.
4. Implementar por tareas verificables. Consultar únicamente decisiones de producto o ampliaciones no autorizadas; continuar el trabajo independiente.
5. Registrar comprobaciones observadas, pendientes y limitaciones. Reabrir tareas invalidadas sin borrar evidencia anterior.
6. Al retomar, leer el registro y reconciliarlo con código, GitHub y Trello. Al terminar, informar qué cambió y qué falta.

## Qué hace útil un registro

Identificadores estables, resultado observable, referencias precisas, citas breves de la petición cuando importen y criterios comprobables. Separar contexto, decisiones y evidencia; no marcar tareas como terminadas por haber escrito código. Usar [plantilla](plantilla-trabajo.md). La documentación preliminar puede revisarse sin bloquear correcciones rutinarias.

## Ejemplo aplicado, aún no autorizado para implementar

Trabajo: comparar PCA euclidiano y Mahalanobis con recortes corporales equivalentes. Criterio: producir resultados reproducibles de falsas aceptaciones, rechazo del objetivo, latencia y RAM; no declarar ganador por intuición. Si cambian los recortes, reabrir la comparación afectada conservando los resultados anteriores.
