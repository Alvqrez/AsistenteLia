#!/usr/bin/env python3
"""
productivity.py — Pomodoro, hora, fecha, calculadora y conversiones.
Delega en `mod_productividad` y `mod_memoria` (pomodoro).
"""

from __future__ import annotations

import logging

from core.intent import IntentSpec
from core.matchers import contains_any, first_number
from core.skill import Skill

logger = logging.getLogger("lia.skill.productividad")

_SINONIMOS_HORA = ("qué hora", "que hora", "la hora", "dime la hora",
                   "qué horas son", "que horas son", "tienes hora")
_SINONIMOS_FECHA = ("qué fecha", "que fecha", "qué día es", "que dia es", "hoy es",
                    "qué día es hoy", "que dia es hoy", "cuándo es hoy", "cuando es hoy")


def _pomodoro(ctx, m):
    minutos = first_number(m.text, 25)
    ctx.memoria.iniciar_pomodoro(minutos)


def _hora(ctx, m): ctx.productividad.decir_hora()
def _fecha(ctx, m): ctx.productividad.decir_fecha()


def _calcular(ctx, m):
    # calcular() devuelve False si el texto no era una operación válida.
    if not ctx.productividad.calcular(m.text):
        ctx.say(ctx.persona.no_entendi())


def _convertir(ctx, m):
    ctx.productividad.convertir(m.text)


class ProductivitySkill(Skill):
    name = "productivity"

    def intents(self, ctx):
        return [
            IntentSpec(name="prod.pomodoro", priority=350,
                       matcher=contains_any(("pomodoro", "temporizador", "cronómetro",
                                             "cronometro", "enciende el pomodoro",
                                             "inicia el pomodoro", "empieza el pomodoro")),
                       handler=_pomodoro, examples=("pomodoro 30", "temporizador 25 minutos")),
            IntentSpec(name="prod.hora", priority=700,
                       matcher=contains_any(_SINONIMOS_HORA), handler=_hora,
                       examples=("qué hora es",)),
            IntentSpec(name="prod.fecha", priority=710,
                       matcher=contains_any(_SINONIMOS_FECHA), handler=_fecha,
                       examples=("qué fecha es hoy",)),
            IntentSpec(name="prod.calcular", priority=720,
                       matcher=contains_any(("cuánto es", "cuanto es", "calcula",
                                             "resultado de", "cuánto son", "cuanto son")),
                       handler=_calcular, examples=("cuánto es 12 por 8",)),
            IntentSpec(name="prod.convertir", priority=730,
                       matcher=contains_any(("convierte ", "convertir ")),
                       handler=_convertir, examples=("convierte 100 dólares a pesos",)),
        ]
