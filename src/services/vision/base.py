#!/usr/bin/env python3
"""
base.py — Contrato del servicio de visión (Fase 9).

    VisionService     — ABC: capture_screen(), ocr(), read_screen(), describe().
    NullVisionService — implementación inactiva por defecto (sin dependencias).

Implementación futura sugerida:
    • capture_screen → `mss` o `PIL.ImageGrab`
    • ocr            → `pytesseract`
    • describe       → un AIProvider con visión (Fase 6)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class VisionService(ABC):
    name: str = "abstract-vision"

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def capture_screen(self, region: Optional[tuple] = None) -> Optional[str]:
        """Captura la pantalla (o una región) y devuelve la ruta del archivo."""
        ...

    @abstractmethod
    def ocr(self, image_path: str) -> str:
        """Extrae texto de una imagen."""
        ...

    def read_screen(self, region: Optional[tuple] = None) -> str:
        """Atajo: captura + OCR. 'Lee lo que tengo abierto'."""
        path = self.capture_screen(region)
        return self.ocr(path) if path else ""


class NullVisionService(VisionService):
    """Servicio de visión inactivo (default). No requiere dependencias."""

    name = "null-vision"

    def is_available(self) -> bool:
        return False

    def capture_screen(self, region: Optional[tuple] = None) -> Optional[str]:
        return None

    def ocr(self, image_path: str) -> str:
        return ""
