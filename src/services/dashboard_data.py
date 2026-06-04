#!/usr/bin/env python3
"""
dashboard_data.py — Agregador de datos REALES para el dashboard (Fase 11).

Unifica en un solo lugar los datos que antes mostraba el popup tkinter
(`mod_dashboard.py`) y que la GUI React no tenía conectados (mostraba mocks):
sistema (CPU/RAM/disco), pendientes, recordatorios, actividad reciente, etc.

La GUI React lo consume vía `PythonBridge.getDashboardData()` y deja de usar
datos ficticios. Así existe UN solo dashboard (React) alimentado de verdad.
"""

from __future__ import annotations

import datetime
import logging
import os
import platform
import re

logger = logging.getLogger("lia.dashboard_data")

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_DEFAULT_NOTAS_DIR   = os.path.join(os.path.expanduser("~"), "Documents", "Notas")
_DEFAULT_PENDIENTES  = os.path.join(_DEFAULT_NOTAS_DIR, "Pendientes.md")
_MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
          "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _pendientes_path(kernel) -> str:
    try:
        cfg = getattr(kernel, "config", None)
        if cfg:
            p = cfg.get("pendientes_path")
            if p:
                return p
    except Exception:
        pass
    return _DEFAULT_PENDIENTES


def _leer_pendientes(limite: int = 12, kernel=None) -> list[str]:
    ruta = _pendientes_path(kernel)
    items: list[str] = []
    try:
        if not os.path.exists(ruta):
            return items
        with open(ruta, "r", encoding="utf-8-sig") as f:
            for linea in f:
                m = re.match(r"^-\s*\[\s*\]\s*(.*)", linea.strip().lstrip("﻿"))
                if m and m.group(1).strip():
                    items.append(m.group(1).strip())
                    if len(items) >= limite:
                        break
    except Exception as ex:
        logger.debug("No se pudieron leer pendientes: %s", ex)
    return items


def _sistema() -> dict:
    if not _PSUTIL:
        return {"cpu": 0, "ram": 0, "disk": 0}
    try:
        ruta = "C:\\" if platform.system() == "Windows" else "/"
        return {
            # interval=None: no bloquea; mide desde la llamada anterior.
            "cpu": round(psutil.cpu_percent(interval=None)),
            "ram": round(psutil.virtual_memory().percent),
            "disk": round(psutil.disk_usage(ruta).percent),
        }
    except Exception as ex:
        logger.debug("No se pudo leer sistema: %s", ex)
        return {"cpu": 0, "ram": 0, "disk": 0}


def _hora_de(iso: str) -> str:
    try:
        return datetime.datetime.fromisoformat(iso).strftime("%H:%M")
    except Exception:
        return ""


def build(kernel) -> dict:
    """Construye el snapshot que consume la GUI. `kernel` es el LiaKernel."""
    ahora = datetime.datetime.now()

    # Recordatorios (servicio ya persistente).
    rec_hoy, rec_prox = [], []
    rec = getattr(kernel, "recordatorios", None)
    if rec is not None:
        try:
            rec_hoy = rec.obtener_hoy()
            rec_prox = [r for r in rec.obtener_proximos(7)
                        if r.get("fecha") != ahora.date().isoformat()][:5]
        except Exception as ex:
            logger.debug("recordatorios: %s", ex)

    # Actividad reciente desde la memoria unificada.
    actividad = []
    mem = getattr(kernel, "memory", None)
    if mem is not None:
        try:
            for a in reversed(mem.actividades_recientes(8)):
                actividad.append({"t": _hora_de(a.get("timestamp", "")),
                                  "text": a.get("actividad", "")})
        except Exception as ex:
            logger.debug("actividad: %s", ex)

    estado = "activa"
    try:
        estado = "activa" if kernel.active() else "pausada"
    except Exception:
        pass

    return {
        "time": ahora.strftime("%H:%M"),
        "date": f"{ahora.day} {_MESES[ahora.month - 1]}, {ahora.year}",
        "system": _sistema(),
        "pendientes": _leer_pendientes(kernel=kernel),
        "pendientes_path": _pendientes_path(kernel),
        "recordatorios_hoy": rec_hoy,
        "recordatorios_proximos": rec_prox,
        "actividad": actividad,
        "estado": estado,
    }
