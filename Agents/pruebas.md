# Verificación y evidencia

Para documentación, comprobar enlaces locales, consistencia de estados, fuentes, unidades y git diff --check. Para código, ejecutar pruebas pertinentes al comportamiento cambiado; no agregar pruebas que solo repliquen la implementación.

## Niveles

| Nivel | Ubicación | Evidencia |
| --- | --- | --- |
| Lógica de IA y control | pruebas/software/ | Casos deterministas, entradas inválidas y resultados observables |
| Comunicación | pruebas/integracion/ | Tramas, caducidad, desconexión y recuperación |
| Experimento de identificación | herramientas/ y docs/validacion/ | Protocolo, configuración y métricas por secuencia |
| Robot físico | pruebas/integracion/ y docs/validacion/ | Condiciones, operador, referencia de distancia, fallos y paradas |

Leer docs/validacion/protocolo-preliminar.md antes de evaluar aceptación. No inventar framework, cobertura ni resultados. Hoy no hay aplicación, runner o banco físico verificado. Informar qué no pudo probarse y por qué.

Una casilla terminada necesita evidencia observada. Validación por stakeholder, prueba técnica y estado de Trello son cosas distintas. Si una regla cambia, reabrir únicamente los resultados afectados.
