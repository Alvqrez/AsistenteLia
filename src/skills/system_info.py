#!/usr/bin/env python3
"""
system_info.py — Modos (estudio/código/juego), info del sistema y acciones de
energía. Delega en `mod_sistema` (SystemTools).

Endurecimiento de seguridad (Fase 13): las acciones destructivas o de alto
impacto disparadas por voz (apagar la PC) ahora piden confirmación explícita,
porque un falso positivo del reconocedor no debería apagar el equipo.
"""

from __future__ import annotations

import logging

from core.intent import IntentSpec
from core.matchers import contains_any, contains_word_any, without
from core.skill import Skill

logger = logging.getLogger("lia.skill.system")

_SINONIMOS_VSCODE = (
    "necesito programar", "quiero programar", "a programar", "vscode", "vs code",
    "visual studio", "código", "editor", "modo código", "modo programacion",
    "a codear", "codear", "abre el editor", "entorno de desarrollo",
    "ayúdame a programar", "quiero codear", "vamos a programar", "modo dev",
    "programemos",
)
_SINONIMOS_ESTUDIO = (
    "modo estudio", "a estudiar", "necesito estudiar", "quiero estudiar",
    "tiempo de estudiar", "hora de estudiar", "a trabajar", "modo trabajo",
    "chatgpt y whatsapp", "voy a estudiar", "voy a trabajar", "hora de trabajar",
    "modo concentración", "modo concentracion",
)
_SINONIMOS_JUEGO = (
    "modo juego", "a jugar", "quiero jugar", "hora de jugar", "gaming",
    "videojuegos", "necesito discord", "abre discord", "vamos a jugar",
    "quiero relajarme jugando", "hora de gaming",
)
_SINONIMOS_SISTEMA = (
    "sistema", "cpu", "ram", "recursos", "cómo está la pc", "como esta la pc",
    "uso del sistema", "rendimiento", "cómo anda la pc", "como anda la pc",
    "cómo está el equipo", "como esta el equipo", "cómo estoy de memoria",
    "como estoy de memoria",
)
_SINONIMOS_DISCO = (
    "disco", "espacio", "espacio libre", "cuánto disco", "cuanto disco",
    "cuánto espacio", "cuanto espacio", "espacio en disco", "cuánto me queda",
    "cuanto me queda",
)
_AFIRMATIVO = ("sí", "si", "claro", "confirmo", "dale", "hazlo", "ok", "okay",
               "apaga", "adelante", "por supuesto")


def _es_afirmativo(r: str) -> bool:
    return any(w in r.lower() for w in _AFIRMATIVO)


def _modo_codigo(ctx, match):
    ctx.sistema.modo_programacion()


def _modo_estudio(ctx, match):
    ctx.sistema.modo_estudio()


def _modo_juego(ctx, match):
    ctx.sistema.modo_juego()


def _info_sistema(ctx, match):
    ctx.sistema.obtener_info_sistema()


def _disco(ctx, match):
    ctx.sistema.obtener_uso_disco()


def _procesos(ctx, match):
    ctx.sistema.obtener_procesos_pesados()


def _bloquear(ctx, match):
    ctx.sistema.bloquear_pc()


def _apagar(ctx, match):
    def _confirm(r):
        if _es_afirmativo(r):
            ctx.sistema.apagar_pc(segundos=60)
        else:
            ctx.say("Apagado cancelado.")
    ctx.ask("¿Seguro que quieres apagar la PC? Di sí para confirmar.", _confirm)


def _cancelar_apagado(ctx, match):
    ctx.sistema.cancelar_apagado()


class SystemSkill(Skill):
    name = "system"
    category = "sistema"

    def intents(self, ctx):
        return [
            # contains_word_any: con subcadenas, "tarea estudiar X" contiene
            # "a estudiar" y activaba el modo estudio. Límite de palabra lo evita.
            IntentSpec(name="system.modo_codigo", priority=180,
                       matcher=without(contains_word_any(_SINONIMOS_VSCODE), ("abre", "cierra", "cerrar")),
                       handler=_modo_codigo,
                       description="Modo programación: VS Code, GitHub y Spotify",
                       aliases=("a programar", "modo código"),
                       examples=("a programar", "modo código", "quiero codear")),
            IntentSpec(name="system.modo_estudio", priority=185,
                       matcher=without(contains_word_any(_SINONIMOS_ESTUDIO), ("abre", "tarea", "pendiente", "anota")),
                       handler=_modo_estudio,
                       description="Modo estudio: ChatGPT y WhatsApp",
                       aliases=("a estudiar", "modo estudio"),
                       examples=("a estudiar", "modo estudio", "voy a trabajar")),
            IntentSpec(name="system.modo_juego", priority=190,
                       matcher=without(contains_word_any(_SINONIMOS_JUEGO), ("abre",)),
                       handler=_modo_juego,
                       description="Modo juego: Discord y optimización",
                       aliases=("a jugar", "modo juego"),
                       examples=("a jugar", "gaming", "modo juego")),
            IntentSpec(name="system.info", priority=490,
                       # contains_word_any: 'ram'/'cpu' deben ser palabras, no
                       # subcadenas (evita capturar 'rama', 'ramas', etc.).
                       matcher=contains_word_any(_SINONIMOS_SISTEMA), handler=_info_sistema,
                       description="Estado del sistema: CPU, RAM y recursos",
                       aliases=("sistema", "cómo está la pc"),
                       examples=("sistema", "cómo está la pc", "cpu")),
            IntentSpec(name="system.disco", priority=500,
                       matcher=contains_any(_SINONIMOS_DISCO), handler=_disco,
                       description="Espacio libre en disco",
                       aliases=("disco", "cuánto espacio libre"),
                       examples=("disco", "cuánto espacio libre")),
            IntentSpec(name="system.procesos", priority=510,
                       matcher=contains_any(("procesos pesados", "qué proceso usa más",
                                             "que proceso usa mas", "procesos que más consumen",
                                             "qué está consumiendo", "que esta consumiendo")),
                       handler=_procesos,
                       description="Lista los procesos que más consumen",
                       aliases=("procesos pesados",),
                       examples=("procesos pesados",)),
            IntentSpec(name="system.bloquear", priority=520,
                       matcher=without(contains_any(("bloquea", "bloquear")),
                                       ("desbloquea", "desbloquear")),
                       handler=_bloquear,
                       description="Bloquea la sesión de Windows",
                       aliases=("bloquea la pc",),
                       examples=("bloquea", "bloquea la pc")),
            IntentSpec(name="system.apagar", priority=530,
                       matcher=contains_any(("apaga la pc", "apaga el pc", "apaga la computadora")),
                       handler=_apagar,
                       description="Apaga la PC en 60 segundos (pide confirmación)",
                       aliases=("apaga la pc",),
                       examples=("apaga la pc",)),
            IntentSpec(name="system.cancelar_apagado", priority=540,
                       matcher=contains_any(("cancela apagado",)), handler=_cancelar_apagado,
                       description="Cancela un apagado programado",
                       aliases=("cancela apagado",),
                       examples=("cancela apagado",)),
        ]
