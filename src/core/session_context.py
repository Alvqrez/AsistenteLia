#!/usr/bin/env python3
"""
session_context.py — Estado de conversación de corta duración.

Mantiene contexto sobre lo que el usuario está haciendo en esta sesión.
Los handlers anotan claves ("last_app", "current_topic", "last_file") y
otros handlers las consultan para resolver ambigüedades.

Se limpia automáticamente tras TIMEOUT segundos de inactividad, de modo
que Lia no confunda contexto de una sesión anterior con la actual.

Claves estándar usadas por las skills:
  "last_app"       — última aplicación mencionada/abierta (str)
  "last_file"      — último archivo mencionado/creado (str)
  "current_topic"  — tema dominante de la conversación (str: "musica", "dev", ...)
  "last_search"    — última búsqueda realizada (str)
"""

from __future__ import annotations

import threading
import time
import logging

logger = logging.getLogger("lia.session")

TIMEOUT_SECONDS = 300  # 5 minutos de inactividad → limpiar


class SessionContext:
    def __init__(self, timeout: int = TIMEOUT_SECONDS) -> None:
        self._data: dict = {}
        self._timeout = timeout
        self._last_touch = time.monotonic()
        self._lock = threading.Lock()

    # ── Internos ──────────────────────────────────────────────────────────────
    def _maybe_expire(self) -> None:
        if time.monotonic() - self._last_touch > self._timeout:
            if self._data:
                logger.debug("Sesión expirada por inactividad — contexto limpiado")
            self._data.clear()

    # ── API pública ───────────────────────────────────────────────────────────
    def set(self, key: str, value) -> None:
        with self._lock:
            self._maybe_expire()
            self._data[key] = value
            self._last_touch = time.monotonic()

    def get(self, key: str, default=None):
        with self._lock:
            self._maybe_expire()
            return self._data.get(key, default)

    def touch(self) -> None:
        """Renueva el temporizador de expiración sin modificar datos."""
        with self._lock:
            self._last_touch = time.monotonic()

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def snapshot(self) -> dict:
        """Devuelve una copia del estado actual (para debugging/logging)."""
        with self._lock:
            self._maybe_expire()
            return dict(self._data)
