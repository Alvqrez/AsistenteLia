#!/usr/bin/env python3
"""
runner.py — Ejecuta comandos de desarrollo por voz, en una terminal visible,
con cwd en el proyecto activo.

  "ejecuta flutter run"      "ejecuta npm install"
  "ejecuta flutter build apk"  "ejecuta npm run dev"

Seguridad: SOLO se ejecutan comandos cuyo primer token está en la whitelist
de herramientas de desarrollo. "ejecuta el proyecto" (sin comando) sigue
yendo a ws.ejecutar (130), que ahora detecta Flutter/Vite/React/Node/Python
automáticamente (modo JARVIS en mod_contexto.detectar_comando_proyecto).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from core.intent import IntentSpec
from core.skill import Skill

logger = logging.getLogger("lia.plugin.runner")

_HERRAMIENTAS = ("flutter", "npm", "npx", "yarn", "pnpm", "dart", "python",
                 "pip", "git", "cargo", "go", "dotnet", "mvn", "gradle")
_TRIGGERS = ("ejecuta ", "corre ", "lanza ")


def _match_comando_dev(cmd: str) -> Optional[dict]:
    """Matcher: 'ejecuta <herramienta> ...' solo si la herramienta es conocida."""
    for t in _TRIGGERS:
        if cmd.startswith(t):
            resto = cmd[len(t):].strip()
            if resto.split(" ", 1)[0] in _HERRAMIENTAS:
                return {"comando": resto}
    return None


def _ejecutar(ctx, m):
    comando = m.slot("comando", "")
    activo = getattr(ctx.contexto, "proyecto_activo", None)
    if activo and activo.get("ruta") and os.path.isdir(activo["ruta"]):
        ruta = activo["ruta"]
        donde = f"en {activo['nombre']}"
    else:
        ruta = os.path.expanduser("~")
        donde = "en tu carpeta de usuario (no hay proyecto activo)"
    try:
        ctx.contexto.ejecutar_en_terminal(comando, ruta)
        ctx.say(f"Ejecutando {comando} {donde}.")
        ctx.registrar_actividad(f"Ejecutó: {comando}")
    except Exception as ex:
        logger.error("No se pudo ejecutar '%s': %s", comando, ex)
        ctx.say("No pude abrir la terminal para ejecutar eso.")


class RunnerSkill(Skill):
    name = "runner"
    category = "desarrollo"

    def intents(self, ctx):
        return [
            IntentSpec(
                # Antes de ws.ejecutar (130): "ejecuta flutter run" es un comando
                # concreto; "ejecuta" a secas sigue siendo el proyecto activo.
                name="dev.ejecutar_comando", priority=125,
                matcher=_match_comando_dev,
                handler=_ejecutar,
                description="Ejecuta un comando de desarrollo en el proyecto activo",
                aliases=("ejecuta npm run dev", "ejecuta flutter run"),
                examples=("ejecuta flutter run", "ejecuta flutter build apk",
                          "ejecuta npm install", "ejecuta npm run dev"),
            ),
        ]
