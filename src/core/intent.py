#!/usr/bin/env python3
"""
intent.py — Primitivas del sistema de intenciones (Fase 5).

Una *intención* es "lo que el usuario quiere" con independencia de la frase
exacta. "abre Spotify", "pon Spotify" y "quiero escuchar música" son la misma
intención.

Diseño preparado para IA (Fase 6): hoy el `matcher` es determinista
(palabras/regex), pero `IntentSpec` también declara `examples`, de modo que un
resolutor por IA pueda entrenarse/promptearse con esos ejemplos más adelante
sin tocar las skills.

    IntentSpec   — declaración de una intención (la registran las skills).
    IntentMatch  — resultado de hacer match: la intención + slots extraídos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

# matcher(cmd_lower) -> dict de slots si coincide, o None si no.
# Devolver {} cuenta como coincidencia sin slots.
Matcher = Callable[[str], Optional[dict]]

# handler(ctx, match) -> None. `ctx` es el AssistantContext; `match` el IntentMatch.
Handler = Callable[["object", "IntentMatch"], None]


@dataclass(frozen=True)
class IntentSpec:
    """
    Declaración de una intención registrada por una skill.

    name        — identificador único, p.ej. "apps.abrir".
    matcher     — función que decide si un texto activa esta intención y extrae slots.
    handler     — función que ejecuta la acción.
    priority    — orden de evaluación (menor = se evalúa antes). Permite reproducir
                  con exactitud el orden del antiguo if/elif y resolver colisiones
                  (p.ej. "resumen personal" debe ganar a "resumen").
    description — qué hace el comando, en una línea. Alimenta el help dinámico
                  y la búsqueda de comandos; nunca se hardcodea en menús.
    category    — agrupación para el help ("desarrollo", "internet", ...). Si se
                  deja vacía, el registry hereda la `category` de la skill dueña.
    aliases     — frases canónicas que disparan la intención. Son metadata viva:
                  el CommandRegistry las usa para el help, la búsqueda y la
                  VALIDACIÓN de conflictos (cada alias debe rutear a su dueño).
    examples    — frases de ejemplo con slots; documentación viva y semilla NLU.
    skill       — nombre de la skill propietaria (lo rellena el registry).
    global_override — si True, el router la evalúa ANTES de resolver una acción
                  pendiente (ctx.has_pending()). Reservado para "kill switches"
                  tipo "aborta" que deben funcionar sin importar el estado de
                  la conversación. Usar con moderación: cada intención global
                  se evalúa en cada turno, incluso con pending activo.
    """
    name: str
    matcher: Matcher
    handler: Handler
    priority: int = 1000
    description: str = ""
    category: str = ""
    aliases: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    skill: str = ""
    global_override: bool = False


@dataclass
class IntentMatch:
    """Resultado de enrutar un texto a una intención."""
    spec: IntentSpec
    text: str
    slots: dict = field(default_factory=dict)
    score: float = 1.0

    @property
    def name(self) -> str:
        return self.spec.name

    def slot(self, key: str, default=None):
        return self.slots.get(key, default)
