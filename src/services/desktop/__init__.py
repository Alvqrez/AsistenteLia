"""
services.desktop — Andamiaje de control del escritorio (Fase 8).

Prepara la arquitectura para control de ventanas, multimedia y monitores
(foco de ventana, minimizar/maximizar, play/pausa/siguiente, mover entre
monitores). La interfaz vive en `base.DesktopService`; la implementación real
(pygetwindow, pycaw, teclas multimedia, screeninfo) se añade luego sin afectar
a quien la consume. El control de Spotify multimedia puede apoyarse aquí o en
la API de Spotify.
"""

from services.desktop.base import DesktopService, NullDesktopService

__all__ = ["DesktopService", "NullDesktopService"]
