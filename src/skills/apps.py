#!/usr/bin/env python3
"""
apps.py — Abrir aplicaciones / sitios web y cerrar todo.

Delega en `mod_sistema` (SystemTools). El mapa de URLs (`WEB_MAP`) sigue siendo
la única fuente de verdad en `mod_sistema`, evitando la duplicación que existía
cuando Lia.py mantenía su propia copia.
"""

from __future__ import annotations

import logging
import webbrowser

from core.intent import IntentSpec
from core.matchers import after_trigger, contains_any, without
from core.skill import Skill

logger = logging.getLogger("lia.skill.apps")

_SUFIJOS_NAVEGADOR = (
    " en google", " en internet", " en el navegador", " en chrome",
    " en firefox", " en edge", " en opera", " en el explorador",
    " en brave", " en el browser",
)


def _abrir(ctx, match):
    app = match.slot("resto", "")

    abrir_en_web = False
    for sufijo in _SUFIJOS_NAVEGADOR:
        if app.endswith(sufijo):
            app = app[: -len(sufijo)].strip()
            abrir_en_web = True
            break

    if not app:
        ctx.ask("¿Qué quieres que abra?",
                lambda r: ctx.sistema.open_application(r))
        return

    web_map = ctx.sistema.WEB_MAP
    if app in web_map:
        webbrowser.open(web_map[app])
        ctx.say(f"Abriendo {app}.")
        ctx.registrar_actividad(f"Abrió web {app}")
        return

    if abrir_en_web:
        nombre_url = app.replace(" ", "")
        webbrowser.open(f"https://www.{nombre_url}.com")
        ctx.say(f"Abriendo {app} en el navegador.")
        ctx.registrar_actividad(f"Abrió web {app}")
        return

    ctx.sistema.open_application(app)


def _cerrar_app(ctx, match):
    nombre = match.slot("resto", "").strip()
    if not nombre:
        ctx.ask("¿Qué quieres que cierre?",
                lambda r: ctx.sistema.cerrar_app(r))
        return
    ctx.sistema.cerrar_app(nombre)


def _cerrar_todo(ctx, match):
    # Acción destructiva (taskkill /f puede perder trabajo sin guardar): confirmar.
    def _confirm(r):
        if any(w in r.lower() for w in ("sí", "si", "claro", "confirmo", "dale",
                                        "hazlo", "ok", "okay", "adelante", "cierra")):
            ctx.sistema.cerrar_todo()
        else:
            ctx.say("Listo, no cierro nada.")
    ctx.ask("Voy a cerrar navegadores y apps. ¿Confirmas? Di sí.", _confirm)


class AppsSkill(Skill):
    name = "apps"
    category = "aplicaciones"

    def intents(self, ctx):
        return [
            IntentSpec(
                name="apps.abrir", priority=270,
                matcher=after_trigger(("abre ", "abrir ")),
                handler=_abrir,
                description="Abre una aplicación o sitio web",
                aliases=("abre spotify",),
                examples=("abre spotify", "abre youtube", "abre chrome",
                          "abre amazon en internet"),
            ),
            # "cierra X" — excluye "todo" para no chocar con apps.cerrar_todo
            IntentSpec(
                name="apps.cerrar_app", priority=275,
                matcher=without(
                    after_trigger(("cierra ", "cerrar "), slot="resto"),
                    ("todo", "eso"),
                ),
                handler=_cerrar_app,
                description="Cierra una aplicación por su nombre",
                aliases=("cierra spotify",),
                examples=("cierra spotify", "cierra chrome", "cerrar discord",
                          "cierra el vscode"),
            ),
            IntentSpec(
                name="apps.cerrar_todo", priority=280,
                matcher=contains_any(("cierra todo", "cerrar todo", "ciérralo todo")),
                handler=_cerrar_todo,
                description="Cierra navegadores y apps abiertas (pide confirmación)",
                aliases=("cierra todo",),
                examples=("cierra todo",),
            ),
        ]
