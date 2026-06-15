#!/usr/bin/env python3
"""
proyecto.py — Acceso rápido al proyecto activo (mod_contexto).

"abre mi proyecto actual"      → VS Code en la carpeta del proyecto activo.
"abre la carpeta del proyecto" → Explorador en esa carpeta.

Prioridad 205: antes de ws.abrir_proyecto (210), que interpretaría
"abre el proyecto actual" como un proyecto literalmente llamado "actual".
"""

from __future__ import annotations

import logging
import os
import subprocess

from core.intent import IntentSpec
from core.matchers import contains_any
from core.skill import Skill

logger = logging.getLogger("lia.plugin.proyecto")


def _ruta_activa(ctx):
    activo = getattr(ctx.contexto, "proyecto_activo", None)
    if activo and activo.get("ruta") and os.path.isdir(activo["ruta"]):
        return activo
    return None


def _abrir_proyecto_actual(ctx, m):
    activo = _ruta_activa(ctx)
    if activo is None:
        ctx.ask("No hay proyecto activo. ¿Cuál quieres abrir?",
                lambda r: ctx.contexto.abrir_proyecto(r))
        return
    try:
        subprocess.Popen(["code", activo["ruta"]], shell=True)
        ctx.say(f"Abriendo {activo['nombre']} en VS Code.")
    except Exception:
        os.startfile(activo["ruta"])
        ctx.say(f"Abriendo la carpeta de {activo['nombre']}.")
    ctx.registrar_actividad(f"Abrió proyecto actual: {activo['nombre']}")


def _abrir_carpeta_proyecto(ctx, m):
    activo = _ruta_activa(ctx)
    if activo is None:
        ctx.ask("No hay proyecto activo. ¿Cuál proyecto busco?",
                lambda r: ctx.contexto.abrir_proyecto(r))
        return
    os.startfile(activo["ruta"])
    ctx.say(f"Abriendo la carpeta de {activo['nombre']}.")
    ctx.registrar_actividad(f"Abrió carpeta del proyecto {activo['nombre']}")


class ProyectoActualSkill(Skill):
    name = "proyecto_actual"
    category = "desarrollo"

    def intents(self, ctx):
        return [
            IntentSpec(
                name="dev.proyecto_actual", priority=205,
                matcher=contains_any(("abre mi proyecto actual", "abre el proyecto actual",
                                      "abre mi proyecto", "proyecto en vscode")),
                handler=_abrir_proyecto_actual,
                description="Abre el proyecto activo en VS Code",
                aliases=("abre mi proyecto actual",),
                examples=("abre mi proyecto actual",),
            ),
            IntentSpec(
                name="dev.carpeta_proyecto", priority=206,
                matcher=contains_any(("abre la carpeta del proyecto",
                                      "carpeta del proyecto",
                                      "abre el directorio del proyecto")),
                handler=_abrir_carpeta_proyecto,
                description="Abre la carpeta del proyecto activo en el explorador",
                aliases=("abre la carpeta del proyecto",),
                examples=("abre la carpeta del proyecto",),
            ),
        ]
