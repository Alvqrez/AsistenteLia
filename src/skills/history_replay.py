#!/usr/bin/env python3
"""
history_replay.py — Re-ejecución de historial y consulta de actividades.

Aprovecha dos fuentes de datos:
  • CommandHistory (en memoria, esta sesión): tiene el texto exacto del comando
    → permite "repite el último comando"
  • lia_historial.json (persistente): tiene descripciones de actividades
    → permite "qué hice hoy" y "cuántas cosas hice esta semana"

No registra sus propios intents en CommandHistory (name="history.*") para
evitar que "repite el último" se repita a sí mismo indefinidamente.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sys

from core.intent import IntentSpec
from core.matchers import contains_any, equals_any
from core.skill import Skill

logger = logging.getLogger("lia.skill.history")

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT_DIR = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(_SRC_DIR)
_HISTORIAL_PATH = os.path.join(_ROOT_DIR, "data", "lia_historial.json")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cargar_actividades() -> list[dict]:
    try:
        if os.path.exists(_HISTORIAL_PATH):
            with open(_HISTORIAL_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("actividades", [])
    except Exception as ex:
        logger.warning("No se pudo leer historial: %s", ex)
    return []


def _actividades_de(fecha_iso: str) -> list[dict]:
    return [a for a in _cargar_actividades() if a.get("timestamp", "").startswith(fecha_iso)]


# ── Handlers ──────────────────────────────────────────────────────────────────

def _repite_ultimo(ctx, m):
    history = ctx.service("command_history")
    if history is None:
        ctx.say("El historial de comandos no está disponible.")
        return
    ultimo = history.last()
    if ultimo is None:
        ctx.say("No hay comandos anteriores en esta sesión.")
        return
    texto = ultimo.get("text", "")
    if not texto:
        ctx.say("No puedo repetir el último comando.")
        return
    ctx.say(f"Repitiendo: {texto}.")
    ctx.kernel.handle_text(texto)


def _que_hice_hoy(ctx, m):
    hoy = datetime.date.today().isoformat()
    actividades = _actividades_de(hoy)

    # Complementar con los de la sesión actual (CommandHistory)
    history = ctx.service("command_history")
    sesion_hoy = history.today() if history else []

    total = len(actividades)
    if total == 0:
        ctx.say("No registré ninguna actividad tuya hoy.")
        return

    # Últimas 5 actividades (las más recientes)
    recientes = actividades[-5:]
    descripciones = [a.get("actividad", "acción") for a in recientes]
    resumen = "; ".join(descripciones)

    if total <= 5:
        ctx.say(f"Hoy hiciste {total} cosas: {resumen}.")
    else:
        ctx.say(f"Hoy registré {total} actividades. Las últimas: {resumen}.")
    ctx.registrar_actividad("Consultó historial de hoy")


def _que_hice_semana(ctx, m):
    hoy = datetime.date.today()
    inicio_semana = hoy - datetime.timedelta(days=hoy.weekday())
    todas = _cargar_actividades()
    de_la_semana = [
        a for a in todas
        if a.get("timestamp", "") >= inicio_semana.isoformat()
    ]
    if not de_la_semana:
        ctx.say("No hay actividades registradas esta semana.")
        return

    por_dia: dict[str, int] = {}
    for a in de_la_semana:
        fecha = a.get("timestamp", "")[:10]
        por_dia[fecha] = por_dia.get(fecha, 0) + 1

    nombres_dia = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    lineas = []
    for i in range(7):
        fecha = (inicio_semana + datetime.timedelta(days=i)).isoformat()
        if fecha in por_dia:
            dia_nombre = nombres_dia[i]
            lineas.append(f"{dia_nombre}: {por_dia[fecha]}")

    total = len(de_la_semana)
    ctx.say(f"Esta semana registré {total} actividades. Por día: {', '.join(lineas)}.")
    ctx.registrar_actividad("Consultó historial semanal")


# ── Skill ─────────────────────────────────────────────────────────────────────

class HistoryReplaySkill(Skill):
    name = "history"
    category = "productividad"

    def intents(self, ctx):
        return [
            IntentSpec(
                name="history.repite",
                priority=300,
                matcher=contains_any((
                    "repite el último", "repite el ultimo",
                    "repite lo último", "repite lo ultimo",
                    "vuelve a hacer lo mismo", "repite eso",
                    "otra vez lo mismo",
                )),
                handler=_repite_ultimo,
                description="Repite el último comando ejecutado en esta sesión",
                aliases=("repite el último comando",),
                examples=("repite el último comando",),
            ),
            IntentSpec(
                name="history.hoy",
                priority=700,
                matcher=contains_any((
                    "qué hice hoy", "que hice hoy",
                    "qué hiciste hoy", "que hiciste hoy",
                    "resumen de hoy", "actividad de hoy",
                    "qué hemos hecho hoy", "que hemos hecho hoy",
                )),
                handler=_que_hice_hoy,
                description="Muestra las actividades registradas hoy",
                aliases=("qué hice hoy",),
                examples=("qué hice hoy",),
            ),
            IntentSpec(
                name="history.semana",
                priority=700,
                matcher=contains_any((
                    "qué hice esta semana", "que hice esta semana",
                    "resumen de la semana", "actividad de la semana",
                    "qué hiciste esta semana", "que hiciste esta semana",
                )),
                handler=_que_hice_semana,
                description="Resume las actividades de esta semana",
                aliases=("qué hice esta semana",),
                examples=("qué hice esta semana",),
            ),
        ]
