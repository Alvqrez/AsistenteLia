#!/usr/bin/env python3
"""
base.py — Contrato abstracto de proveedores de IA (Fase 6).

    AIProvider      — ABC: chat(), complete(), is_available().
    ChatMessage     — mensaje role/content para conversación.
    AIResponse      — respuesta normalizada (texto + metadatos).

Cualquier proveedor (OpenAIProvider, ClaudeProvider, GeminiProvider,
LocalProvider) implementa esta interfaz. El resto del sistema depende solo de
`AIProvider`, nunca de un SDK concreto → cambiar de proveedor es trivial.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    role: str          # "system" | "user" | "assistant"
    content: str


@dataclass
class AIResponse:
    text: str
    provider: str = ""
    model: str = ""
    raw: dict = field(default_factory=dict)


class AIProvider(ABC):
    """Interfaz común a todos los proveedores de IA."""

    name: str = "abstract"

    @abstractmethod
    def is_available(self) -> bool:
        """¿Está el proveedor configurado y listo (API key, modelo cargado, ...)?"""
        raise NotImplementedError

    @abstractmethod
    def chat(self, messages: list[ChatMessage], **kwargs) -> AIResponse:
        """Conversación multi-turno."""
        raise NotImplementedError

    def complete(self, prompt: str, system: str = "", **kwargs) -> AIResponse:
        """Atajo de turno único; por defecto se apoya en chat()."""
        msgs = []
        if system:
            msgs.append(ChatMessage("system", system))
        msgs.append(ChatMessage("user", prompt))
        return self.chat(msgs, **kwargs)
