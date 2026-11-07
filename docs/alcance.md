# Alcance preliminar del MVP

Estado: consolidación documental para revisión, 2026-11-07. Fuente principal: [Project Charter](Project%20Charter%20Robot%20seguidor.pdf), secciones 2.2, 3, 4.3 y 6. No implica aceptación formal nueva del stakeholder.

## Propósito

Validar técnicamente las capacidades que permitirían una futura plataforma para transportar objetos mientras una persona camina. La iteración actual prueba movilidad, enrolamiento, identidad, seguimiento y distancia. Agricultura, transporte pesado y asistencia a personas mayores son motivaciones futuras; no constituyen validación con esos usuarios.

## Incluido y excluido

| Estado | Capacidad o restricción |
| --- | --- |
| Must, Charter | Movimiento controlado sobre superficies lisas y regulares |
| Must, Charter | Enrolamiento e identificación visual de un usuario |
| Must, Charter | Seguimiento autónomo conservando identidad frente a otras personas |
| Must, Charter | Regulación de distancia durante el seguimiento |
| Restricción del usuario | Procesamiento local; sin API remota para percepción o seguimiento |
| Should, Charter | Sensores complementarios y autonomía cercana a 30 min; ver contradicción de aceptación abajo |
| Could, Charter | Pantalla o interfaz de estado y percepción complementaria; no implementar por defecto |
| Fuera de alcance | Cargas significativas, escaleras, desniveles pronunciados, terrenos irregulares y escala industrial |

La construcción descrita por el usuario es metálica con cuatro motores DC y cuatro ruedas, accionadas por lados. Sensores, puentes H y computador exactos no están seleccionados. Botón y giro de enrolamiento son propuestas de interacción.

## Criterios extraídos del Charter

| ID | Criterio documental | Qué falta concretar para verificar |
| --- | --- | --- |
| AC-01 | Enrolamiento en máximo 5 intentos | Definición de intento, duración, señal de éxito y reinicio |
| AC-02 | No sustituir al usuario cuando otra persona cruza | Escenarios, repeticiones, oclusión y regla de reanudación |
| AC-03 | Distancia 1,5 m ± 0,3 m | Referencia física, medición, proporción temporal y transitorios permitidos |
| AC-04 | Completar recorrido con seguimiento ininterrumpido | Longitud, velocidad, curvas, condiciones y cómo registrar pérdidas |
| AC-05 | Autonomía mínima de 30 minutos | Batería, carga de cómputo y ciclo de movimiento |
| AC-06 | Resultados y documentación reproducibles | Protocolo final y evidencias de ejecución |

El intervalo 1,2–1,8 m se deriva de AC-03: no es distancia mínima/máxima del sensor ni límite físico de seguridad. No usarlo como tal sin diseño de frenado.

## Seguridad y contradicciones pendientes

Trello incluye detenerse ante pérdida y evitar colisiones. El tiempo máximo de parada, umbral de obstáculos y política de recuperación siguen sin valor acordado. Propuesta conservadora: parar ante incertidumbre; no maniobrar buscando al usuario por defecto.

El Charter clasifica autonomía como Should, pero exige 30 min en la aceptación del entregable 4. Mantener visible esa exigencia y confirmar su prioridad. La continuidad del recorrido se evalúa en escenario nominal; en pruebas de pérdida u obstáculos se evalúa la parada. Una parada correcta no debe penalizarse como decisión insegura para satisfacer continuidad.

Ver [fuentes y pendientes](fuentes-y-pendientes.md) y [protocolo](validacion/protocolo-preliminar.md). Los cinco entregables son análisis, diseño, implementación, validación y despliegue/documentación; los cuatro incrementos I1–I4 continúan como organización operativa.
