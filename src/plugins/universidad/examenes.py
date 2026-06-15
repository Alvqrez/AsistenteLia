#!/usr/bin/env python3
"""
examenes.py — Exámenes de la universidad: alta con fecha, próximos y cuenta
regresiva. Persisten en data/lia_universidad.json.

Reutiliza el parser de fechas en español de mod_recordatorios
("mañana", "el lunes", "el 15 de julio"...).

Las tareas de la uni usan los pendientes normales ("agrega tarea X",
"lista tareas", "tarea X completada" → skill tasks).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from datetime import date, datetime

from core.intent import IntentSpec
from core.matchers import after_trigger, contains_any
from core.skill import Skill
from mod_recordatorios import _parsear_fecha

logger = logging.getLogger("lia.plugin.universidad")

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT_DIR = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(_SRC_DIR)
UNI_PATH = os.path.join(_ROOT_DIR, "data", "lia_universidad.json")


def _cargar() -> dict:
    try:
        if os.path.exists(UNI_PATH):
            with open(UNI_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as ex:
        logger.error("No se pudo cargar lia_universidad.json: %s", ex)
    return {"examenes": []}


def _guardar(data: dict) -> None:
    try:
        dir_ = os.path.dirname(UNI_PATH) or "."
        os.makedirs(dir_, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, UNI_PATH)
    except Exception as ex:
        logger.error("No se pudo guardar lia_universidad.json: %s", ex)


def examenes_proximos() -> list:
    """[(materia, fecha_iso, dias_restantes)] futuros, ordenados por cercanía.
    También lo usa el plugin de agenda."""
    hoy = date.today()
    resultado = []
    for ex in _cargar().get("examenes", []):
        try:
            fecha = datetime.strptime(ex["fecha"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        dias = (fecha - hoy).days
        if dias >= 0:
            resultado.append((ex.get("materia", "examen"), ex["fecha"], dias))
    resultado.sort(key=lambda e: e[2])
    return resultado


_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def _fecha_hablada(fecha: date) -> str:
    return f"{fecha.day} de {_MESES[fecha.month - 1]}"


def _decir_dias(dias: int) -> str:
    if dias == 0:
        return "es HOY"
    if dias == 1:
        return "es mañana"
    return f"faltan {dias} días"


def _agregar_examen(ctx, m):
    texto = m.slot("resto", "").strip()

    def _guardar_examen(texto_completo: str):
        fecha = _parsear_fecha(texto_completo.lower())
        if fecha is None:
            ctx.say("No entendí la fecha. Di por ejemplo: agrega examen de cálculo el 15 de julio.")
            return
        # La materia es lo que queda antes de la marca de fecha más temprana.
        materia = texto_completo
        for sep in (" el ", " para el ", " este ", " mañana", " manana", " hoy"):
            idx = texto_completo.lower().find(sep)
            if idx > 0:
                materia = texto_completo[:idx]
                break
        materia = materia.strip(" ,.").removeprefix("de ").strip() or "examen"
        data = _cargar()
        data.setdefault("examenes", []).append(
            {"materia": materia, "fecha": fecha.isoformat()})
        _guardar(data)
        dias = (fecha - date.today()).days
        ctx.say(f"Examen de {materia} anotado para el {_fecha_hablada(fecha)}. "
                f"{_decir_dias(dias).capitalize()}.")
        ctx.registrar_actividad(f"Agregó examen: {materia}")

    if texto:
        _guardar_examen(texto)
    else:
        ctx.ask("¿De qué materia y para qué fecha es el examen?", _guardar_examen)


def _proximos(ctx, m):
    examenes = examenes_proximos()
    if not examenes:
        ctx.say("No tienes exámenes anotados. Puedes decir: agrega examen de física el 20 de junio.")
        return
    ctx.say(f"Tienes {len(examenes)} examen{'es' if len(examenes) != 1 else ''} próximo{'s' if len(examenes) != 1 else ''}.")
    for materia, fecha, dias in examenes[:5]:
        ctx.say(f"{materia}: {_decir_dias(dias)}.")


def _cuanto_falta(ctx, m):
    examenes = examenes_proximos()
    if not examenes:
        ctx.say("No tienes exámenes anotados.")
        return
    # Si menciona una materia, buscarla; si no, el más cercano.
    texto = m.text
    for materia, fecha, dias in examenes:
        if materia.lower() in texto:
            ctx.say(f"Para el examen de {materia} {_decir_dias(dias)}.")
            return
    materia, fecha, dias = examenes[0]
    ctx.say(f"Tu siguiente examen es {materia}: {_decir_dias(dias)}.")


class ExamenesSkill(Skill):
    name = "examenes"
    category = "universidad"

    def intents(self, ctx):
        return [
            IntentSpec(
                # 294: antes de vida.agregar_* (296) y tasks.anotar (300),
                # porque "agrega examen" contiene el verbo genérico "agrega".
                name="uni.agregar_examen", priority=294,
                matcher=after_trigger(("agrega examen", "agregar examen",
                                       "nuevo examen", "anota examen",
                                       "anota el examen", "agrega un examen")),
                handler=_agregar_examen,
                description="Anota un examen con su fecha",
                aliases=("agrega examen de cálculo el 15 de julio",),
                examples=("agrega examen de física el 20 de junio",),
            ),
            IntentSpec(
                name="uni.proximos_examenes", priority=295,
                matcher=contains_any(("próximos exámenes", "proximos examenes",
                                      "mis exámenes", "mis examenes",
                                      "qué exámenes tengo", "que examenes tengo",
                                      "exámenes próximos", "examenes proximos")),
                handler=_proximos,
                description="Lista tus próximos exámenes con días restantes",
                aliases=("próximos exámenes", "mis exámenes"),
                examples=("próximos exámenes",),
            ),
            IntentSpec(
                name="uni.cuanto_falta", priority=293,
                matcher=contains_any(("cuánto falta para el examen",
                                      "cuanto falta para el examen",
                                      "cuándo es el examen", "cuando es el examen",
                                      "cuántos días para el examen",
                                      "cuantos dias para el examen")),
                handler=_cuanto_falta,
                description="Dice cuánto falta para tu examen (el más cercano o por materia)",
                aliases=("cuánto falta para el examen",),
                examples=("cuánto falta para el examen de cálculo",),
            ),
        ]
