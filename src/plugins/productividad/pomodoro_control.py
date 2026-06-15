#!/usr/bin/env python3
"""
pomodoro_control.py — Pausar, reanudar y cancelar el pomodoro en curso.

El pomodoro de mod_memoria ahora corre con tick de 1 segundo y eventos de
pausa/cancelación; este plugin solo expone los comandos de voz.

Prioridades 86–88: antes de control.pausa (100, captura "pausa") y de
prod.pomodoro (350, captura "pomodoro").
"""

from __future__ import annotations

from core.intent import IntentSpec
from core.matchers import contains_any
from core.skill import Skill


def _pausar(ctx, m):
    ctx.memoria.pausar_pomodoro()


def _reanudar(ctx, m):
    ctx.memoria.reanudar_pomodoro()


def _cancelar(ctx, m):
    ctx.memoria.cancelar_pomodoro()


class PomodoroControlSkill(Skill):
    name = "pomodoro_control"
    category = "productividad"

    def intents(self, ctx):
        return [
            IntentSpec(
                name="prod.pomodoro_pausar", priority=86,
                matcher=contains_any(("pausa el pomodoro", "pausa pomodoro",
                                      "pausa mi pomodoro", "detén el pomodoro",
                                      "deten el pomodoro")),
                handler=_pausar,
                description="Pausa el pomodoro en curso",
                aliases=("pausa pomodoro", "pausa el pomodoro"),
                examples=("pausa el pomodoro",),
            ),
            IntentSpec(
                name="prod.pomodoro_reanudar", priority=87,
                matcher=contains_any(("reanuda el pomodoro", "reanuda pomodoro",
                                      "continúa el pomodoro", "continua el pomodoro",
                                      "sigue el pomodoro")),
                handler=_reanudar,
                description="Reanuda un pomodoro pausado",
                aliases=("reanuda pomodoro",),
                examples=("reanuda el pomodoro",),
            ),
            IntentSpec(
                name="prod.pomodoro_cancelar", priority=88,
                matcher=contains_any(("cancela el pomodoro", "cancela pomodoro",
                                      "cancela mi pomodoro", "termina el pomodoro",
                                      "olvida el pomodoro")),
                handler=_cancelar,
                description="Cancela el pomodoro en curso",
                aliases=("cancela pomodoro", "cancela el pomodoro"),
                examples=("cancela el pomodoro",),
            ),
        ]
