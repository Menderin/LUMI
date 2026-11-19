# Enlace de base ESP32-S3

Estado: en curso, 2026-11-18. Petición autorizada: identificar la ESP conectada y cargar el banco de control acordado, con motores sin potencia. HU: https://trello.com/c/P9X0XPYL.

## Evidencia y decisiones

esptool 5.6.0 identificó ESP32-S3 QFN56 revisión 0.2, 240 MHz, PSRAM integrada de 8 MB y flash de 16 MB. USB Serial/JTAG en COM7 tras BOOT/RESET. GPIO, lógica de alimentación del módulo L298N y capacidad de corriente necesitan verificación física antes de habilitar potencia.

ROS 2 en Linux y firmware C++/ESP-IDF por USB serie. Primera carga en modo banco: se procesan órdenes y se mantienen salidas de motor a cero. No se implementa micro-ROS ni se integra todavía el mando Android. No se declara validado el movimiento físico.

## Criterios y tareas

| ID | Criterio | Estado y evidencia |
| --- | --- | --- |
| B1 | Identificar chip y memoria | Verificado con esptool |
| B2 | Respaldar flash existente | En curso, copia local fuera de Git |
| B3 | Compilar firmware y documentar protocolo/cableado | En curso |
| B4 | Arrancar desarmado, rechazar órdenes inválidas/caducadas y parar tras pérdida de enlace | Pendiente de pruebas USB |
| B5 | Crear puente ROS con rearme explícito y límites de banco | Pendiente; ROS no instalado en este Windows |
| B6 | Probar ruedas y corrientes | Pendiente, requiere montaje y prueba física supervisada |
