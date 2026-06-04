#!/usr/bin/env python3
"""
router.py — IntentRouter (sustituye el `if/elif` de 620 líneas).

Las skills registran `IntentSpec`s. El router los evalúa **en orden de
prioridad ascendente** y despacha el primero que coincide. Esto reproduce con
exactitud la semántica del antiguo parser (donde el orden importaba y había
guardas para resolver colisiones) pero ahora es modular y extensible (OCP):
agregar una intención no requiere tocar este archivo.

Flujo de `handle_text`:
    1. Si hay una acción pendiente (Lia esperaba un dato), la respuesta la completa.
    2. Se busca la intención de mayor prioridad que coincida y se despacha.
    3. Si nada coincide y hay un `IntentResolver` (IA) configurado, se delega.
    4. Si todo falla, fallback de "no entendí".

El resolutor por IA (Fase 6) es opcional e inyectable; hoy queda en None.
"""

from __future__ import annotations

import logging
from typing import Optional, Protocol

from core.intent import IntentMatch, IntentSpec

logger = logging.getLogger("lia.router")


class IntentResolver(Protocol):
    """Contrato para un resolutor de intenciones por IA (Fase 6, futuro)."""

    def resolve(self, text: str, specs: list[IntentSpec]) -> Optional[IntentMatch]:
        ...


class IntentRouter:
    def __init__(self, ctx, ai_resolver: Optional[IntentResolver] = None) -> None:
        self.ctx = ctx
        self._specs: list[IntentSpec] = []
        self._sorted = True
        self.ai_resolver = ai_resolver
        # Callback opcional de fallback cuando nada coincide (lo pone el kernel).
        self.on_unhandled = None

    # ── Registro ───────────────────────────────────────────────────────────
    def register(self, spec: IntentSpec) -> None:
        self._specs.append(spec)
        self._sorted = False

    def register_many(self, specs) -> None:
        for s in specs:
            self.register(s)

    @property
    def specs(self) -> list[IntentSpec]:
        if not self._sorted:
            self._specs.sort(key=lambda s: s.priority)
            self._sorted = True
        return self._specs

    # ── Matching ─────────────────────────────────────────────────────────────
    def match(self, cmd_lower: str) -> Optional[IntentMatch]:
        """Devuelve la primera intención (por prioridad) que coincide, o None."""
        for spec in self.specs:
            try:
                slots = spec.matcher(cmd_lower)
            except Exception as ex:
                logger.warning("Matcher de '%s' falló: %s", spec.name, ex)
                continue
            if slots is not None:
                return IntentMatch(spec=spec, text=cmd_lower, slots=slots)
        return None

    # ── Despacho ───────────────────────────────────────────────────────────
    def handle_text(self, raw: str) -> bool:
        """
        Procesa un comando ya limpio (sin palabra de activación).
        Devuelve True si algo lo atendió.
        """
        if not raw or not raw.strip():
            return False

        ctx = self.ctx

        # 1) Acción pendiente: la respuesta del usuario la completa.
        if ctx.has_pending():
            ctx.resolve_pending(raw)
            return True

        cmd_l = raw.lower().strip()

        # 2) Intención determinista.
        match = self.match(cmd_l)
        if match is not None:
            ctx.bus.publish("intent", {"name": match.name, "text": cmd_l})
            try:
                match.spec.handler(ctx, match)
            except Exception as ex:
                logger.error("Handler de '%s' falló: %s", match.name, ex, exc_info=True)
                ctx.say(ctx.persona.error_generico("completar esa acción"))
            return True

        # 3) Resolutor por IA (futuro; hoy None).
        if self.ai_resolver is not None:
            try:
                ai_match = self.ai_resolver.resolve(cmd_l, self.specs)
            except Exception as ex:
                logger.warning("Resolutor IA falló: %s", ex)
                ai_match = None
            if ai_match is not None:
                ai_match.spec.handler(ctx, ai_match)
                return True

        # 4) Fallback: no entendí.
        if self.on_unhandled is not None:
            self.on_unhandled(cmd_l)
        return False
