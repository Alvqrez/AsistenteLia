#!/usr/bin/env python3
"""
agenda.py — Inteligencia personal: agenda del día, prioridad y enfoque.

No inventa datos: combina las fuentes reales que Lia ya mantiene —
pendientes (mod_memoria), recordatorios de hoy (mod_recordatorios),
exámenes (plugin universidad) y metas/proyectos (mod_vida) — y las
resume con un criterio de prioridad simple y explicable:

    examen a ≤3 días  >  recordatorio de hoy  >  primer pendiente  >  meta
"""

from __future__ import annotations

import logging

from core.intent import IntentSpec
from core.matchers import contains_any
from core.skill import Skill
from plugins.universidad.examenes import examenes_proximos

logger = logging.getLogger("lia.plugin.agenda")


def _datos(ctx):
    pendientes = []
    recordatorios_hoy = []
    metas = []
    try:
        pendientes = ctx.memoria.obtener_pendientes()
    except Exception as ex:
        logger.debug("Sin pendientes: %s", ex)
    try:
        recordatorios_hoy = ctx.recordatorios.obtener_hoy()
    except Exception as ex:
        logger.debug("Sin recordatorios: %s", ex)
    try:
        metas = ctx.vida.obtener_metas()
    except Exception as ex:
        logger.debug("Sin metas: %s", ex)
    try:
        examenes = examenes_proximos()
    except Exception as ex:
        logger.debug("Sin exámenes: %s", ex)
        examenes = []
    return pendientes, recordatorios_hoy, metas, examenes


def _agenda_dia(ctx, m):
    pendientes, recs, metas, examenes = _datos(ctx)
    if not any((pendientes, recs, metas, examenes)):
        ctx.say("Tu día está despejado: sin pendientes, recordatorios ni exámenes. "
                "Buen momento para avanzar en tus metas.")
        return

    partes = []
    if recs:
        msgs = ", ".join(r.get("mensaje", "") for r in recs[:3])
        partes.append(f"para hoy tienes {len(recs)} recordatorio{'s' if len(recs) != 1 else ''}: {msgs}")
    if examenes:
        materia, _, dias = examenes[0]
        cuando = "hoy" if dias == 0 else ("mañana" if dias == 1 else f"en {dias} días")
        partes.append(f"tu siguiente examen es {materia}, {cuando}")
    if pendientes:
        top = ", ".join(pendientes[:3])
        partes.append(f"tienes {len(pendientes)} pendiente{'s' if len(pendientes) != 1 else ''}; los primeros: {top}")
    if metas:
        partes.append(f"y {len(metas)} meta{'s' if len(metas) != 1 else ''} activa{'s' if len(metas) != 1 else ''}")

    ctx.say("Tu agenda: " + ". ".join(partes) + ".")
    ctx.registrar_actividad("Consultó la agenda del día")


def _prioridad(ctx, m):
    pendientes, recs, metas, examenes = _datos(ctx)

    if examenes and examenes[0][2] <= 3:
        materia, _, dias = examenes[0]
        cuando = "hoy" if dias == 0 else ("mañana" if dias == 1 else f"en {dias} días")
        ctx.say(f"Tu prioridad es estudiar para el examen de {materia}: es {cuando}.")
    elif recs:
        ctx.say(f"Tu prioridad de hoy: {recs[0].get('mensaje', 'tu recordatorio de hoy')}.")
    elif pendientes:
        ctx.say(f"Tu prioridad: {pendientes[0]}. Es lo primero de tu lista de pendientes.")
    elif metas:
        ctx.say(f"Sin urgencias hoy. Te sugiero avanzar en tu meta: {metas[0]}.")
    else:
        ctx.say("No tienes nada urgente registrado. Día libre de verdad.")
    ctx.registrar_actividad("Consultó su prioridad")


def _objetivos(ctx, m):
    # Delegado: las metas son la fuente de verdad de los objetivos.
    ctx.vida.leer_metas()


def _modo_profundo(ctx, m):
    # Trabajo profundo: bloqueo de sitios distractores durante 90 minutos.
    ctx.say("Modo profundo: 90 minutos sin distracciones. Concéntrate, yo vigilo el reloj.")
    ctx.focus.activar(90)
    ctx.registrar_actividad("Inició modo profundo (90 min)")


class AgendaSkill(Skill):
    name = "agenda"
    category = "productividad"

    def intents(self, ctx):
        return [
            IntentSpec(
                name="prod.agenda_dia", priority=282,
                matcher=contains_any(("agenda mi día", "agenda mi dia",
                                      "agéndame el día", "agendame el dia",
                                      "plan del día", "plan del dia",
                                      "cómo viene mi día", "como viene mi dia",
                                      "organiza mi día", "organiza mi dia")),
                handler=_agenda_dia,
                description="Resume tu día: recordatorios, exámenes, pendientes y metas",
                aliases=("agenda mi día", "plan del día"),
                examples=("agenda mi día",),
            ),
            IntentSpec(
                name="prod.prioridad", priority=283,
                matcher=contains_any(("cuál es mi prioridad", "cual es mi prioridad",
                                      "mi prioridad", "qué debería hacer hoy",
                                      "que deberia hacer hoy", "qué hago primero",
                                      "que hago primero", "en qué debería enfocarme",
                                      "en que deberia enfocarme", "en qué me enfoco",
                                      "en que me enfoco")),
                handler=_prioridad,
                description="Te dice en qué enfocarte ahora (exámenes > recordatorios > pendientes > metas)",
                aliases=("cuál es mi prioridad", "qué debería hacer hoy",
                         "en qué debería enfocarme"),
                examples=("cuál es mi prioridad", "en qué me enfoco"),
            ),
            IntentSpec(
                # 284: antes de rem.minutos/fecha (360/370), que capturan "recuérdame".
                name="prod.objetivos", priority=284,
                matcher=contains_any(("recuérdame mis objetivos", "recuerdame mis objetivos",
                                      "mis objetivos", "recuérdame mis metas",
                                      "recuerdame mis metas")),
                handler=_objetivos,
                description="Te recuerda tus objetivos (metas activas)",
                aliases=("recuérdame mis objetivos", "mis objetivos"),
                examples=("recuérdame mis objetivos",),
            ),
            IntentSpec(
                name="prod.modo_profundo", priority=178,
                matcher=contains_any(("modo profundo", "inicia modo profundo",
                                      "trabajo profundo", "deep work",
                                      "concentración máxima", "concentracion maxima")),
                handler=_modo_profundo,
                description="90 minutos de trabajo profundo: bloquea sitios distractores",
                aliases=("modo profundo", "inicia modo profundo"),
                examples=("inicia modo profundo",),
            ),
        ]
