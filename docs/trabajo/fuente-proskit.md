# Fuente Pro’sKit TE-5305: identificación y ajuste pendiente

Fecha: 2026-11-19.

Usuario identifica fuente como Pro’sKit TE-5305, rango 0–30 V / 0–5 A. Ensayo declarado a 12 V, indicador CV, corriente observada 0,7 A con PWM 20 %. No se ha verificado el punto de limitación de corriente. Se solicitó PWM 60 %, todavía no implementado ni cargado por faltar ajuste de fuente.

## Fuente consultada

[Producto oficial TE-5305B](https://www.proskit.com/Product/TE-5305B?hl=en-US) y [manual oficial del fabricante](https://www.proskit.com/Files/6d16d366-2777-4e77-a3dc-951625c112cc), edición 2015. El sufijo B no fue confirmado por el usuario: comprobar coincidencia de controles antes de aplicar instrucciones de esa variante.

El manual, páginas impresas 5–6 (páginas PDF 6–7), identifica amperímetro como indicador de corriente de salida, ajuste de corriente fino/grueso, e indicadores de tensión constante/corriente constante. Para fijar límite describe una carga variable externa y ajuste hasta el umbral CC. No describe en ese apartado una lectura independiente del límite sin carga. No confundir corriente consumida con corriente límite ni con picos de bobinado bajo PWM.

## Próximo paso

Fuente apagada y separada del driver/ESP/motores para preparar el ajuste. Si el panel coincide, utilizar carga electrónica o carga resistiva de potencia adecuada para establecer y verificar un límite exploratorio de 1 A, independiente del robot. Como ejemplo calculado a 12 V: 12 ohmios disipan 12 W al circular 1 A, por lo que usar resistencia de potencia de al menos 25 W con montaje y ventilación apropiados; se calienta y no va en protoboard. Es un ejemplo de carga, no un componente confirmado disponible ni un fusible/protector ya instalado.

Con carga de prueba y ajustes de corriente inicialmente bajos, subir gradualmente hasta el umbral de aproximadamente 1 A. Cortar la fuente antes de retirar esa carga y reconectar. Mantener las perillas CURRENT sin cambios; verificar después la tensión de salida en vacío. No utilizar motores bloqueados ni el puente H como carga de calibración, ni improvisar un cortocircuito de bornes como método de este manual.

El límite de fuente es exploratorio y no certifica picos del puente: condensadores y recirculación pueden hacer que corriente de entrada y corriente de motor difieran. No se ha aprobado operación al 60 % ni caracterizado el L298. Una carga electrónica o resistencia de potencia apropiada aún debe confirmarse en laboratorio. Si no está disponible, pedir ayuda al encargado para ajustar/verificar la fuente.

El perfil cargado sigue PWM 20 %, corte máximo 500 ms, con rearme y watchdog V2. Ver [registro del ensayo](ensayo-pwm20.md). No se ejecutaron órdenes físicas ni se cambió firmware durante esta identificación.


Actualización posterior: usuario reiteró probar al 60 % pese a no disponer de carga de prueba. Se cargó perfil 60 %/500 ms conservando rearme/watchdog; no se ajustó ni verificó el límite de fuente. Las menciones anteriores a pendiente/no cargado reflejan el estado previo. [Ensayo y evidencia](ensayo-pwm60.md).
