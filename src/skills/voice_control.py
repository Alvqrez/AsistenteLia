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
from core.matchers import after_trigger, any_of, contains_any, equals_any
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
    registry = ctx.service("commands")
    _help.abrir_txt_comandos(registry)
    if registry is not None:
        ctx.say(_help.resumen_hablado(registry))
    else:
        ctx.say("Aquí tienes todos mis comandos.")
    ctx.registrar_actividad("Abrió Comandos.txt")


def _buscar_comando(ctx, match):
    registry = ctx.service("commands")
    consulta = match.slot("resto", "").strip()
    if registry is None or not consulta:
        ctx.say("Dime qué comando buscas, por ejemplo: busca comando pomodoro.")
        return
    resultados = registry.search(consulta)[:5]
    if not resultados:
        ctx.say(f"No encontré comandos relacionados con '{consulta}'.")
        return
    partes = []
    for s in resultados:
        frase = s.aliases[0] if s.aliases else (s.examples[0] if s.examples else s.name)
        partes.append(f"'{frase}' — {s.description or s.name}")
    ctx.say(f"Encontré {len(resultados)}: " + ". ".join(partes))


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
    category = "control"

    def intents(self, ctx):
        return [
            IntentSpec(
                name="control.cancelar_sin_pendiente", priority=15,
                matcher=equals_any(("cancela", "cancel", "olvídalo", "olvidalo", "no importa")),
                handler=_cancel_sin_pendiente,
                description="Cancela la acción en curso",
                aliases=("cancela",),
                examples=("cancela",),
            ),
            IntentSpec(
                name="control.gracias", priority=30,
                matcher=contains_any(("gracias",)), handler=_gracias,
                description="Cierra el menú de comandos y responde con cortesía",
                aliases=("gracias",),
                examples=("gracias", "muchas gracias lia"),
            ),
            IntentSpec(
                name="control.buscar_comando", priority=35,
                matcher=after_trigger(("busca el comando", "busca comando",
                                       "buscar comando", "qué comando hay para",
                                       "que comando hay para"), require_text=True),
                handler=_buscar_comando,
                description="Busca un comando por nombre o tema en el catálogo",
                aliases=("busca comando pomodoro",),
                examples=("busca comando git", "qué comando hay para el clima"),
            ),
            IntentSpec(
                name="control.ayuda", priority=40,
                matcher=contains_any(("comandos", "ayuda", "menú", "menu",
                                      "qué puedes hacer", "que puedes hacer",
                                      "qué sabes hacer", "que sabes hacer")),
                handler=_ayuda,
                description="Muestra todos los comandos disponibles (lista generada en vivo)",
                aliases=("ayuda", "comandos", "qué puedes hacer"),
                examples=("comandos", "¿qué puedes hacer?"),
            ),
            IntentSpec(
                name="control.dashboard", priority=50,
                matcher=contains_any(("dashboard", "panel", "muéstrame el panel",
                                      "abre el panel", "muestra panel")),
                handler=_dashboard,
                description="Trae al frente el panel principal de Lia",
                aliases=("dashboard", "abre el panel"),
                examples=("dashboard", "abre el panel"),
            ),
            IntentSpec(
                name="control.config", priority=60,
                matcher=contains_any(("configuracion", "configuración", "ajustes",
                                      "ver ajustes", "mi configuracion")),
                handler=_config,
                description="Abre el asistente de configuración",
                aliases=("configuración", "ajustes"),
                examples=("configuracion", "ajustes"),
            ),
            IntentSpec(
                name="control.silencio", priority=80,
                matcher=contains_any(("silencio", "cállate", "callate", "modo silencioso",
                                      "sin voz", "no hables", "mute", "ya no hables",
                                      "deja de hablar", "silencia tu voz")),
                handler=_silencio,
                description="Silencia la voz de Lia (sigue escuchando)",
                aliases=("silencio", "mute"),
                examples=("silencio", "cállate", "mute"),
            ),
            IntentSpec(
                name="control.habla", priority=90,
                matcher=contains_any(("habla", "activa voz", "voz normal", "ya puedes hablar")),
                handler=_habla,
                description="Reactiva la voz de Lia",
                aliases=("habla", "activa voz"),
                examples=("habla", "activa voz"),
            ),
            IntentSpec(
                name="control.pausa", priority=100,
                # Las palabras cortas ("pausa", "para", "detente"...) solo por
                # igualdad EXACTA: como subcadenas secuestraban cualquier frase
                # con la preposición "para" o con "pausa X" ("cuánto falta para
                # el examen" pausaba a Lia).
                matcher=any_of(
                    equals_any(("pausa", "pausate", "para", "detente", "descansa",
                                "espérate", "esperate", "un momento")),
                    contains_any(("pausate", "modo descanso", "silencia los aplausos",
                                  "voy a descansar", "voy a dormir", "tengo sueño",
                                  "me voy un momento")),
                ),
                handler=_pausa,
                description="Pausa la escucha (reactivar con 'ya regresé' o 3 aplausos)",
                aliases=("pausate", "descansa"),
                examples=("pausate", "voy a descansar"),
            ),
            IntentSpec(
                name="control.reactivar", priority=110,
                matcher=contains_any(("ya regresé", "ya regrese", "ya volví", "ya volvi",
                                      "estoy de vuelta", "aquí estoy", "aqui estoy")),
                handler=_reactivar,
                description="Reactiva a Lia después de una pausa",
                aliases=("ya regresé", "estoy de vuelta"),
                examples=("ya regresé", "ya volví"),
            ),
            IntentSpec(
                name="control.apagate", priority=120,
                matcher=contains_any(("apagate", "apagar lia", "ciérrate", "cierrate",
                                      "hasta luego", "hasta mañana", "hasta manana",
                                      "chao lia", "adiós lia", "adios lia")),
                handler=_apagate,
                description="Apaga el asistente por completo",
                aliases=("apagate", "hasta luego"),
                examples=("apagate", "adiós lia"),
            ),
            IntentSpec(
                name="control.calibrar", priority=480,
                matcher=contains_any(("calibrar aplausos", "calibrar micrófono",
                                      "calibrar microfono", "recalibrar", "recalibra")),
                handler=_calibrar,
                description="Calibra el detector de aplausos con tu micrófono",
                aliases=("recalibra", "calibrar aplausos"),
                examples=("recalibra", "calibrar aplausos"),
            ),
        ]
