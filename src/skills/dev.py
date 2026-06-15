#!/usr/bin/env python3
"""
dev.py — Productividad de programación (Fase 10): Git, VS Code, docs y scaffolding.

Delega en `mod_dev` (DevTools) y `mod_sistema`. Punto de extensión para Fase 10
avanzada (PRs, auditorías, integración con GitHub/Claude Code): basta añadir
intenciones aquí.
"""

from __future__ import annotations

import logging

from core.intent import IntentSpec
from core.matchers import contains_any
from core.skill import Skill

logger = logging.getLogger("lia.skill.dev")


def _git_status(ctx, m): ctx.dev.estado_git()
def _git_push(ctx, m): ctx.dev.hacer_push()
def _git_pull(ctx, m): ctx.dev.hacer_pull()
def _git_log(ctx, m): ctx.dev.log_reciente()
def _ramas(ctx, m): ctx.dev.listar_ramas()
def _docs_python(ctx, m): ctx.dev.abrir_docs_python()
def _mdn(ctx, m): ctx.dev.abrir_mdn()
def _stackoverflow(ctx, m): ctx.dev.abrir_stackoverflow()


def _git_commit(ctx, m):
    mensaje = (m.text.replace("git commit", "").replace("haz commit", "")
               .replace("hacer commit", "").replace("-m", "").strip().strip('"\''))
    if mensaje:
        ctx.dev.hacer_commit(mensaje)
    else:
        ctx.ask("¿Cuál es el mensaje del commit?", lambda r: ctx.dev.hacer_commit(r))


def _nueva_rama(ctx, m):
    nombre = (m.text.replace("nueva rama", "").replace("crea rama", "")
              .replace("crear rama", "").strip())
    if nombre:
        ctx.dev.crear_rama(nombre)
    else:
        ctx.ask("¿Cómo se llamará la nueva rama?", lambda r: ctx.dev.crear_rama(r))


def _cambiar_rama(ctx, m):
    nombre = (m.text.replace("cambia rama", "").replace("cambiar rama", "")
              .replace("cambia a rama", "").replace("ve a rama", "")
              .replace("checkout", "").strip())
    if nombre:
        ctx.dev.cambiar_rama(nombre)
    else:
        ctx.ask("¿A qué rama quieres cambiar?", lambda r: ctx.dev.cambiar_rama(r))


def _clonar(ctx, m):
    url = (m.text.replace("clona", "").replace("clonar", "")
           .replace("git clone", "").strip())
    if url:
        ctx.dev.clonar_repositorio(url)
    else:
        ctx.ask("¿Cuál es la URL del repositorio a clonar?",
                lambda r: ctx.dev.clonar_repositorio(r))


def _vscode_en(ctx, m):
    cmd_l = m.text
    for kw in ("abre vscode en ", "abrir vscode en ", "code en "):
        if kw in cmd_l:
            carpeta = cmd_l.split(kw, 1)[-1].strip()
            ruta = ctx.sistema._resolver_carpeta_destino(carpeta)
            ctx.dev.abrir_vscode(ruta)
            return
    ctx.dev.abrir_vscode()


def _proyecto_react(ctx, m):
    cmd_l = m.text
    for kw in ("crea proyecto react en ", "crear proyecto react en ",
               "crea proyecto de react en ", "crea proyecto react ",
               "crear proyecto react ", "nuevo proyecto react en ",
               "nuevo proyecto react "):
        if kw in cmd_l:
            nombre = cmd_l.split(kw, 1)[-1].strip()
            if nombre:
                ctx.dev.crear_proyecto_react(nombre)
            else:
                ctx.ask("¿Cómo se va a llamar el proyecto React?",
                        lambda r: ctx.dev.crear_proyecto_react(r))
            return
    ctx.ask("¿Cómo se va a llamar el proyecto React?",
            lambda r: ctx.dev.crear_proyecto_react(r))


class DevSkill(Skill):
    name = "dev"
    category = "desarrollo"

    def intents(self, ctx):
        return [
            IntentSpec(name="dev.proyecto_react", priority=260,
                       matcher=contains_any(("proyecto react", "proyecto de react")),
                       handler=_proyecto_react,
                       description="Crea un proyecto React con Vite",
                       aliases=("crea proyecto react en documentos",),
                       examples=("crea proyecto react en documentos",)),
            IntentSpec(name="dev.vscode_en", priority=265,
                       matcher=contains_any(("abre vscode en", "abrir vscode en", "code en")),
                       handler=_vscode_en,
                       description="Abre VS Code en una carpeta concreta",
                       aliases=("abre vscode en mi-proyecto",),
                       examples=("abre vscode en mi-proyecto",)),
            IntentSpec(name="dev.git_status", priority=550,
                       matcher=contains_any(("git status", "estado del repo", "estado del git")),
                       handler=_git_status,
                       description="Muestra el estado del repositorio Git actual",
                       aliases=("git status", "estado del repo"),
                       examples=("git status",)),
            IntentSpec(name="dev.git_push", priority=560,
                       matcher=contains_any(("git push", "sube los cambios", "hacer push")),
                       handler=_git_push,
                       description="Hace push de los commits al remoto",
                       aliases=("git push", "sube los cambios"),
                       examples=("git push", "sube los cambios")),
            IntentSpec(name="dev.git_pull", priority=570,
                       matcher=contains_any(("git pull", "baja los cambios", "jala los cambios")),
                       handler=_git_pull,
                       description="Trae los cambios del remoto (pull)",
                       aliases=("git pull", "baja los cambios"),
                       examples=("git pull",)),
            IntentSpec(name="dev.git_log", priority=580,
                       matcher=contains_any(("git log", "últimos commits", "ultimos commits",
                                             "historial de commits")),
                       handler=_git_log,
                       description="Lee los últimos commits del repositorio",
                       aliases=("git log", "últimos commits"),
                       examples=("git log", "últimos commits")),
            IntentSpec(name="dev.git_commit", priority=590,
                       matcher=contains_any(("git commit", "haz commit", "hacer commit")),
                       handler=_git_commit,
                       description="Crea un commit con el mensaje que digas",
                       aliases=("haz commit",),
                       examples=('git commit "fix bug"',)),
            IntentSpec(name="dev.ramas", priority=600,
                       matcher=contains_any(("ramas", "listar ramas", "mis ramas")),
                       handler=_ramas,
                       description="Lista las ramas del repositorio",
                       aliases=("mis ramas",),
                       examples=("mis ramas",)),
            IntentSpec(name="dev.nueva_rama", priority=610,
                       matcher=contains_any(("nueva rama", "crea rama", "crear rama")),
                       handler=_nueva_rama,
                       description="Crea una rama nueva y cambia a ella",
                       aliases=("nueva rama feature-x",),
                       examples=("nueva rama feature-x",)),
            IntentSpec(name="dev.cambiar_rama", priority=620,
                       matcher=contains_any(("cambia rama", "cambiar rama", "cambia a rama",
                                             "ve a rama", "checkout")),
                       handler=_cambiar_rama,
                       description="Cambia a otra rama (checkout)",
                       aliases=("cambia rama main",),
                       examples=("cambia rama main",)),
            IntentSpec(name="dev.clonar", priority=630,
                       matcher=contains_any(("clona ", "clonar ", "git clone")),
                       handler=_clonar,
                       description="Clona un repositorio desde una URL",
                       aliases=("clona un repositorio",),
                       examples=("clona https://github.com/...",)),
            IntentSpec(name="dev.docs_python", priority=650,
                       matcher=contains_any(("docs python", "documenta python",
                                             "documentación python")),
                       handler=_docs_python,
                       description="Abre la documentación oficial de Python",
                       aliases=("docs python",),
                       examples=("docs python",)),
            IntentSpec(name="dev.mdn", priority=660,
                       matcher=contains_any(("mdn ", "mdn")), handler=_mdn,
                       description="Abre MDN Web Docs",
                       aliases=("mdn",),
                       examples=("mdn",)),
            IntentSpec(name="dev.stackoverflow", priority=670,
                       matcher=contains_any(("stackoverflow", "stack overflow")),
                       handler=_stackoverflow,
                       description="Abre Stack Overflow",
                       aliases=("stackoverflow",),
                       examples=("stackoverflow",)),
        ]
