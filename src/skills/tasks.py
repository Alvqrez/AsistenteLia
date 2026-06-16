#!/usr/bin/env python3
"""
tasks.py — Pendientes y notas. Delega en `mod_memoria` (MemoryTools), que
persiste en Pendientes.md (Obsidian) y lia_memoria.json.
"""

from __future__ import annotations

import logging

from core.intent import IntentSpec
from core.matchers import all_of, any_of, contains_any, starts_with
from core.skill import Skill

logger = logging.getLogger("lia.skill.tasks")

_SINONIMOS_PENDIENTES = (
    "pendientes", "mis pendientes", "qué tengo pendiente", "que tengo pendiente",
    "mis tareas", "lista de tareas", "lista tareas", "lista mis tareas",
    "qué debo hacer", "que debo hacer",
    "qué tengo que hacer", "que tengo que hacer", "dime mis pendientes",
    "mis compromisos", "en qué andaba", "en que andaba",
)
_VERBOS_ANOTAR = ("anota", "apunta", "agrega pendiente", "agrega tarea",
                  "agrega", "añade pendiente", "añade")
_KW_COMPLETAR = ("lista", "completada", "hecha", "terminada", "completa", "done")
_REFERENCIAS_ULTIMO = ("eso", "esa", "ese", "la última", "la ultima",
                       "el último", "el ultimo", "lo último", "lo ultimo")


def _pendientes(ctx, m):
    ctx.memoria.decir_pendientes()


def _anotar(ctx, m):
    for verbo in _VERBOS_ANOTAR:
        if verbo in m.text:
            texto = m.text.split(verbo, 1)[-1].strip().strip(",.-: ")
            if texto:
                ctx.memoria.agregar_pendiente(texto)
                ctx.contexto.registrar_pendiente(texto)
            else:
                ctx.say("¿Qué quieres que anote?")
            return


def _completar(ctx, m):
    for kw in _KW_COMPLETAR:
        if kw in m.text:
            tarea = (m.text.replace("tarea", "").replace("pendiente", "")
                     .replace(kw, "").strip().strip(",.-: "))
            # Referencia a "lo último" en vez del texto exacto del pendiente:
            # reutiliza el mismo patrón que ya existe para apps/urls/archivos
            # en ContextoConversacional, extendido a pendientes.
            if not tarea or tarea in _REFERENCIAS_ULTIMO:
                tarea = getattr(ctx.contexto, "ultimo_pendiente", None)
                if not tarea:
                    ctx.say("No sé a qué pendiente te refieres. Dime cuál.")
                    return
            ctx.memoria.completar_tarea(tarea)
            return


def _nota(ctx, m):
    resto = m.text[5:].strip()  # tras "nota "
    partes = resto.split(" ", 1)
    if len(partes) == 2:
        ctx.memoria.guardar_nota(partes[0], partes[1])
    else:
        ctx.say("Di: nota [clave] [contenido].")


def _leer_nota(ctx, m):
    clave = m.text.replace("recuerda nota", "").replace("lee nota", "").strip()
    ctx.memoria.obtener_nota(clave)


def _listar_notas(ctx, m):
    ctx.memoria.listar_notas()


class TasksSkill(Skill):
    name = "tasks"
    category = "tareas"

    def intents(self, ctx):
        return [
            IntentSpec(name="tasks.pendientes", priority=290,
                       matcher=contains_any(_SINONIMOS_PENDIENTES), handler=_pendientes,
                       description="Lee tus pendientes (sincronizados con Obsidian)",
                       aliases=("pendientes", "mis tareas"),
                       examples=("pendientes", "mis tareas", "qué debo hacer")),
            IntentSpec(name="tasks.anotar", priority=300,
                       matcher=contains_any(_VERBOS_ANOTAR), handler=_anotar,
                       description="Anota un pendiente nuevo",
                       aliases=("anota comprar pan",),
                       examples=("anota comprar pan", "apunta llamar a Ana")),
            IntentSpec(name="tasks.completar", priority=310,
                       # Dispara con "tarea"/"pendiente" explícito (caso original)
                       # O con una referencia a "lo último" ("completa eso"),
                       # que _completar resuelve vía ContextoConversacional.
                       matcher=any_of(
                           all_of(contains_any(_KW_COMPLETAR),
                                  contains_any(("tarea", "pendiente"))),
                           all_of(contains_any(_KW_COMPLETAR),
                                  contains_any(_REFERENCIAS_ULTIMO)),
                       ),
                       handler=_completar,
                       description="Marca una tarea como completada (por nombre o "
                                   "con 'completa eso' / 'la última' tras anotarla)",
                       aliases=("tarea comprar pan lista", "completa eso"),
                       examples=("tarea comprar pan lista", "completa eso")),
            IntentSpec(name="tasks.nota", priority=320,
                       matcher=starts_with(("nota ",)), handler=_nota,
                       description="Guarda una nota clave-valor",
                       aliases=("nota wifi clave1234",),
                       examples=("nota wifi clave1234",)),
            IntentSpec(name="tasks.leer_nota", priority=330,
                       matcher=contains_any(("recuerda nota ", "lee nota ")),
                       handler=_leer_nota,
                       description="Lee una nota guardada por su clave",
                       aliases=("recuerda nota wifi",),
                       examples=("recuerda nota wifi",)),
            IntentSpec(name="tasks.listar_notas", priority=340,
                       matcher=contains_any(("lista notas", "mis notas")),
                       handler=_listar_notas,
                       description="Lista todas tus notas guardadas",
                       aliases=("mis notas",),
                       examples=("mis notas",)),
        ]
