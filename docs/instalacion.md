# Preparación de LUMI en Raspberry Pi 3 Model B

Actualizado el 2026-11-19. El usuario sustituyó la Pi 5 por una Raspberry Pi 3 Model B debido al presupuesto. El usuario informa que instaló Ubuntu Server en la Raspberry. El agente no grabó la tarjeta ni ha comprobado versión/arquitectura o validado LUMI en ella. Los pasos de grabación quedan como referencia de reinstalación.

## Sistema seleccionado para preparar el banco

Ubuntu Server 24.04 LTS, imagen preinstalada específica de Raspberry Pi, arm64, con ROS 2 Jazzy ros-base y operación por consola/SSH como decisión actual. Xfce/LXQt queda opcional para configuración, no es necesario para cámara, vídeo ni ROS. El intento de Desktop no funcionó según el usuario; no se instala una GUI automáticamente. La [matriz oficial de Canonical](https://ubuntu.com/hardware/docs/boards/how-to/ubuntu_supported/raspberry-pi/) incluye Pi 3B con Server en 24.04. La [documentación ROS](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) ofrece Jazzy para Ubuntu 24.04 arm64.

No usar una ISO amd64 ni una ISO ARM genérica para esta grabación. Buscar el nombre `ubuntu-24.04.x-preinstalled-server-arm64+raspi.img.xz`, donde x corresponde a la revisión disponible. Descargar de [Canonical](https://cdimage.ubuntu.com/releases/24.04/release/) y comprobar el SHA256 contra SHA256SUMS si se descarga manualmente. No cambiar a otra versión mayor porque aparezca primero en el catálogo.

## Grabar la microSD desde Windows

1. Conservar la tarjeta anterior como respaldo o verificar una copia recuperable antes de reutilizarla. La escritura elimina el contenido de la tarjeta elegida.
2. Usar [Raspberry Pi Imager](https://www.raspberrypi.com/software/). Seleccionar dispositivo Raspberry Pi 3.
3. Elegir Ubuntu Server 24.04 LTS de 64 bits. Si no aparece, descargar la imagen preinstalada indicada y seleccionarla mediante la opción de imagen personalizada.
4. Seleccionar exclusivamente la microSD destinada a LUMI, comprobando capacidad y lector. Como tamaño de trabajo se recomienda 32 GB o más si está disponible; no sustituye comprobar el espacio real de imagen y dataset.
5. Si Imager admite personalización para esa imagen, configurar usuario, hostname `lumi`, SSH y red. Si no la admite, seguir la configuración inicial oficial; no asumir que existe el usuario `pi` ni una contraseña predeterminada.
6. Escribir y completar la verificación de Imager. Expulsar la tarjeta correctamente, insertarla en la Pi y arrancar con alimentación adecuada. Preferir Ethernet para el primer acceso si se dispone de él.

[Guía oficial de preparación](https://www.raspberrypi.com/documentation/computers/getting-started.html). Este documento no ejecuta escritura de discos ni autoriza seleccionar una unidad desconocida.

## Primera comprobación en la Raspberry

```sh
cat /etc/os-release
uname -m
free -h
lsblk
```

Esperado: Ubuntu 24.04 y `aarch64`. Comprobar memoria y espacio disponibles antes de instalar IA. Registrar revisión de imagen y fecha. Después, con red funcional:

```sh
sudo apt update
sudo apt upgrade
sudo apt install git python3-venv python3-serial
```

Instalar ROS siguiendo su guía oficial, incluyendo la configuración de repositorio y locale. El paquete de objetivo es `ros-jazzy-ros-base`, no desktop. No copiar solo `apt install` sin preparar antes el repositorio ROS. Verificar ROS con una prueba mínima antes de integrar cámara y ESP.

## Operación por consola y vídeo

La revisión posterior del usuario propone prescindir del escritorio para el siguiente banco. Recomendación: mantener Ubuntu Server por consola/SSH y evaluar [vídeo compartido con ROS 2](video-ros-pi3.md). No se requiere Xfce/LXQt para capturar ni transmitir imágenes. Los pasos de escritorio siguientes quedan como alternativa opcional, no requisito del robot. No se desinstaló nada de la Raspberry.

## Escritorio ligero opcional

Instalar primero la imagen Server anterior. Después del primer arranque y la actualización, añadir Xfce y pantalla de inicio de sesión:

```sh
sudo apt install --no-install-recommends xorg xfce4 lightdm lightdm-gtk-greeter
sudo systemctl set-default graphical.target
sudo reboot
```

Los paquetes Xfce/LightDM están disponibles en Ubuntu 24.04 arm64. Si no se encuentran, comprobar que está habilitado el componente Universe; no añadir repositorios de otras versiones. Si se pregunta por gestor de sesión, elegir LightDM. No se ha ejecutado esta instalación ni comprobado la salida gráfica en la Pi del usuario. El escritorio añade consumo: medir memoria libre antes y durante cámara/IA, y evitar navegador/IDE simultáneos en la placa. El modelo dispone de 1 GB de RAM.

Para futuras pruebas de rendimiento sin escritorio, desde terminal local y tras guardar el trabajo, puede arrancarse en consola con `sudo systemctl set-default multi-user.target` y reiniciar. Restaurar el escritorio con `sudo systemctl set-default graphical.target` y reiniciar. No desinstala Xfce ni cambia el sistema base. No se cambia el modo de arranque automáticamente en esta tarea.

Referencias: [Xfce en Ubuntu Noble](https://packages.ubuntu.com/noble/xfce4), [LightDM](https://packages.ubuntu.com/noble/lightdm), [greeter](https://packages.ubuntu.com/noble/lightdm-gtk-greeter). Esta propuesta no equivale al soporte oficial de una imagen Desktop para Pi 3B.
## Restricciones y orden de integración

La [Pi 3B tiene CPU Cortex-A53/BCM2837 de cuatro núcleos a 1,2 GHz y 1 GB RAM](https://www.raspberrypi.com/products/raspberry-pi-3-model-b/). Compatibilidad del sistema no demuestra viabilidad del pipeline completo.

- Mantener firmware C++ en ESP32-S3 y USB serie. No trasladar la IA a la ESP por la reducción de memoria.
- Instalar únicamente dependencias necesarias para cada ensayo. Verificar wheels/compatibilidad ARM64 y consumo antes de instalar runtimes de IA. No ejecutar la instalación completa de entrenamiento en la Pi.
- Entrenar y comparar inicialmente en el servidor disponible; exportar solo candidatos de inferencia. Que un histograma/PCA sea ligero no elimina el coste del detector corporal.
- Validar cámara, luego enlace serie/ROS y luego detección e identificación, por separado y en conjunto. Medir RSS, CPU, temperatura, latencia p95 y FPS. Usar colas cortas y resolución/FPS de ensayo documentados, sin prometer 10 FPS.
- Medir también la sobrecarga de vídeo Android. Evitar copias y colas crecientes. No usar swap como garantía de respuesta en tiempo real.
- Si la placa no alcanza memoria o latencia requeridas, registrar el límite y revisar configuración o alcance con el equipo. No introducir inferencia remota durante operación para sortearlo.

## Python, firmware y datos

Usar el intérprete del sistema compatible con rclpy. Para herramientas offline puede crearse `.venv` con `python3 -m venv .venv`; recrearlo en cada equipo. Un entorno aislado no cambia el intérprete y puede ocultar paquetes ROS del sistema: definir su acceso expresamente. No copiar el entorno Windows a Linux.

El código de firmware usa ESP-IDF/PlatformIO; compilarlo en el PC de desarrollo evita cargar la Pi. Ver [controlador](../firmware/controlador/README.md). Capturas, galerías y resultados permanecen en `datos/`, fuera de Git. No clonar credenciales ni datos del proyecto anterior al repositorio público.

El [plan de arquitectura](plan-arquitectura-raspberry-esp.md) conserva interfaces y criterios de parada. La potencia de los cuatro motores sigue pendiente de dimensionar y es independiente de esta instalación.