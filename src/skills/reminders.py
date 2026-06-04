#!/usr/bin/env python3
"""
reminders.py — Recordatorios por minutos y por fecha.

  • "recuerda X en N minutos"  → PersistentScheduler (servicio nuevo). Antes
    vivía en un hilo en memoria y se perdía al reiniciar; ahora persiste.
  • "recuerda X mañana / el 15 de julio" → `mod_recordatorios` (ya persistía).
"""

from __future__ import annotations

import logging
import re

from core.intent import IntentSpec
from core.matchers import all_of, contains_any
from core.skill import Skill

logger = logging.getLogger("lia.skill.reminders")

_MARCAS_FECHA = [
    "pasado mañana", "pasado manana", "mañana", "manana", "hoy",
    " el lunes", " el martes", " el miércoles", " el miercoles",
    " el jueves", " el viernes", " el sábado", " el sabado", " el domingo",
    " lunes", " martes", " miércoles", " miercoles",
    " jueves", " viernes", " sábado", " sabado", " domingo",
]


def _recordar_minutos(ctx, m):
    cmd_l = m.text
    if " en " not in cmd_l:
        ctx.say("No entendí el recordatorio. Di: recuerda [cosa] en [N] minutos.")
        return
    partes = cmd_l.rsplit(" en ", 1)
    mensaje = (partes[0].replace("recuérdame", "").replace("recuerdame", "")
               .replace("recuerda", "").strip())
    resto = partes[1]
    try:
        mins = float("".join(c for c in resto if c.isdigit() or c == ".") or "5")
    except ValueError:
        mins = 5.0
    if mins <= 0:
        mins = 5.0
    ctx.scheduler.schedule_in(mensaje, mins, kind="recordatorio")
    ctx.say(ctx.persona.recordatorio_creado(mensaje, mins))
    ctx.registrar_actividad(f"Programó recordatorio: {mensaje}")


def _recordar_fecha(ctx, m):
    texto = (m.text.replace("recuérdame", "").replace("recuerdame", "")
             .replace("recuerda", "").strip())
    mensaje = texto
    texto_fecha = texto
    for marca in _MARCAS_FECHA:
        idx = texto.find(marca)
        if idx > 0:
            mensaje = texto[:idx].strip()
            texto_fecha = texto[idx:].strip()
            break
    else:
        match = re.search(r"\d{1,2}\s+de\s+\w+", texto)
        if match:
            idx = match.start()
            mensaje = texto[:idx].strip()
            texto_fecha = texto[idx:].strip()

    if not mensaje.strip():
        ctx.say("No entendí qué quieres que recuerde. Di: recuerda [cosa] mañana.")
        return
    ctx.recordatorios.agregar(mensaje, texto_fecha)


def _listar(ctx, m):
    ctx.recordatorios.listar()


def _completar(ctx, m):
    for kw in ("recordatorio completado ", "marcar recordatorio ", "completar recordatorio "):
        if kw in m.text:
            texto = m.text.split(kw, 1)[-1].strip()
            if texto:
                ctx.recordatorios.completar(texto)
            return


class RemindersSkill(Skill):
    name = "reminders"

    def intents(self, ctx):
        return [
            IntentSpec(name="rem.minutos", priority=360,
                       matcher=all_of(contains_any(("recuerda", "recuérdame", "recuerdame")),
                                      contains_any(("minuto",))),
                       handler=_recordar_minutos,
                       examples=("recuerda llamar a Ana en 10 minutos",)),
            IntentSpec(name="rem.fecha", priority=370,
                       matcher=contains_any(("recuerda", "recuérdame", "recuerdame")),
                       handler=_recordar_fecha,
                       examples=("recuerda pagar la luz el 15 de julio",
                                 "recuérdame la cita mañana")),
            IntentSpec(name="rem.listar", priority=380,
                       matcher=contains_any(("mis recordatorios", "lista de recordatorios",
                                             "qué recordatorios tengo", "que recordatorios tengo",
                                             "recordatorios pendientes")),
                       handler=_listar, examples=("mis recordatorios",)),
            IntentSpec(name="rem.completar", priority=390,
                       matcher=contains_any(("recordatorio completado ", "marcar recordatorio ",
                                             "completar recordatorio ")),
                       handler=_completar, examples=("recordatorio completado pagar luz",)),
        ]
