#!/usr/bin/env python3
"""
internet.py — Clima, rutina de inicio, búsquedas web (Wikipedia/YouTube/Maps),
traducción, IP, conexión y noticias. Delega en `mod_internet`.
"""

from __future__ import annotations

import logging
import urllib.parse
import webbrowser

from core.intent import IntentSpec
from core.matchers import contains_any
from core.skill import Skill

logger = logging.getLogger("lia.skill.internet")

_SINONIMOS_INICIO = (
    "inicio", "rutina", "buenos días", "buen día", "buenas", "empecemos",
    "comencemos", "arranquemos el día", "empezar el día", "empezar el dia",
    "arrancamos", "buenos días lia", "hola lia", "qué hay de nuevo",
    "que hay de nuevo", "cómo va todo", "como va todo",
)
_SINONIMOS_CLIMA = (
    "clima", "tiempo", "cómo está el clima", "como esta el clima",
    "qué temperatura hace", "que temperatura hace", "va a llover", "llueve hoy",
    "hace frío", "hace calor", "cómo está el tiempo", "como esta el tiempo",
    "clima de hoy", "qué clima hay", "que clima hay",
)


def _rutina(ctx, m): ctx.internet.rutina_inicio()
def _clima(ctx, m): ctx.internet.decir_clima()
def _ip(ctx, m): ctx.internet.obtener_ip_publica()
def _conexion(ctx, m): ctx.internet.verificar_conexion()
def _noticias(ctx, m): ctx.internet.abrir_noticias()


def _wikipedia(ctx, m):
    consulta = m.text.replace("busca en wikipedia", "").replace("wikipedia", "").strip()
    if consulta:
        ctx.internet.buscar_wikipedia(consulta)
    else:
        ctx.say("¿Qué quieres buscar en Wikipedia?")


def _youtube(ctx, m):
    consulta = m.text.replace("busca en youtube", "").replace("youtube", "").strip()
    if consulta:
        ctx.internet.buscar_youtube(consulta)
    else:
        ctx.ask("¿Qué quieres buscar en YouTube?",
                lambda r: ctx.internet.buscar_youtube(r))


def _traduce(ctx, m):
    consulta = (m.text.replace("traduce", "").replace("traducir", "")
                .replace("cómo se dice", "").strip())
    if consulta:
        webbrowser.open(f"https://translate.google.com/?text={urllib.parse.quote(consulta)}")
        ctx.say(f"Buscando traducción de '{consulta}'.")
    else:
        ctx.internet.abrir_traductor()


def _maps(ctx, m):
    lugar = (m.text.replace("abre maps", "").replace("google maps", "")
             .replace("maps", "").strip())
    ctx.internet.abrir_maps(lugar if lugar else None)


class InternetSkill(Skill):
    name = "internet"
    category = "internet"

    def intents(self, ctx):
        return [
            IntentSpec(name="internet.rutina", priority=70,
                       matcher=contains_any(_SINONIMOS_INICIO), handler=_rutina,
                       description="Rutina de inicio del día: saludo, clima y pendientes",
                       aliases=("buenos días", "inicio"),
                       examples=("buenos días", "inicio", "hola lia")),
            IntentSpec(name="internet.maps", priority=268,
                       matcher=contains_any(("maps ", "abre maps", "google maps")),
                       handler=_maps,
                       description="Abre Google Maps, opcionalmente en un lugar",
                       aliases=("abre maps", "maps madrid"),
                       examples=("maps madrid", "abre maps")),
            IntentSpec(name="internet.clima", priority=400,
                       matcher=contains_any(_SINONIMOS_CLIMA), handler=_clima,
                       description="Dice el clima actual de tu ciudad",
                       aliases=("clima", "va a llover"),
                       examples=("clima", "va a llover")),
            IntentSpec(name="internet.wikipedia", priority=410,
                       matcher=contains_any(("wikipedia", "busca en wikipedia")),
                       handler=_wikipedia,
                       description="Busca un tema en Wikipedia",
                       aliases=("wikipedia einstein",),
                       examples=("wikipedia einstein",)),
            IntentSpec(name="internet.youtube", priority=420,
                       matcher=contains_any(("youtube", "busca en youtube")),
                       handler=_youtube,
                       description="Busca un video en YouTube",
                       aliases=("youtube lofi",),
                       examples=("youtube lofi",)),
            IntentSpec(name="internet.traduce", priority=430,
                       matcher=contains_any(("traduce ", "traducir ", "cómo se dice")),
                       handler=_traduce,
                       description="Traduce un texto en Google Translate",
                       aliases=("traduce hola al inglés",),
                       examples=("traduce hola al inglés",)),
            IntentSpec(name="internet.ip", priority=450,
                       matcher=contains_any(("mi ip", "ip pública", "ip publica")),
                       handler=_ip,
                       description="Dice tu dirección IP pública",
                       aliases=("mi ip",),
                       examples=("mi ip",)),
            IntentSpec(name="internet.conexion", priority=460,
                       matcher=contains_any(("hay internet", "tengo conexión", "tengo conexion",
                                             "hay conexión", "hay conexion", "checa internet")),
                       handler=_conexion,
                       description="Verifica si hay conexión a internet",
                       aliases=("hay internet",),
                       examples=("hay internet",)),
            IntentSpec(name="internet.noticias", priority=470,
                       matcher=contains_any(("noticias",)), handler=_noticias,
                       description="Abre las noticias del día",
                       aliases=("noticias",),
                       examples=("noticias",)),
        ]
