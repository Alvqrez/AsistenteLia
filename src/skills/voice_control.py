#!/usr/bin/env python3
"""
voice_control.py — Control de Lia: voz, pausa, apagado, ayuda, dashboard,
configuración y calibración.

Reúne las intenciones "meta" que en el diseño anterior vivían dispersas al
principio del if/elif. La lógica de ciclo de vida (pausar/reactivar/apagar) se
delega al kernel a través de `ctx.kernel`.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading

from core.intent import IntentSpec
from core.matchers import contains_any, equals_any
from core.skill import Skill
from skills import _help

logger = logging.getLogger("lia.skill.voice")

try:
    import mod_sonidos
except Exception:  # pragma: no cover
    mod_sonidos = None


# ── Handlers ───────────────────────────────────────────────────────────────
def _cancel_sin_pendiente(ctx, match):
    ctx.say("No hay ninguna acción pendiente.")


def _gracias(ctx, match):
    _help.cerrar_txt_comandos()
    ctx.say(ctx.persona.gracias())


def _ayuda(ctx, match):
    _help.abrir_txt_comandos()
    ctx.say("Aquí tienes todos mis comandos.")
    ctx.registrar_actividad("Abrió Comandos.txt")


def _dashboard(ctx, match):
    # Dashboard consolidado: una sola GUI (React). El comando trae al frente la
    # ventana principal (vía señal Qt thread-safe), en vez del antiguo popup
    # tkinter de mod_dashboard.py (ya deprecado).
    win = getattr(ctx, "_gui_window", None)
    if win is not None and hasattr(win, "signal_show"):
        win.signal_show.emit()
        ctx.say("Aquí tienes el panel.")
    else:
        ctx.say("El panel está en la ventana principal de Lia.")


def _config(ctx, match):
    ctx.config.asistente_configuracion(ctx)


def _silencio(ctx, match):
    if ctx.voz is not None:
        ctx.voz.set_silencioso(True)
    print("Modo silencioso activado.")


def _habla(ctx, match):
    if ctx.voz is not None:
        ctx.voz.set_silencioso(False)
    ctx.say(ctx.persona.voz_reactivada())


def _pausa(ctx, match):
    if ctx.kernel is not None:
        ctx.kernel.pause()
    ctx.say(ctx.persona.pausa())


def _reactivar(ctx, match):
    estaba_en_pausa = ctx.kernel.resume() if ctx.kernel is not None else False
    if estaba_en_pausa:
        ctx.say(ctx.persona.reactivacion())
    else:
        ctx.say(ctx.persona.saludo_corto())


def _apagate(ctx, match):
    if mod_sonidos:
        mod_sonidos.sonido_apagado()
    ctx.say(ctx.persona.apagado())
    if ctx.kernel is not None:
        ctx.kernel.request_shutdown()


def _calibrar(ctx, match):
    ctx.say("Voy a calibrar el detector de aplausos. Abre la consola y sigue las instrucciones.")
    script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "calibrar_perfil.py",
    )

    def _run():
        try:
            subprocess.run([sys.executable, script], check=True)
            if ctx.detector is not None:
                ctx.detector.recargar_perfil()
            ctx.say("Calibración completada. Umbrales personalizados cargados.")
        except Exception:
            ctx.say("Hubo un error durante la calibración. Revisa la consola.")

    threading.Thread(target=_run, daemon=True).start()


class VoiceControlSkill(Skill):
    name = "voice_control"

    def intents(self, ctx):
        return [
            IntentSpec(
                name="control.cancelar_sin_pendiente", priority=15,
                matcher=equals_any(("cancela", "cancel", "olvídalo", "olvidalo", "no importa")),
                handler=_cancel_sin_pendiente,
                examples=("cancela",),
            ),
            IntentSpec(
                name="control.gracias", priority=30,
                matcher=contains_any(("gracias",)), handler=_gracias,
                examples=("gracias", "muchas gracias lia"),
            ),
            IntentSpec(
                name="control.ayuda", priority=40,
                matcher=contains_any(("comandos", "ayuda", "menú", "menu",
                                      "qué puedes hacer", "que puedes hacer",
                                      "qué sabes hacer", "que sabes hacer")),
                handler=_ayuda, examples=("comandos", "¿qué puedes hacer?"),
            ),
            IntentSpec(
                name="control.dashboard", priority=50,
                matcher=contains_any(("dashboard", "panel", "muéstrame el panel",
                                      "abre el panel", "muestra panel")),
                handler=_dashboard, examples=("dashboard", "abre el panel"),
            ),
            IntentSpec(
                name="control.config", priority=60,
                matcher=contains_any(("configuracion", "configuración", "ajustes",
                                      "ver ajustes", "mi configuracion")),
                handler=_config, examples=("configuracion", "ajustes"),
            ),
            IntentSpec(
                name="control.silencio", priority=80,
                matcher=contains_any(("silencio", "cállate", "callate", "modo silencioso",
                                      "sin voz", "no hables", "mute", "ya no hables",
                                      "deja de hablar", "silencia tu voz")),
                handler=_silencio, examples=("silencio", "cállate", "mute"),
            ),
            IntentSpec(
                name="control.habla", priority=90,
                matcher=contains_any(("habla", "activa voz", "voz normal", "ya puedes hablar")),
                handler=_habla, examples=("habla", "activa voz"),
            ),
            IntentSpec(
                name="control.pausa", priority=100,
                matcher=contains_any(("pausate", "pausa", "detente", "para", "descansa",
                                      "modo descanso", "silencia los aplausos", "voy a descansar",
                                      "voy a dormir", "tengo sueño", "me voy un momento",
                                      "espérate", "esperate", "un momento")),
                handler=_pausa, examples=("pausate", "voy a descansar"),
            ),
            IntentSpec(
                name="control.reactivar", priority=110,
                matcher=contains_any(("ya regresé", "ya regrese", "ya volví", "ya volvi",
                                      "estoy de vuelta", "aquí estoy", "aqui estoy")),
                handler=_reactivar, examples=("ya regresé", "ya volví"),
            ),
            IntentSpec(
                name="control.apagate", priority=120,
                matcher=contains_any(("apagate", "apagar lia", "ciérrate", "cierrate",
                                      "hasta luego", "hasta mañana", "hasta manana",
                                      "chao lia", "adiós lia", "adios lia")),
                handler=_apagate, examples=("apagate", "adiós lia"),
            ),
            IntentSpec(
                name="control.calibrar", priority=480,
                matcher=contains_any(("calibrar aplausos", "calibrar micrófono",
                                      "calibrar microfono", "recalibrar", "recalibra")),
                handler=_calibrar, examples=("recalibra", "calibrar aplausos"),
            ),
        ]
