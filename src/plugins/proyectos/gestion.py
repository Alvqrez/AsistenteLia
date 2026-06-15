#!/usr/bin/env python3
"""
gestion.py — Gestión del proyecto activo de trabajo (mod_contexto).

  "proyecto activo"            → dice cuál es (sin abrir nada).
  "cambia proyecto activo a X" → lo cambia sin abrir VS Code.
  "lista proyectos"            → tus proyectos personales (Proyectos.md).

Distinto de "abre el proyecto X" (ws.abrir_proyecto), que además abre VS Code.
"""

from __future__ import annotations

import logging
from typing import Optional

from core.intent import IntentSpec
from core.matchers import after_trigger, contains_any
from core.skill import Skill

logger = logging.getLogger("lia.plugin.gestion")


def _cual_activo(ctx, m):
    activo = getattr(ctx.contexto, "proyecto_activo", None)
    if activo and activo.get("nombre"):
        ruta = activo.get("ruta")
        extra = f", en {ruta}" if ruta else " (sin carpeta encontrada)"
        ctx.say(f"El proyecto activo es {activo['nombre']}{extra}.")
    else:
        ctx.say("No hay proyecto activo. Di: cambia proyecto activo a, y el nombre.")


def _cambiar_activo(ctx, m):
    nombre = m.slot("resto", "").strip()
    if nombre:
        ctx.contexto.establecer_proyecto(nombre)
    else:
        ctx.ask("¿A qué proyecto cambio?", lambda r: ctx.contexto.establecer_proyecto(r))


def _listar_proyectos(ctx, m):
    ctx.vida.estado_proyectos()


def _match_proyecto_activo(cmd: str) -> Optional[dict]:
    """'proyecto activo' exacto o como pregunta — pero no 'proyecto activo X'
    (eso es de ws.abrir_proyecto, que recibe un nombre)."""
    if cmd.strip() == "proyecto activo":
        return {}
    for frase in ("cuál es el proyecto activo", "cual es el proyecto activo",
                  "qué proyecto está activo", "que proyecto esta activo",
                  "cuál es mi proyecto activo", "cual es mi proyecto activo"):
        if frase in cmd:
            return {}
    return None


class GestionProyectosSkill(Skill):
    name = "gestion_proyectos"
    category = "proyectos"

    def intents(self, ctx):
        return [
            IntentSpec(
                # 204: antes de ws.abrir_proyecto (210), que captura "proyecto activo".
                name="proy.activo", priority=204,
                matcher=_match_proyecto_activo,
                handler=_cual_activo,
                description="Dice cuál es el proyecto activo de trabajo",
                aliases=("proyecto activo", "cuál es el proyecto activo"),
                examples=("cuál es el proyecto activo",),
            ),
            IntentSpec(
                name="proy.cambiar_activo", priority=203,
                matcher=after_trigger(("cambia proyecto activo a",
                                       "cambia el proyecto activo a",
                                       "cambia de proyecto a",
                                       "cambia proyecto a",
                                       "cambia mi proyecto a")),
                handler=_cambiar_activo,
                description="Cambia el proyecto activo sin abrir nada",
                aliases=("cambia proyecto activo a lia",),
                examples=("cambia proyecto activo a lia",),
            ),
            IntentSpec(
                # 779: junto a vida.proyectos (780), añade la forma "lista proyectos".
                name="proy.listar", priority=779,
                matcher=contains_any(("lista proyectos", "lista de proyectos",
                                      "lista mis proyectos")),
                handler=_listar_proyectos,
                description="Lista tus proyectos personales",
                aliases=("lista proyectos",),
                examples=("lista proyectos",),
            ),
        ]
