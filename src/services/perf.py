#!/usr/bin/env python3
"""
perf.py — Auto-diagnóstico de rendimiento del PROPIO proceso de Lia.

Distinto de SystemTools.obtener_info_sistema(), que mide la máquina entera:
aquí medimos lo que Lia consume (RAM de su proceso, % CPU, hilos vivos,
tiempo encendida). Sirve para detectar fugas de memoria o hilos que se acumulan,
y para el comando de voz "rendimiento de Lia".

Además expone un cronómetro de latencia de ruteo (`time_routing`) que el
benchmark usa para medir cuánto tarda la capa de interpretación, sin micrófono.

Solo lectura: no modifica nada del runtime. Si psutil no está, degrada a los
datos que ofrece la librería estándar (hilos, uptime).
"""

from __future__ import annotations

import logging
import os
import threading
import time

logger = logging.getLogger("lia.perf")

try:
    import psutil
    _PROC = psutil.Process(os.getpid())
    _PSUTIL = True
except Exception:  # pragma: no cover
    _PROC = None
    _PSUTIL = False

_START_TS = time.monotonic()


def snapshot() -> dict:
    """Devuelve métricas instantáneas del proceso de Lia."""
    datos = {
        "uptime_s": round(time.monotonic() - _START_TS, 1),
        "threads": threading.active_count(),
        "ram_mb": None,
        "cpu_pct": None,
    }
    if _PSUTIL and _PROC is not None:
        try:
            datos["ram_mb"] = round(_PROC.memory_info().rss / (1024 * 1024), 1)
            # interval=None: % desde la última llamada; no bloquea.
            datos["cpu_pct"] = round(_PROC.cpu_percent(interval=None), 1)
        except Exception as ex:
            logger.debug("psutil falló en snapshot: %s", ex)
    return datos


def report_text() -> str:
    """Resumen legible/hablable del estado de recursos de Lia."""
    s = snapshot()
    partes = []
    if s["ram_mb"] is not None:
        partes.append(f"{s['ram_mb']:.0f} megas de RAM")
    if s["cpu_pct"] is not None:
        partes.append(f"{s['cpu_pct']:.0f} por ciento de CPU")
    partes.append(f"{s['threads']} hilos activos")
    mins = s["uptime_s"] / 60
    if mins >= 1:
        partes.append(f"llevo {mins:.0f} minutos encendida")
    return "Estoy usando " + ", ".join(partes) + "."


def time_routing(router, frases) -> dict:
    """
    Mide la latencia de la capa de interpretación (normalización + matching)
    sobre una lista de frases. No ejecuta handlers (solo router.match).
    Devuelve avg/p95/max en milisegundos.
    """
    from core.normalizer import normalize

    tiempos = []
    for frase in frases:
        t0 = time.perf_counter()
        cmd = normalize(frase, getattr(router.ctx, "config", None))
        router.match(cmd)
        tiempos.append((time.perf_counter() - t0) * 1000.0)
    if not tiempos:
        return {"n": 0, "avg_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    tiempos.sort()
    p95 = tiempos[min(len(tiempos) - 1, int(len(tiempos) * 0.95))]
    return {
        "n": len(tiempos),
        "avg_ms": round(sum(tiempos) / len(tiempos), 3),
        "p95_ms": round(p95, 3),
        "max_ms": round(tiempos[-1], 3),
    }
