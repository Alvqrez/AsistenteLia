#!/usr/bin/env python3
"""
aliases.py — Gestión de aliases personales del usuario.

Permite al usuario registrar sus propias frases cortas que el normalizer
expandirá automáticamente antes de enrutar. Los aliases viven en
config["aliases_usuario"] y el normalizer (normalizer.py) los aplica
en cada comando entrante.

Ejemplos:
  "Lia, crea alias fluter para abre el proyecto de flutter"
  → cuando diga "fluter", Lia ejecuta "abre el proyecto de flutter"

  "Lia, cuando diga fluter abre el proyecto de flutter"
  → mismo efecto

Los aliases son de sustitución exacta (texto completo). Para frases
compuestas que incluyen el alias, usar la frase completa como alias.
"""

from __future__ import annotations

import logging

from core.intent import IntentSpec
from core.matchers import contains_any, starts_with
from core.skill import Skill

logger = logging.getLogger("lia.skill.aliases")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_aliases(ctx) -> dict:
    return ctx.config.get("aliases_usuario", {}) or {}


def _save_alias(ctx, frase: str, comando: str) -> None:
    aliases = _get_aliases(ctx)
    aliases[frase.lower().strip()] = comando.strip()
    ctx.config.set("aliases_usuario", aliases)
    ctx.say(f"Listo. Cuando digas '{frase}', ejecutaré '{comando}'.")
    ctx.registrar_actividad(f"Alias creado: '{frase}' → '{comando}'")


# ── Handlers ──────────────────────────────────────────────────────────────────

def _crear_alias(ctx, m):
    """
    Soporta dos formas:
      "crea alias FRASE para COMANDO"  — parsea con " para " como separador
      "crea alias"                     — flujo interactivo con pending
    """
    resto = m.slots.get("resto", "").strip()

    # Forma directa: "crea alias fluter para abre el proyecto"
    if " para " in resto:
        partes = resto.split(" para ", 1)
        frase, comando = partes[0].strip(), partes[1].strip()
        if frase and comando:
            _save_alias(ctx, frase, comando)
            return

    # "cuando diga X haz Y" / "cuando diga X ejecuta Y"
    if resto and " haz " in resto:
        partes = resto.split(" haz ", 1)
        frase, comando = partes[0].strip(), partes[1].strip()
        if frase and comando:
            _save_alias(ctx, frase, comando)
            return
    if resto and " ejecuta " in resto:
        partes = resto.split(" ejecuta ", 1)
        frase, comando = partes[0].strip(), partes[1].strip()
        if frase and comando:
            _save_alias(ctx, frase, comando)
            return

    # Flujo interactivo si no se pudo parsear directo
    if resto:
        frase_candidata = resto

        def _on_comando(comando: str) -> None:
            _save_alias(ctx, frase_candidata, comando)

        ctx.ask(
            f"¿Y qué debo hacer cuando digas '{frase_candidata}'?",
            _on_comando,
        )
    else:
        def _on_frase(frase: str) -> None:
            def _on_comando(comando: str) -> None:
                _save_alias(ctx, frase, comando)
            ctx.ask(f"¿Qué debe hacer Lia cuando digas '{frase}'?", _on_comando)

        ctx.ask("¿Cuál es la frase que quieres usar como alias?", _on_frase)


def _listar_aliases(ctx, m):
    aliases = _get_aliases(ctx)
    if not aliases:
        ctx.say("No tienes aliases personales. Crea uno con 'crea alias'.")
        return
    lineas = [f"'{k}' → '{v}'" for k, v in aliases.items()]
    ctx.say(f"Tienes {len(lineas)} alias{'es' if len(lineas) != 1 else ''}: {'; '.join(lineas)}.")


def _borrar_alias(ctx, m):
    frase = m.slots.get("resto", "").strip().lower()
    if not frase:
        def _on_frase(f: str) -> None:
            _borrar_con_frase(ctx, f.strip().lower())
        ctx.ask("¿Qué alias quieres borrar?", _on_frase)
        return
    _borrar_con_frase(ctx, frase)


def _borrar_con_frase(ctx, frase: str) -> None:
    aliases = _get_aliases(ctx)
    if frase not in aliases:
        ctx.say(f"No encontré un alias para '{frase}'.")
        return
    del aliases[frase]
    ctx.config.set("aliases_usuario", aliases)
    ctx.say(f"Alias '{frase}' eliminado.")
    ctx.registrar_actividad(f"Alias eliminado: '{frase}'")


# ── Skill ─────────────────────────────────────────────────────────────────────

class AliasesSkill(Skill):
    name = "aliases"
    category = "configuración"

    def intents(self, ctx):
        return [
            IntentSpec(
                name="aliases.crear",
                priority=360,
                matcher=starts_with((
                    "crea alias ",
                    "nuevo alias ",
                    "agrega alias ",
                    "cuando diga ",
                    "crear alias ",
                )),
                handler=_crear_alias,
                description="Crea un alias personal: frase corta que Lia expande automáticamente",
                aliases=("crea alias fluter para abre el proyecto de flutter",),
                examples=(
                    "crea alias fluter para abre el proyecto de flutter",
                    "cuando diga mi correo ejecuta abre gmail",
                ),
            ),
            IntentSpec(
                name="aliases.listar",
                priority=700,
                matcher=contains_any((
                    "lista mis aliases", "mis aliases", "ver aliases",
                    "qué aliases tengo", "que aliases tengo",
                    "lista aliases", "mostrar aliases",
                )),
                handler=_listar_aliases,
                description="Lista todos los aliases personales configurados",
                aliases=("mis aliases",),
                examples=("lista mis aliases",),
            ),
            IntentSpec(
                name="aliases.borrar",
                priority=400,
                matcher=starts_with((
                    "borra alias ", "elimina alias ", "quita alias ",
                    "borrar alias ", "eliminar alias ",
                )),
                handler=_borrar_alias,
                description="Elimina un alias personal",
                aliases=("borra alias fluter",),
                examples=("borra alias fluter",),
            ),
        ]
