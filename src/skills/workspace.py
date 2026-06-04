#!/usr/bin/env python3
"""
workspace.py — Contexto de trabajo: proyecto activo, ejecutar, abrir/cerrar lo
último, abortar. Delega en `mod_contexto` (ContextoConversacional).
"""

from __future__ import annotations

from core.intent import IntentSpec
from core.matchers import contains_any
from core.skill import Skill


def _ejecutar(ctx, m): ctx.contexto.ejecutar_ultimo()
def _que_hago(ctx, m): ctx.contexto.que_estoy_haciendo()
def _abrir_ultimo(ctx, m): ctx.contexto.abrir_ultimo()
def _cerrar_ultimo(ctx, m): ctx.contexto.cerrar_ultimo()
def _abortar(ctx, m): ctx.contexto.abortar()


def _abrir_proyecto(ctx, m):
    cmd_l = m.text
    for kw in ("abre el proyecto ", "abrir proyecto ", "proyecto activo "):
        if kw in cmd_l:
            nombre = cmd_l.split(kw, 1)[-1].strip()
            if nombre:
                ctx.contexto.abrir_proyecto(nombre)
            else:
                ctx.ask("¿Cuál proyecto quieres abrir?",
                        lambda r: ctx.contexto.abrir_proyecto(r))
            return
    ctx.ask("¿Cuál proyecto quieres abrir?", lambda r: ctx.contexto.abrir_proyecto(r))


class WorkspaceSkill(Skill):
    name = "workspace"

    def intents(self, ctx):
        return [
            IntentSpec(name="ws.ejecutar", priority=130,
                       matcher=contains_any(("ejecuta", "ejecutar el proyecto",
                                             "corre el proyecto", "inicia el proyecto")),
                       handler=_ejecutar, examples=("ejecuta", "corre el proyecto")),
            IntentSpec(name="ws.que_hago", priority=140,
                       matcher=contains_any(("qué estoy haciendo", "que estoy haciendo",
                                             "en qué proyecto estoy", "en que proyecto estoy",
                                             "qué tengo abierto", "que tengo abierto")),
                       handler=_que_hago, examples=("qué estoy haciendo",)),
            IntentSpec(name="ws.abrir_ultimo", priority=150,
                       matcher=contains_any(("abre lo último", "abre lo ultimo",
                                             "abre lo de antes", "vuelve a abrir")),
                       handler=_abrir_ultimo, examples=("abre lo último",)),
            IntentSpec(name="ws.cerrar_ultimo", priority=160,
                       matcher=contains_any(("cierra lo último", "cierra lo ultimo", "cierra eso")),
                       handler=_cerrar_ultimo, examples=("cierra lo último",)),
            IntentSpec(name="ws.abortar", priority=170,
                       matcher=contains_any(("abortar", "aborta todo",
                                             "cierra todo lo que abriste")),
                       handler=_abortar, examples=("abortar",)),
            IntentSpec(name="ws.abrir_proyecto", priority=210,
                       matcher=contains_any(("abre el proyecto", "abrir proyecto", "proyecto activo")),
                       handler=_abrir_proyecto, examples=("abre el proyecto lia",)),
        ]
