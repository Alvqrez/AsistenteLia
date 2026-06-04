#!/usr/bin/env python3
"""
providers.py — Proveedores de IA concretos (Fase 6).

Hoy solo está operativo `NullProvider` (sin IA). Los proveedores reales quedan
como esqueletos documentados: implementarlos es enchufar su SDK dentro de
`chat()` y leer la API key desde la configuración/entorno. El resto de Lia no
cambia.

`get_provider(nombre, config)` es el punto único de selección de proveedor.
"""

from __future__ import annotations

import logging

from services.ai.base import AIProvider, AIResponse, ChatMessage

logger = logging.getLogger("lia.ai")


class NullProvider(AIProvider):
    """Proveedor por defecto: no hay IA conectada. Responde de forma honesta."""

    name = "null"

    def is_available(self) -> bool:
        return False

    def chat(self, messages: list[ChatMessage], **kwargs) -> AIResponse:
        return AIResponse(
            text="La integración con IA todavía no está activada.",
            provider=self.name,
        )


class OpenAIProvider(AIProvider):
    """Esqueleto para OpenAI/ChatGPT. Implementar con el SDK `openai`."""

    name = "openai"

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: list[ChatMessage], **kwargs) -> AIResponse:
        raise NotImplementedError("OpenAIProvider aún no implementado (Fase 6).")


class ClaudeProvider(AIProvider):
    """Esqueleto para Anthropic Claude. Implementar con el SDK `anthropic`."""

    name = "claude"

    def __init__(self, api_key: str = "", model: str = "claude-opus-4-8") -> None:
        self.api_key = api_key
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: list[ChatMessage], **kwargs) -> AIResponse:
        raise NotImplementedError("ClaudeProvider aún no implementado (Fase 6).")


class GeminiProvider(AIProvider):
    """Esqueleto para Google Gemini. Implementar con `google-generativeai`."""

    name = "gemini"

    def __init__(self, api_key: str = "", model: str = "gemini-1.5-flash") -> None:
        self.api_key = api_key
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: list[ChatMessage], **kwargs) -> AIResponse:
        raise NotImplementedError("GeminiProvider aún no implementado (Fase 6).")


class LocalProvider(AIProvider):
    """Esqueleto para modelos locales (Ollama, llama.cpp, etc.)."""

    name = "local"

    def __init__(self, endpoint: str = "http://localhost:11434", model: str = "llama3") -> None:
        self.endpoint = endpoint
        self.model = model

    def is_available(self) -> bool:
        return False  # se activará al implementar la llamada al endpoint local

    def chat(self, messages: list[ChatMessage], **kwargs) -> AIResponse:
        raise NotImplementedError("LocalProvider aún no implementado (Fase 6).")


_PROVIDERS = {
    "null": NullProvider,
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "local": LocalProvider,
}


def get_provider(nombre: str = "null", config=None) -> AIProvider:
    """
    Devuelve un proveedor por nombre. Hoy el default es 'null' (sin IA).
    Cuando se implemente un proveedor real, este es el único sitio donde se
    lee la API key desde `config` y se decide qué clase instanciar.
    """
    cls = _PROVIDERS.get((nombre or "null").lower(), NullProvider)
    try:
        if cls is NullProvider:
            return NullProvider()
        # Los proveedores reales leerán su clave desde config cuando se implementen.
        return cls()
    except Exception as ex:
        logger.warning("No se pudo crear el proveedor '%s' (%s). Usando NullProvider.", nombre, ex)
        return NullProvider()
