#!/usr/bin/env python3
"""
windows.py — Implementación real de DesktopService para Windows.

Mismo enfoque que `plugins/musica/spotify.py::_titulo_spotify` (EnumWindows +
GetWindowTextW vía ctypes, sin dependencias nuevas), generalizado a TODAS las
ventanas visibles con título, no solo a un proceso concreto.
"""

from __future__ import annotations

import ctypes
import logging

from services.desktop.base import DesktopService

logger = logging.getLogger("lia.desktop")

_SW_MINIMIZE = 6
_SW_MAXIMIZE = 3


def _enumerar_ventanas() -> list[tuple[int, str]]:
    """Devuelve [(hwnd, titulo)] de las ventanas visibles con título no vacío."""
    user32 = ctypes.windll.user32
    encontradas: list[tuple[int, str]] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _enum(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        largo = user32.GetWindowTextLengthW(hwnd)
        if largo > 0:
            buf = ctypes.create_unicode_buffer(largo + 1)
            user32.GetWindowTextW(hwnd, buf, largo + 1)
            if buf.value.strip():
                encontradas.append((hwnd, buf.value))
        return True

    user32.EnumWindows(_enum, 0)
    return encontradas


def _buscar(substring: str) -> tuple[int, str] | None:
    sub = substring.lower().strip()
    if not sub:
        return None
    for hwnd, titulo in _enumerar_ventanas():
        if sub in titulo.lower():
            return hwnd, titulo
    return None


class WindowsDesktopService(DesktopService):
    name = "windows-desktop"

    def is_available(self) -> bool:
        return True

    def list_windows(self) -> list[str]:
        return [titulo for _, titulo in _enumerar_ventanas()]

    def focus_window(self, title_substring: str) -> bool:
        encontrada = _buscar(title_substring)
        if not encontrada:
            return False
        hwnd, _ = encontrada
        try:
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            return True
        except Exception as ex:
            logger.warning("No se pudo enfocar la ventana: %s", ex)
            return False

    def minimize_window(self, title_substring: str) -> bool:
        return self._show(title_substring, _SW_MINIMIZE)

    def maximize_window(self, title_substring: str) -> bool:
        return self._show(title_substring, _SW_MAXIMIZE)

    def _show(self, title_substring: str, sw_flag: int) -> bool:
        encontrada = _buscar(title_substring)
        if not encontrada:
            return False
        hwnd, _ = encontrada
        try:
            ctypes.windll.user32.ShowWindow(hwnd, sw_flag)
            return True
        except Exception as ex:
            logger.warning("No se pudo cambiar el estado de la ventana: %s", ex)
            return False
