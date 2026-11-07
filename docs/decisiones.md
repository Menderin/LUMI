# Registro de decisiones técnicas

Actualizado: 2026-11-07. Confirmado significa respaldado por petición o fuente indicada; no significa implementado ni validado experimentalmente.

| ID | Decisión o hipótesis | Estado y origen | Motivo / condición para cerrar |
| --- | --- | --- | --- |
| D-01 | Separar software, firmware, hardware, pruebas, modelos, docs y Agents | Confirmado por usuario | Organización del repositorio |
| D-02 | MVP en superficies lisas, sin cargas significativas ni escaleras | Base documental del Charter | Validar funciones antes de escalar |
| D-03 | Procesamiento local sin API externa de IA | Restricción explícita del usuario | Operación autónoma local |
| D-04 | Cuatro ruedas/motores, dirección diferencial por lados | Diseño declarado por usuario; inventario pendiente | No implica orugas físicas ni driver ya dimensionado |
| D-05 | Python para IA | Orientación explícita del usuario | Facilitar experimentación; versiones pendientes |
| D-06 | ROS 2 en computador; C/C++ en firmware | Propuesta alineada con usuario y Charter | Confirmar SO, placa e interfaces |
| D-07 | Comparar PCA Euclídea/Mahalanobis y autoencoder; Re-ID como referencia candidata | Propuesto | Resolver divergencia entre documentos con mediciones |
| D-08 | Parar ante pérdida/ambigüedad; sin búsqueda móvil por defecto | Propuesta de seguridad compatible con HU de Trello | Acordar tiempos, reacquisición y rearme |
| D-09 | Enlace serie simple frente a micro-ROS | Pendiente | Elegir con placa y presupuesto de recursos |
| D-10 | CMake/ament/colcon; Conan solo si aporta dependencia externa | Propuesta | No instalar una segunda cadena de paquetes sin necesidad |
| D-11 | Instrucciones modulares y flujo ODD local | Solicitado por usuario; adaptación para revisión | AGENTS.md enruta; no instala Gentle AI/Engram/RDD |

## Cómo actualizar

Conservar ID, fecha, fuente, alternativas y motivo de cualquier cambio relevante. Una prueba puede invalidar una hipótesis sin ampliar el alcance. Cambios de funciones o compromisos requieren acuerdo; correcciones documentales rutinarias no necesitan aprobación adicional.

## D-12: Datos propios y enrolamiento

Estado: organización documental solicitada por el usuario. Separar herramientas de construcción del dataset, lógica de enrolamiento y almacenamiento local de datos. Propuesta: comenzar capturas con cámara en soporte a geometría prevista y repetir validación en el robot montado. Volumen, cámara y protocolo final pendientes. No se han capturado imágenes ni implementado scripts.
