"""
services — Capa de servicios inyectables de Lia.

Servicios singleton que el kernel instancia una vez y comparte vía el
AssistantContext. Incluye:

    memory_store — memoria unificada corto/largo plazo (Fase 4).
    scheduler    — temporizadores persistentes (arregla la pérdida de
                   recordatorios/pomodoros al reiniciar).
    ai/          — abstracción de proveedores de IA (Fase 6, interfaz lista,
                   sin proveedor real conectado todavía).
    vision/      — andamiaje para OCR / capturas / análisis visual (Fase 9).
    desktop/     — andamiaje para control de ventanas / multimedia (Fase 8).

Los módulos `mod_*` históricos (mod_sistema, mod_dev, ...) siguen actuando como
la capa de implementación y NO se mueven aquí: el kernel los registra como
servicios tal cual, preservando su comportamiento ya probado.
"""
