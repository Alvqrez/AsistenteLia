#!/usr/bin/env python3
"""resumen.py — Resumen del día. Delega en `mod_resumen` (ResumenTools)."""

from __future__ import annotations

from core.intent import IntentSpec
from core.matchers import contains_any
from core.skill import Skill


def _resumen_dia(ctx, m):
    ctx.resumen.resumen_del_dia()


class ResumenSkill(Skill):
    name = "resumen"

    def intents(self, ctx):
        return [
            IntentSpec(name="resumen.dia", priority=690,
                       matcher=contains_any(("resumen", "qué hice hoy", "que hice hoy",
                                             "mi resumen", "resumen del día", "resumen del dia")),
                       handler=_resumen_dia, examples=("resumen", "qué hice hoy")),
        ]
