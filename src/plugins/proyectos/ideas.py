#!/usr/bin/env python3
"""
ideas.py — Captura rápida de ideas por voz. Persisten en data/lia_ideas.json
con fecha, para que ninguna se pierda.

  "agrega idea app de recetas"   "lista ideas"   "recuérdame mis ideas"
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from datetime import date

from core.intent import IntentSpec
from core.matchers import after_trigger, contains_any
from core.skill import Skill

logger = logging.getLogger("lia.plugin.ideas")

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT_DIR = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(_SRC_DIR)
IDEAS_PATH = os.path.join(_ROOT_DIR, "data", "lia_ideas.json")


def _cargar() -> list:
    try:
        if os.path.exists(IDEAS_PATH):
            with open(IDEAS_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("ideas", [])
    except Exception as ex:
        logger.error("No se pudo cargar lia_ideas.json: %s", ex)
    return []


def _guardar(ideas: list) -> None:
    try:
        dir_ = os.path.dirname(IDEAS_PATH) or "."
        os.makedirs(dir_, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"ideas": ideas}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, IDEAS_PATH)
    except Exception as ex:
        logger.error("No se pudo guardar lia_ideas.json: %s", ex)


def _agregar(ctx, m):
    texto = m.slot("resto", "").strip()

    def _save(idea: str):
        idea = idea.strip(" ,.")
        if not idea:
            ctx.say("No escuché la idea.")
            return
        ideas = _cargar()
        ideas.append({"texto": idea, "fecha": date.today().isoformat()})
        _guardar(ideas)
        ctx.say(f"Idea guardada: {idea}. Llevas {len(ideas)}.")
        ctx.registrar_actividad(f"Guardó idea: {idea}")

    if texto:
        _save(texto)
    else:
        ctx.ask("¿Cuál es la idea?", _save)


def _listar(ctx, m):
    ideas = _cargar()
    if not ideas:
        ctx.say("No tienes ideas guardadas. Di: agrega idea, y lo que se te ocurra.")
        return
    ctx.say(f"Tienes {len(ideas)} idea{'s' if len(ideas) != 1 else ''} guardada{'s' if len(ideas) != 1 else ''}.")
    for idea in ideas[-5:]:
        ctx.say(idea.get("texto", ""))
    if len(ideas) > 5:
        ctx.say(f"Esas son las 5 más recientes; hay {len(ideas) - 5} más en lia_ideas.json.")


class IdeasSkill(Skill):
    name = "ideas"
    category = "proyectos"

    def intents(self, ctx):
        return [
            IntentSpec(
                # 292: antes de vida.agregar_* (296) y tasks.anotar (300).
                name="proy.agregar_idea", priority=292,
                matcher=after_trigger(("agrega idea", "agrega la idea",
                                       "agrega una idea", "nueva idea",
                                       "anota la idea", "anota idea",
                                       "apunta la idea", "apunta idea",
                                       "tengo una idea")),
                handler=_agregar,
                description="Guarda una idea con su fecha",
                aliases=("agrega idea app de recetas", "tengo una idea"),
                examples=("agrega idea app de recetas",),
            ),
            IntentSpec(
                # 285: antes de rem.fecha (370), que captura "recuérdame".
                name="proy.listar_ideas", priority=285,
                matcher=contains_any(("lista ideas", "lista de ideas",
                                      "mis ideas", "lista mis ideas",
                                      "recuérdame mis ideas", "recuerdame mis ideas",
                                      "qué ideas tengo", "que ideas tengo")),
                handler=_listar,
                description="Lee tus ideas guardadas (las más recientes primero)",
                aliases=("lista ideas", "mis ideas", "recuérdame mis ideas"),
                examples=("lista ideas", "recuérdame mis ideas"),
            ),
        ]
