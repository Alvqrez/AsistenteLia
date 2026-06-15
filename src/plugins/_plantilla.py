#!/usr/bin/env python3
"""
_plantilla.py — Plantilla de un comando/plugin de Lia. NO se carga (empieza
por '_'). Para crear un comando real: copia este archivo a
`plugins/<categoria>/mi_comando.py` (o a `skills/`) y ajusta.

Guía completa: docs/CREAR_COMANDO.md
"""

from __future__ import annotations

from core.intent import IntentSpec
from core.matchers import after_trigger, contains_any
from core.skill import Skill


def _saludar(ctx, match):
    """
    Handler: recibe el AssistantContext (DI) y el IntentMatch.

    ctx te da acceso controlado a todo, sin variables globales:
        ctx.say("...")                  — hablar (TTS + GUI + log)
        ctx.ask("¿...?", callback)      — pregunta de seguimiento
        ctx.sistema / ctx.dev / ctx.internet / ctx.memoria / ...  — servicios
        ctx.memory                      — MemoryStore (corto/largo plazo)
        ctx.config                      — configuración
        ctx.scheduler                   — recordatorios persistentes
        ctx.emit("mi_evento", payload)  — publicar en el EventBus
        ctx.registrar_actividad("...")  — historial de actividades

    match te da lo extraído por el matcher:
        match.text                      — el comando completo en minúsculas
        match.slot("resto")             — slots que extrajo el matcher
    """
    nombre = match.slot("resto", "") or "mundo"
    ctx.say(f"¡Hola, {nombre}!")


class PlantillaSkill(Skill):
    # Identificador para logs y categoría por defecto de sus intenciones.
    name = "plantilla"
    category = "ejemplos"

    def intents(self, ctx):
        return [
            IntentSpec(
                name="plantilla.saludar",          # único en todo el sistema
                priority=900,                       # menor = se evalúa antes
                matcher=after_trigger(("saluda a ",)),
                handler=_saludar,
                description="Saluda a alguien por su nombre",
                aliases=("saluda a lia",),          # frases canónicas: help,
                                                    # búsqueda y validación
                examples=("saluda a leonardo",),
            ),
        ]

    def on_load(self, ctx):
        # Hook opcional: suscribirse a eventos del bus, preparar estado, etc.
        # ctx.bus.subscribe("command_executed", lambda p: ...)
        pass
