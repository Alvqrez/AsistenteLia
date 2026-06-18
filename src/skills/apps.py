#!/usr/bin/env python3
"""
apps.py — Abrir aplicaciones / sitios web y cerrar todo.

Delega en `mod_sistema` (SystemTools). El mapa de URLs (`WEB_MAP`) sigue siendo
la única fuente de verdad en `mod_sistema`, evitando la duplicación que existía
cuando Lia.py mantenía su propia copia.
"""

from __future__ import annotations

import logging
import re
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

# Extrae el nombre real de app de frases naturales como:
# "la pestaña de edge", "la app de spotify", "el navegador edge", "el discord"
_RE_NOISE_PREFIX = re.compile(
    r'^(?:(?:la|el|las|los|un|una)\s+)'
    r'(?:pestaña|ventana|pantalla|app|aplicaci[oó]n|aplicacion|programa|navegador|proceso)\s+'
    r'(?:\w+\s+)*'   # palabras extra: "inicio", "principal", etc.
    r'(?:de\s+)?'    # "de" opcional
    r'(.+)$',
    re.IGNORECASE,
)
_RE_ARTICLE = re.compile(r'^(?:el|la|los|las|un|una)\s+(.+)$', re.IGNORECASE)


def _limpiar_nombre_app(texto: str) -> str:
    """
    Extrae el nombre real de la app desde frases naturales:
      "la pestaña de edge"       → "edge"
      "la pestaña inicio de edge"→ "edge"
      "el navegador edge"        → "edge"
      "la app de spotify"        → "spotify"
      "el discord"               → "discord"
      "spotify"                  → "spotify"  (sin cambio)
    """
    texto = texto.strip()
    if not texto:
        return texto
    m = _RE_NOISE_PREFIX.match(texto)
    if m:
        return m.group(1).strip()
    m = _RE_ARTICLE.match(texto)
    if m:
        return m.group(1).strip()
    return texto


def _abrir(ctx, match):
    app = _limpiar_nombre_app(match.slot("resto", ""))

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
    nombre = _limpiar_nombre_app(match.slot("resto", ""))
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
                matcher=after_trigger(("abre ", "abrir ", "lanza ", "lanzar ",
                                       "inicia ", "arranca ", "arrancar ",
                                       "pon ", "ponme ")),
                handler=_abrir,
                description="Abre una aplicación o sitio web",
                aliases=("abre spotify",),
                examples=("abre spotify", "abre youtube", "abre chrome",
                          "lanza discord", "inicia teams",
                          "abre amazon en internet"),
            ),
            # "cierra/mata/termina X" — excluye "todo" para no chocar con apps.cerrar_todo
            IntentSpec(
                name="apps.cerrar_app", priority=275,
                matcher=without(
                    after_trigger(("cierra ", "cerrar ", "mata ", "termina ",
                                   "terminar ", "kill "), slot="resto"),
                    ("todo", "eso"),
                ),
                handler=_cerrar_app,
                description="Cierra una aplicación por su nombre",
                aliases=("cierra spotify",),
                examples=("cierra spotify", "cierra chrome", "cerrar discord",
                          "cierra el vscode", "mata edge",
                          "cierra la pestaña de edge"),
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
