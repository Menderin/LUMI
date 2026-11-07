# Protocolo preliminar de validación

Estado: propuesta, sin pruebas ejecutadas. Fuente de metas: Charter, tabla 3 y entregable 4. Completar configuración y condiciones antes de usar para aceptación.

## Registro mínimo por ejecución

Fecha, operador, versión de código/modelo, plataforma, configuración, secuencia o recorrido, iluminación, participantes, instrumentos de referencia, resultado y fallos. Para autonomía agregar batería y ciclo de trabajo. No adjuntar imágenes personales al repositorio por defecto.

| Prueba | Criterio | Procedimiento por completar |
| --- | --- | --- |
| Enrolamiento | AC-01: máximo 5 intentos | Definir intento, giro permitido y prueba independiente de identificación |
| Cruces | AC-02: no cambiar de usuario | Definir distractores, cruces y oclusiones; contabilizar cambios y rechazos |
| Distancia | AC-03: 1,5 m ±0,3 m | Medir con referencia externa; acordar arranque, giros y porcentaje temporal exigido |
| Recorrido nominal | AC-04: seguimiento continuo | Fijar longitud, velocidad y superficie; registrar pérdidas e intervenciones |
| Autonomía | AC-05: al menos 30 min | Fijar ciclo representativo; registrar energía, temperatura y reinicios |
| Pérdida/fallo | HU de parada segura | Medir desde fallo/pérdida hasta detención; umbral máximo pendiente |
| Obstáculos | HU de evitar colisión | Definir objetos, posiciones, velocidad y distancia de parada antes de ejecutar |

## Secuencia segura propuesta

Verificar primero lógica y comunicación sin motores energizados, luego firmware con ruedas elevadas y finalmente recorrido supervisado a velocidad limitada. Confirmar parada física y timeout antes de permitir seguimiento. Acordar límites físicos con el equipo; no ejecutar desde un agente sin autorización de la prueba.

## Informe

Marcar cada criterio como cumple / no cumple / no evaluado, con datos y límites. No interpretar ausencia de colisiones en una muestra como garantía general. Una detención correcta durante prueba de fallo tiene prioridad sobre continuidad. El éxito nominal y la respuesta a fallos se reportan por separado.
