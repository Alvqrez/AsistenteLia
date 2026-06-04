"""
services.ai — Abstracción de proveedores de IA (Fase 6).

La arquitectura queda LISTA para enchufar modelos (OpenAI, Claude, Gemini,
locales) detrás de una interfaz común, pero —por decisión de producto— hoy no
hay ningún proveedor real conectado: el proveedor por defecto es `NullProvider`.

Para activar IA en el futuro basta con:
    1. Implementar/usar un proveedor concreto en `providers.py`.
    2. Inyectarlo en el kernel y, opcionalmente, envolverlo en un IntentResolver
       para resolver intenciones por lenguaje natural (Fase 5 + 6).
Nada en las skills ni en el router necesita cambiar.
"""

from services.ai.base import AIProvider, ChatMessage, AIResponse
from services.ai.providers import NullProvider, get_provider

__all__ = ["AIProvider", "ChatMessage", "AIResponse", "NullProvider", "get_provider"]
