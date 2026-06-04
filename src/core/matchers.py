#!/usr/bin/env python3
"""
matchers.py — Fábricas de `Matcher` reutilizables.

Resuelve la violación DRY del antiguo `Lia.py`, donde el patrón
`cmd_l.split(trigger, 1)[-1].strip()` se repetía ~30 veces y los conjuntos de
sinónimos se comprobaban a mano una y otra vez.

Cada función devuelve un `Matcher` (cmd_lower -> dict|None) que las skills
componen declarativamente al registrar sus intenciones.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional


def contains_any(palabras: Iterable[str]) -> "callable":
    """Coincide si el texto contiene cualquiera de las subcadenas dadas."""
    palabras = tuple(palabras)

    def _m(cmd: str) -> Optional[dict]:
        return {} if any(p in cmd for p in palabras) else None

    return _m


def contains_word_any(palabras: Iterable[str]) -> "callable":
    """
    Como contains_any, pero exige que la palabra/frase aparezca con límites de
    palabra (\\b). Evita falsos positivos por subcadena, p.ej. que el sinónimo
    "ram" dispare con "ra**ram**a" o "p**ram**ide".
    """
    patrones = [re.compile(rf"\b{re.escape(p)}\b") for p in palabras]

    def _m(cmd: str) -> Optional[dict]:
        return {} if any(rx.search(cmd) for rx in patrones) else None

    return _m


def equals_any(palabras: Iterable[str]) -> "callable":
    """Coincide solo si el texto (ya en minúsculas, stripeado) es exactamente una."""
    opciones = {p.lower() for p in palabras}

    def _m(cmd: str) -> Optional[dict]:
        return {} if cmd.strip() in opciones else None

    return _m


def starts_with(prefijos: Iterable[str], slot: str = "resto") -> "callable":
    """
    Coincide si el texto empieza con alguno de los prefijos; extrae el resto
    en `slot`. Sustituye al repetido `split(trigger, 1)[-1]`.
    """
    prefijos = tuple(prefijos)

    def _m(cmd: str) -> Optional[dict]:
        for p in prefijos:
            if cmd.startswith(p):
                return {slot: cmd[len(p):].strip(" ,.-:")}
        return None

    return _m


def after_trigger(triggers: Iterable[str], slot: str = "resto",
                  require_text: bool = False) -> "callable":
    """
    Coincide si el texto contiene cualquiera de los triggers (no necesariamente
    al inicio) y extrae lo que va DESPUÉS del primero encontrado en `slot`.

    require_text=True ⇒ solo coincide si queda texto tras el trigger.
    """
    triggers = tuple(triggers)

    def _m(cmd: str) -> Optional[dict]:
        for t in triggers:
            if t in cmd:
                resto = cmd.split(t, 1)[-1].strip(" ,.-:")
                if require_text and not resto:
                    return None
                return {slot: resto}
        return None

    return _m


def regex(pattern: str, flags: int = 0) -> "callable":
    """Coincide con una expresión regular; expone los grupos nombrados como slots."""
    rx = re.compile(pattern, flags)

    def _m(cmd: str) -> Optional[dict]:
        m = rx.search(cmd)
        if not m:
            return None
        return dict(m.groupdict())

    return _m


def all_of(*matchers) -> "callable":
    """Composición AND: coincide si todos coinciden; fusiona sus slots."""

    def _m(cmd: str) -> Optional[dict]:
        slots: dict = {}
        for mt in matchers:
            res = mt(cmd)
            if res is None:
                return None
            slots.update(res)
        return slots

    return _m


def without(matcher, palabras_prohibidas: Iterable[str]) -> "callable":
    """
    Envuelve un matcher para que NO coincida si el texto contiene ciertas
    palabras. Reproduce guardas como `_SINONIMOS_VSCODE and "abre" not in cmd_l`.
    """
    prohibidas = tuple(palabras_prohibidas)

    def _m(cmd: str) -> Optional[dict]:
        if any(p in cmd for p in prohibidas):
            return None
        return matcher(cmd)

    return _m


def first_number(cmd: str, default: int = 25) -> int:
    """Extrae el primer entero del texto; útil para 'pomodoro 30', 'enfoque 50'."""
    for token in cmd.split():
        if token.isdigit():
            return int(token)
    return default
