#!/usr/bin/env python3
"""
entornos.py — Entornos de trabajo de una sola orden.

  "abre mi entorno de trabajo" → VS Code + Spotify + GitHub + Terminal
  "abre entorno flutter"       → VS Code + Android Studio + emulador Android
  "abre entorno web"           → VS Code + Chrome + localhost

Prioridades 174–176: antes de system.modo_codigo (180, captura "entorno de
desarrollo") y de apps.abrir (270, captura "abre ...").
"""

from __future__ import annotations

import glob
import logging
import os
import subprocess
import webbrowser

from core.intent import IntentSpec
from core.matchers import contains_any
from core.skill import Skill

logger = logging.getLogger("lia.plugin.entornos")


def _abrir_app(ctx, nombre: str) -> None:
    try:
        ctx.sistema.open_application(nombre, silent=True)
    except TypeError:
        ctx.sistema.open_application(nombre)
    except Exception as ex:
        logger.warning("No se pudo abrir %s: %s", nombre, ex)


def _lanzar_emulador_android(ctx) -> bool:
    """Lanza el primer AVD disponible. True si lo consiguió."""
    sdk = os.environ.get("ANDROID_HOME") or os.path.expandvars(
        r"%LOCALAPPDATA%\Android\Sdk")
    emulator = os.path.join(sdk, "emulator", "emulator.exe")
    if not os.path.exists(emulator):
        candidatos = glob.glob(r"C:\Android\Sdk\emulator\emulator.exe")
        if candidatos:
            emulator = candidatos[0]
        else:
            return False
    try:
        avds = subprocess.run([emulator, "-list-avds"], capture_output=True,
                              text=True, timeout=20).stdout.split()
        if not avds:
            return False
        subprocess.Popen([emulator, "-avd", avds[0]],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as ex:
        logger.warning("No se pudo lanzar el emulador: %s", ex)
        return False


def _entorno_trabajo(ctx, m):
    ctx.say("Preparando tu entorno de trabajo.")
    _abrir_app(ctx, "vscode")
    _abrir_app(ctx, "spotify")
    webbrowser.open("https://github.com")
    _abrir_app(ctx, "terminal")
    ctx.say("Listo: VS Code, Spotify, GitHub y terminal.")
    ctx.registrar_actividad("Abrió entorno de trabajo")


def _entorno_flutter(ctx, m):
    ctx.say("Preparando el entorno Flutter.")
    _abrir_app(ctx, "vscode")
    _abrir_app(ctx, "android studio")
    if _lanzar_emulador_android(ctx):
        ctx.say("VS Code, Android Studio y el emulador van arrancando.")
    else:
        ctx.say("VS Code y Android Studio abiertos. No encontré un emulador "
                "configurado; créalo en Android Studio.")
    ctx.registrar_actividad("Abrió entorno Flutter")


def _entorno_web(ctx, m):
    ctx.say("Preparando el entorno web.")
    _abrir_app(ctx, "vscode")
    _abrir_app(ctx, "chrome")
    webbrowser.open("http://localhost:3000")
    ctx.say("Listo: VS Code, Chrome y localhost 3000.")
    ctx.registrar_actividad("Abrió entorno web")


class EntornosSkill(Skill):
    name = "entornos"
    category = "automatizacion"

    def intents(self, ctx):
        return [
            IntentSpec(
                name="auto.entorno_trabajo", priority=174,
                matcher=contains_any(("entorno de trabajo", "mi entorno de trabajo",
                                      "prepara mi entorno", "arma mi entorno")),
                handler=_entorno_trabajo,
                description="Abre VS Code, Spotify, GitHub y la terminal de una vez",
                aliases=("abre mi entorno de trabajo",),
                examples=("abre mi entorno de trabajo",),
            ),
            IntentSpec(
                name="auto.entorno_flutter", priority=175,
                matcher=contains_any(("entorno flutter", "entorno de flutter",
                                      "modo flutter")),
                handler=_entorno_flutter,
                description="Abre VS Code, Android Studio y el emulador Android",
                aliases=("abre entorno flutter",),
                examples=("abre entorno flutter",),
            ),
            IntentSpec(
                name="auto.entorno_web", priority=176,
                matcher=contains_any(("entorno web", "entorno de desarrollo web",
                                      "modo desarrollo web")),
                handler=_entorno_web,
                description="Abre VS Code, Chrome y localhost para desarrollo web",
                aliases=("abre entorno web",),
                examples=("abre entorno web",),
            ),
        ]
