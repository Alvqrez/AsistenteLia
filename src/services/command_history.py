#!/usr/bin/env python3
"""
command_history.py — Historial de comandos ejecutados en la sesión actual.

Se suscribe al EventBus para registrar cada COMMAND_EXECUTED. No persiste
entre reinicios (solo memoria RAM) para mantenerlo simple y sin acoplamiento
con el sistema de archivos. La skill history_replay lo usa para "repite el
último comando" y "qué hice hoy".

Los comandos de tipo "history.*" no se registran para evitar bucles infinitos
si el usuario dice "repite el último" y el último fue "repite el último".
"""

from __future__ import annotations

import datetime
import logging
import threading
from collections import deque

from core.event_bus import Event

logger = logging.getLogger("lia.cmd_history")

MAX_SIZE = 50


class CommandHistory:
    def __init__(self, bus, maxlen: int = MAX_SIZE) -> None:
        self._history: deque[dict] = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        bus.subscribe(Event.COMMAND_EXECUTED, self._on_executed)

    def _on_executed(self, payload: dict) -> None:
        if not payload:
            return
        name = payload.get("name", "")
        # No registrar comandos del propio historial
        if name.startswith("history."):
            return
        entry = {
            "text": payload.get("text", ""),
            "name": name,
            "skill": payload.get("skill", ""),
            "category": payload.get("category", ""),
            "ts": datetime.datetime.now().isoformat(),
        }
        with self._lock:
            self._history.append(entry)
        logger.debug("Historial: +[%s] '%s'", name, entry["text"])

    def last(self) -> dict | None:
        """Devuelve el último comando ejecutado o None si el historial está vacío."""
        with self._lock:
            return dict(self._history[-1]) if self._history else None

    def today(self) -> list[dict]:
        """Comandos ejecutados hoy (por fecha ISO)."""
        hoy = datetime.date.today().isoformat()
        with self._lock:
            return [dict(e) for e in self._history if e["ts"].startswith(hoy)]

    def all(self) -> list[dict]:
        """Todos los comandos en el buffer (más reciente al final)."""
        with self._lock:
            return list(self._history)

    def clear(self) -> None:
        with self._lock:
            self._history.clear()
