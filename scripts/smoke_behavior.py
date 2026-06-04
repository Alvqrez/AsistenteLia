#!/usr/bin/env python3
"""
smoke_behavior.py — Verifica comportamiento end-to-end sin audio:
  • Dispatch de un handler real (calculadora) capturando lo que Lia "dice".
  • Flujo de pregunta pendiente (ctx.ask + resolución por la siguiente frase).
  • Cancelación de pregunta pendiente.

Uso:  python scripts/smoke_behavior.py
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from core.context import AssistantContext
from core.event_bus import Event, EventBus
from core.router import IntentRouter
from core.skill import SkillRegistry
from mod_config import ConfigManager
from mod_personalidad import Persona
from mod_productividad import ProductividadTools
from services.memory_store import MemoryStore

tmp = tempfile.mkdtemp(prefix="lia_smoke_")
bus = EventBus()
dicho: list = []
bus.subscribe(Event.SPEAK, dicho.append)

ctx = AssistantContext(bus, ConfigManager(tmp), Persona("Test"), MemoryStore(os.path.join(tmp, "data")))
ctx.set_activity_logger(lambda a: None)  # no escribir historial en la prueba
ctx.attach_service("productividad", ProductividadTools(ctx))

router = IntentRouter(ctx)
SkillRegistry().register_all(router, ctx, package_name="skills")

fallos = 0


def check(cond, desc):
    global fallos
    if not cond:
        fallos += 1
        print(f"  [FAIL] {desc}")
    else:
        print(f"  [OK ] {desc}")


# 1) Handler real: calculadora
dicho.clear()
router.handle_text("calcula 2 mas 2")
check(any("4" in t for t in dicho), f"calculadora responde 4 (dijo: {dicho})")

# 2) Pregunta pendiente + resolución por closure
respuestas: list = []
ctx.ask("¿Pregunta?", lambda r: respuestas.append(r))
check(ctx.has_pending(), "ask() deja una acción pendiente")
router.handle_text("la respuesta")
check(respuestas == ["la respuesta"], "la siguiente frase resuelve la pendiente")
check(not ctx.has_pending(), "ya no hay pendiente tras resolver")

# 3) Cancelación de pendiente
dicho.clear()
ctx.ask("¿Otra?", lambda r: respuestas.append("NO_DEBERIA"))
router.handle_text("cancela")
check(not ctx.has_pending(), "cancela limpia la pendiente")
check("NO_DEBERIA" not in respuestas, "cancela NO ejecuta el callback")
check(any("cancelad" in t.lower() for t in dicho), "cancela confirma verbalmente")

print(f"\nFallos: {fallos}")
sys.exit(1 if fallos else 0)
