#!/usr/bin/env python3
"""
diagnostics.py — Auto-diagnóstico de recursos del proceso de Lia.

"Rendimiento de Lia", "cuánto consumes": reporta RAM/CPU/hilos/uptime del
propio asistente. Es distinto de "sistema/cpu/ram" (system.info), que mide la
máquina entera. Delega en services.perf (solo lectura).
"""

from __future__ import annotations

from core.intent import IntentSpec
from core.matchers import contains_any
from core.skill import Skill

from services import perf


def _rendimiento(ctx, m):
    ctx.say(perf.report_text())
    ctx.registrar_actividad("Consultó rendimiento de Lia")


class DiagnosticsSkill(Skill):
    name = "diagnostics"
    category = "sistema"

    def intents(self, ctx):
        return [
            # Triggers deliberadamente específicos ("de lia", "consumes",
            # "memoria usas") para no solaparse con system.info ("sistema",
            # "cpu", "ram", "recursos"), que mide la máquina, no a Lia.
            IntentSpec(
                name="diag.rendimiento", priority=488,
                matcher=contains_any((
                    "rendimiento de lia", "tu rendimiento", "cómo vas tú",
                    "cuánto consumes", "cuanto consumes",
                    "cuánta memoria usas", "cuanta memoria usas",
                    "cuánta ram usas", "cuanta ram usas",
                    "diagnóstico de lia", "diagnostico de lia",
                    "cómo andas de memoria", "como andas de memoria",
                )),
                handler=_rendimiento,
                description="Reporta los recursos que consume Lia (RAM, CPU, hilos, uptime)",
                aliases=("rendimiento de lia", "cuánto consumes"),
                examples=("rendimiento de lia", "cuánta memoria usas"),
            ),
        ]
