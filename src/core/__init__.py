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

# UTF-8 en consola, garantizado para CUALQUIER entry point (main, smoke tests,
# webhook, exe empaquetado). Muchos módulos imprimen emojis/acentos/flechas; en
# una consola cp1252 (Windows) eso lanzaba UnicodeEncodeError y abortaba el
# arranque. Antes esto solo se hacía en main.py, así que cualquier camino que no
# pasara por main (p.ej. los smoke tests al instanciar el kernel) era frágil.
# Como todo entry point importa algo de `core`, este es el lugar central y DRY.
import sys as _sys

for _stream in (_sys.stdout, _sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass  # stdout puede ser None en modo windowed/frozen: se ignora seguro.

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
