"""
services.vision — Andamiaje de visión computacional (Fase 9).

Prepara la arquitectura para OCR, capturas de pantalla y análisis visual
("¿qué error aparece?", "lee lo que tengo abierto"). La interfaz queda definida
en `base.VisionService`; la implementación real (pytesseract, mss, etc.) se
añade después sin tocar a quien la consume.
"""

from services.vision.base import VisionService, NullVisionService

__all__ = ["VisionService", "NullVisionService"]
