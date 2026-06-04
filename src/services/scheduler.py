#!/usr/bin/env python3
"""
scheduler.py — Temporizadores persistentes.

Arregla un bug real del diseño anterior: `mod_memoria.recordar_en()` y los
pomodoros vivían únicamente en hilos en memoria. Si Lia se reiniciaba antes de
que dispararan, se perdían silenciosamente.

`PersistentScheduler` guarda cada temporizador en `lia_scheduler.json` y, al
arrancar, re-arma los pendientes (disparando de inmediato los ya vencidos). Un
único hilo monitor revisa la cola periódicamente.

No reemplaza a `mod_recordatorios` (que ya persiste recordatorios por fecha);
cubre los temporizadores cortos por minutos que antes eran efímeros.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import tempfile
import threading
import time
import uuid
from typing import Callable, Optional

logger = logging.getLogger("lia.scheduler")


class PersistentScheduler:
    def __init__(self, data_dir: str,
                 on_fire: Callable[[dict], None],
                 shutdown_flag: Optional[threading.Event] = None,
                 poll_seconds: int = 15) -> None:
        os.makedirs(data_dir, exist_ok=True)
        self._path = os.path.join(data_dir, "lia_scheduler.json")
        self._on_fire = on_fire
        self._shutdown = shutdown_flag or threading.Event()
        self._poll = poll_seconds
        self._lock = threading.Lock()
        self._timers: list[dict] = self._load()
        self._thread: Optional[threading.Thread] = None

    # ── Persistencia ──────────────────────────────────────────────────────
    def _load(self) -> list:
        try:
            if os.path.exists(self._path):
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f).get("timers", [])
        except Exception as ex:
            logger.error("No se pudo cargar scheduler: %s", ex)
        return []

    def _save(self) -> None:
        dir_ = os.path.dirname(self._path) or "."
        try:
            fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"timers": self._timers}, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self._path)
        except Exception as ex:
            logger.error("No se pudo guardar scheduler: %s", ex)

    # ── API pública ───────────────────────────────────────────────────────
    def schedule_in(self, mensaje: str, minutos: float, kind: str = "recordatorio") -> str:
        fire_at = datetime.datetime.now() + datetime.timedelta(minutes=minutos)
        return self._schedule_at(mensaje, fire_at, kind)

    def schedule_at(self, mensaje: str, cuando: datetime.datetime, kind: str = "recordatorio") -> str:
        return self._schedule_at(mensaje, cuando, kind)

    def _schedule_at(self, mensaje: str, cuando: datetime.datetime, kind: str) -> str:
        tid = str(uuid.uuid4())[:8]
        with self._lock:
            self._timers.append({
                "id": tid,
                "mensaje": mensaje,
                "fire_at": cuando.isoformat(),
                "kind": kind,
                "fired": False,
            })
            self._save()
        return tid

    def cancel(self, tid: str) -> bool:
        with self._lock:
            antes = len(self._timers)
            self._timers = [t for t in self._timers if t["id"] != tid]
            if len(self._timers) != antes:
                self._save()
                return True
            return False

    def pendientes(self) -> list:
        with self._lock:
            return [t for t in self._timers if not t.get("fired")]

    # ── Monitor ───────────────────────────────────────────────────────────
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="LiaScheduler")
        self._thread.start()

    def _loop(self) -> None:
        # Pequeño respiro para que el resto del sistema termine de arrancar
        # antes de disparar recordatorios vencidos.
        if self._shutdown.wait(timeout=2):
            return
        while not self._shutdown.is_set():
            try:
                self._check()
            except Exception as ex:
                logger.error("Error en monitor del scheduler: %s", ex)
            if self._shutdown.wait(timeout=self._poll):
                break

    def _check(self) -> None:
        ahora = datetime.datetime.now()
        disparados = []
        with self._lock:
            for t in self._timers:
                if t.get("fired"):
                    continue
                try:
                    cuando = datetime.datetime.fromisoformat(t["fire_at"])
                except Exception:
                    t["fired"] = True
                    continue
                if cuando <= ahora:
                    t["fired"] = True
                    disparados.append(dict(t))
            if disparados:
                # Limpiar los ya disparados de la lista persistida.
                self._timers = [t for t in self._timers if not t.get("fired")]
                self._save()
        for t in disparados:
            try:
                self._on_fire(t)
            except Exception as ex:
                logger.error("Callback on_fire falló: %s", ex)
