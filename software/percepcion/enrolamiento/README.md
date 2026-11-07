# Enrolamiento del usuario

Reservado para la lógica que registra al usuario durante una sesión de operación: captura guiada, selección de recortes válidos, generación de representación/galería y señal de éxito o fallo.

No equivale a construir todo el dataset ni obliga a entrenar una red desde cero al iniciar. La interacción de botón y giro está propuesta; duración, cobertura de vistas, mínimo de muestras y definición de intento siguen pendientes.

Ver [protocolo de datos](../../../docs/construccion-dataset.md). La galería y otros datos de sesión van en datos/enrolamientos/, excluido de Git. No actualizarla con candidatos dudosos ni sobrescribirla al perder al usuario. Una nueva sesión debe distinguirse de las anteriores y tener política de cierre y eliminación acordada.
