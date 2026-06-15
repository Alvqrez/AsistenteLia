"""
core — Núcleo de orquestación de Lia.

Contiene la infraestructura desacoplada que sustituye al antiguo god-object
`LiaAssistant` y a su parser `if/elif`:

    EventBus        — pub/sub thread-safe entre lógica y UI.
    IntentSpec      — declaración de una intención (matcher + handler + prioridad).
    IntentRouter    — enruta texto reconocido a la skill correcta (sustituye el if/elif).
    CommandRegistry — catálogo consultable: help dinámico, búsqueda y validación.
    AssistantContext— fachada limpia que ven las skills (e interfaz legacy para mod_*).
    Skill / Registry— habilidades auto-registrables (resuelve OCP: agregar skill ≠ tocar el core).
    LiaKernel       — orquestador delgado que ensambla todo.
"""

from core.event_bus import EventBus, Event
from core.intent import IntentSpec, IntentMatch
from core.router import IntentRouter
from core.registry import CommandRegistry
from core.context import AssistantContext
from core.skill import Skill, SkillRegistry

__all__ = [
    "EventBus", "Event",
    "IntentSpec", "IntentMatch",
    "IntentRouter",
    "CommandRegistry",
    "AssistantContext",
    "Skill", "SkillRegistry",
]
