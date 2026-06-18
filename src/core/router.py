#!/usr/bin/env python3
"""
router.py — IntentRouter (sustituye el `if/elif` de 620 líneas).

Las skills registran `IntentSpec`s. El router los evalúa **en orden de
prioridad ascendente** y despacha el primero que coincide. Esto reproduce con
exactitud la semántica del antiguo parser (donde el orden importaba y había
guardas para resolver colisiones) pero ahora es modular y extensible (OCP):
agregar una intención no requiere tocar este archivo.

Flujo de `handle_text`:
    1. Las intenciones `global_override=True` (kill switches como "aborta") se
       evalúan primero, sin importar el estado de la conversación.
    2. Si hay una acción pendiente (Lia esperaba un dato), la respuesta la completa.
    3. Se busca la intención de mayor prioridad que coincida y se despacha.
    4. Si nada coincide y hay un `IntentResolver` (IA) configurado, se delega.
    5. Si todo falla, fallback de "no entendí".

El resolutor por IA (Fase 6) es opcional e inyectable; hoy queda en None.
"""

from __future__ import annotations

import logging
from typing import Optional, Protocol

from core.event_bus import Event
from core.intent import IntentMatch, IntentSpec
from core.normalizer import normalize

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

    @property
    def _global_specs(self) -> list[IntentSpec]:
        return [s for s in self.specs if s.global_override]

    # ── Matching ─────────────────────────────────────────────────────────────
    def match(self, cmd_lower: str, specs: Optional[list[IntentSpec]] = None) -> Optional[IntentMatch]:
        """Devuelve la primera intención (por prioridad) que coincide, o None."""
        for spec in (specs if specs is not None else self.specs):
            try:
                slots = spec.matcher(cmd_lower)
            except Exception as ex:
                logger.warning("Matcher de '%s' falló: %s", spec.name, ex)
                continue
            if slots is not None:
                return IntentMatch(spec=spec, text=cmd_lower, slots=slots)
        return None

    def _dispatch(self, ctx, match: IntentMatch) -> None:
        """Ejecuta el handler de una intención ya resuelta y publica los eventos."""
        cmd_l = match.text
        ctx.bus.publish(Event.INTENT, {"name": match.name, "text": cmd_l})
        try:
            match.spec.handler(ctx, match)
        except Exception as ex:
            logger.error("Handler de '%s' falló: %s", match.name, ex, exc_info=True)
            ctx.bus.publish(Event.COMMAND_FAILED,
                            {"name": match.name, "text": cmd_l, "error": str(ex)})
            ctx.say(ctx.persona.error_generico("completar esa acción"))
        else:
            ctx.bus.publish(Event.COMMAND_EXECUTED,
                            {"name": match.name, "text": cmd_l,
                             "skill": match.spec.skill,
                             "category": match.spec.category})

    # ── Compound splitting ────────────────────────────────────────────────────
    def _try_split_compound(self, text: str) -> Optional[list[str]]:
        """
        Intenta dividir 'A y B' en [A, B] solo si TODAS las partes coinciden
        con intents conocidos. Elimina falsos positivos porque el check de match
        es el mismo router (sin efectos secundarios).

        Separadores probados en orden de especificidad (los largos primero para
        no cortar " y también" como " y " + "también").
        """
        separators = [
            " y también ",
            " y luego ",
            " y después ",
            " luego ",
            " después ",
            " y ",
        ]
        for sep in separators:
            if sep not in text:
                continue
            parts = [p.strip() for p in text.split(sep) if p.strip()]
            if len(parts) >= 2 and all(self.match(p) is not None for p in parts):
                return parts
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

        # Normalización: correcciones fonéticas STT + aliases del usuario.
        # Se aplica antes de TODO el ruteo para que kill-switches, pending y
        # matchers reciban siempre texto limpio y canónico.
        cmd_l = normalize(raw, ctx.config)

        # 1) Kill switches globales (p.ej. "aborta"): se evalúan SIEMPRE primero,
        # incluso con una acción pendiente, porque el usuario debe poder
        # interrumpir a Lia sin importar en qué estado de la conversación esté.
        if self._global_specs:
            global_match = self.match(cmd_l, specs=self._global_specs)
            if global_match is not None:
                self._dispatch(ctx, global_match)
                return True

        # 2) Acción pendiente: la respuesta del usuario la completa.
        # Se pasa el texto normalizado (no raw) para que correcciones fonéticas
        # también apliquen en respuestas de seguimiento.
        if ctx.has_pending():
            ctx.resolve_pending(cmd_l)
            return True

        # 3a) Comandos compuestos: "abre spotify y sube el volumen al 70".
        # Solo divide si AMBAS partes matchean intents conocidos (sin efectos
        # secundarios). Si no, cae al matching normal (3b).
        compound_parts = self._try_split_compound(cmd_l)
        if compound_parts:
            for part in compound_parts:
                m = self.match(part)
                if m is not None:
                    self._dispatch(ctx, m)
            return True

        # 3b) Intención determinista única.
        match = self.match(cmd_l)
        if match is not None:
            self._dispatch(ctx, match)
            return True

        # 4) Resolutor por IA (futuro; hoy None).
        if self.ai_resolver is not None:
            try:
                ai_match = self.ai_resolver.resolve(cmd_l, self.specs)
            except Exception as ex:
                logger.warning("Resolutor IA falló: %s", ex)
                ai_match = None
            if ai_match is not None:
                ai_match.spec.handler(ctx, ai_match)
                return True

        # 5) Fallback: no entendí.
        if self.on_unhandled is not None:
            self.on_unhandled(cmd_l)
        return False
