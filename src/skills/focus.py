#!/usr/bin/env python3
"""focus.py — Modo Enfoque (bloqueo de distracciones). Delega en `mod_focus`."""

from __future__ import annotations

from core.intent import IntentSpec
from core.matchers import contains_any, first_number
from core.skill import Skill


def _activar(ctx, m):
    ctx.focus.activar(first_number(m.text, 25))


def _desactivar(ctx, m):
    ctx.focus.desactivar()


class FocusSkill(Skill):
    name = "focus"

    def intents(self, ctx):
        return [
            IntentSpec(name="focus.activar", priority=740,
                       matcher=contains_any(("modo enfoque", "modo focus",
                                             "activa el enfoque", "activa focus")),
                       handler=_activar, examples=("modo enfoque 50",)),
            IntentSpec(name="focus.desactivar", priority=750,
                       matcher=contains_any(("termina enfoque", "fin enfoque",
                                             "desbloquea sitios", "desactiva enfoque")),
                       handler=_desactivar, examples=("desbloquea sitios",)),
        ]
