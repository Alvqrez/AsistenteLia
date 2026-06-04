#!/usr/bin/env python3
"""
base.py — Contrato del servicio de control de escritorio (Fase 8).

    DesktopService     — ABC: control de ventanas, multimedia y monitores.
    NullDesktopService — implementación inactiva por defecto.

Implementación futura sugerida:
    • ventanas  → `pygetwindow` / Win32 API
    • multimedia→ teclas virtuales VK_MEDIA_* / `pycaw`
    • monitores → `screeninfo`
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class DesktopService(ABC):
    name: str = "abstract-desktop"

    @abstractmethod
    def is_available(self) -> bool:
        ...

    # ── Ventanas ──────────────────────────────────────────────────────────
    @abstractmethod
    def list_windows(self) -> list[str]:
        ...

    @abstractmethod
    def focus_window(self, title_substring: str) -> bool:
        ...

    def minimize_window(self, title_substring: str) -> bool:
        return False

    def maximize_window(self, title_substring: str) -> bool:
        return False

    # ── Multimedia ────────────────────────────────────────────────────────
    def media_play_pause(self) -> bool:
        return False

    def media_next(self) -> bool:
        return False

    def media_previous(self) -> bool:
        return False

    def set_volume(self, percent: int) -> bool:
        return False

    # ── Monitores ─────────────────────────────────────────────────────────
    def list_monitors(self) -> list[dict]:
        return []


class NullDesktopService(DesktopService):
    """Control de escritorio inactivo (default). No requiere dependencias."""

    name = "null-desktop"

    def is_available(self) -> bool:
        return False

    def list_windows(self) -> list[str]:
        return []

    def focus_window(self, title_substring: str) -> bool:
        return False
