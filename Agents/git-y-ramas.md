# Ramas, commits y colaboración en GitHub

Estado: propuesta para revisión del equipo. Esta guía no crea ramas ni configura protecciones en GitHub.

## Modelo recomendado para LUMI

Para dos integrantes proponemos main como base estable y una rama corta por tarea. No necesitamos develop por ahora. Si más adelante debemos integrar varios cambios dependientes antes de una demostración, podemos evaluar una rama temporal de integración.

| Elemento | Qué significa | Ejemplo |
| --- | --- | --- |
| main | Trabajo integrado, revisado y con las comprobaciones pertinentes realizadas | Documentación o capacidades verificadas hasta ese momento |
| Rama de tarea | Espacio para cambiar algo sin afectar la base compartida | feat/captura-dataset |
| Commit | Punto de guardado con descripción, inicialmente local | docs: explicar captura desde cámara baja |
| Push | Publicar commits de tu rama en GitHub | Compartir avances con el compañero |
| Pull request (PR) | Propuesta para revisar e integrar una rama | Captura de sesiones de enrolamiento |
| Tag y release | Marca de una versión demostrable con notas y limitaciones | v0.1.0, cuando exista una primera entrega validada |

main estable no significa producto terminado ni seguro para cualquier entorno. Cada entrega debe indicar qué funciona y qué se probó. La versión final del semestre puede ser una release; no hace falta una rama llamada final o estable que duplique main.

## Flujo cotidiano con GitHub Desktop

1. Seleccionar el repositorio LUMI y comprobar Current branch y Changes.
2. Si hay cambios pendientes, revisarlos y guardarlos en su rama antes de cambiar de tarea. No descartarlos para poder continuar.
3. Con el directorio limpio, seleccionar main, hacer Fetch origin y Pull origin si hay cambios remotos.
4. Crear una rama desde main con Branch → New branch. Usar un nombre corto sin espacios: docs/guia-dataset, feat/enrolamiento, fix/parada-timeout o hardware/diagrama-motores.
5. Trabajar en esa rama y revisar los archivos y diferencias en Changes. Seleccionar solo lo que corresponde a la tarea.
6. Escribir un mensaje claro y hacer Commit to la rama de trabajo. Publish branch la primera vez y Push origin en las siguientes.
7. Abrir un PR hacia main. Usar Draft si falta trabajo o validación. Indicar qué cambia, tarjeta de Trello, comprobaciones y limitaciones.
8. El compañero revisa; corregir y subir nuevos commits a la misma rama si hace falta. Como propuesta de equipo, integrar después de su aprobación y de las comprobaciones aplicables.
9. Tras integrar, actualizar main localmente. Eliminar la rama terminada solo después de verificar que su trabajo está integrado y no contiene cambios pendientes. Crear otra rama para la siguiente tarea.

Si ya empezaste a editar en main pero todavía no hiciste commit, crear una rama puede llevar esos cambios a la rama nueva. Verificar el resultado en Desktop; si ofrece trasladar cambios y no está claro, pedir ayuda sin descartarlos. Si ya publicaste commits equivocados, no reescribir main para ocultarlos.

## Cuándo hacer commit y cuándo esperar

Hacer commit al completar un cambio coherente que puedas describir: un esquema revisado, una corrección concreta o una función con sus pruebas pertinentes. No hace falta esperar a terminar toda la tarea. También puedes guardar un avance incompleto en tu rama para no perderlo, identificándolo como WIP y manteniendo el PR en Draft; eso no lo convierte en apto para main.

Antes de confirmar revisar diff, rama y selección de archivos. Esperar si aparecen cambios que no reconoces, archivos de otra tarea, credenciales, .venv, capturas personales, galerías, datos excluidos o compilaciones. Separar cambios no relacionados y aclarar lo desconocido. No hacer commits vacíos ni grandes lotes de cambios sin revisar solo para cerrar la jornada.

Mensajes sugeridos:

~~~text
docs: documentar protocolo de captura del dataset
feat: capturar sesiones con metadatos de cámara
fix: detener motores ante comandos caducados
hardware: documentar conexiones del puente H
~~~

Un commit guarda trabajo local; el push lo comparte. Ninguno ejecuta pruebas por sí mismo. Anotar pruebas no ejecutadas, sin afirmar que el robot funciona por haber subido código.

## Conflictos y errores

Un conflicto significa que Git no sabe combinar cambios automáticamente; no implica que se haya perdido todo. Revisarlo con el compañero, preservar ambas intenciones y verificar el archivo resuelto. No elegir siempre toda mi versión o toda la otra versión sin entenderlo.

Si una integración introduce un fallo, proponer un revert revisado que deshaga ese cambio conservando el historial. Evitar force push, reset --hard, borrado de ramas compartidas y reescritura de commits publicados como solución rutinaria. Consultar antes de una operación que pueda perder trabajo. Cada integrante trabaja en su propio clon y rama; coordinar antes de editar los mismos archivos.

## Protección recomendada para main

Propuesta pendiente de configurar: exigir PR y una aprobación del otro integrante, impedir force push y eliminación de main, y aplicar restricciones también a administradores cuando corresponda. Agregar checks obligatorios cuando haya CI real, sin exigir nombres de pruebas que aún no existen. Evaluar squash merge para integrar cada PR como un cambio coherente.

Estas reglas escritas no bloquean acciones en GitHub: requieren configurar la protección del repositorio. No darla por activa sin comprobarla.

## Instrucciones para agentes

Antes de cambiar ramas o hacer commit, inspeccionar git status, rama actual y diff. Conservar trabajo previo y respetar la autorización de la sesión. Documentar no autoriza por sí solo commit, push, PR, merge, tags o cambios de protección. Cuando se solicite implementar con esta propuesta aceptada, trabajar en una rama de tarea y no integrar en main sin autorización correspondiente. No crear develop ni ramas final/estable automáticamente. No resolver conflictos descartando cambios desconocidos.

## Referencias

- [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow).
- [Protección de ramas](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).
