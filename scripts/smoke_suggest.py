#!/usr/bin/env python3
"""
smoke_suggest.py — Verifica el sugeridor de comandos offline (CommandSuggester).

Comprueba que:
  • frases NO reconocidas pero cercanas a un comando real proponen ese comando;
  • basura sin parecido NO produce sugerencia (evita ruido / falsos positivos).

No toca micrófono/audio/red: el sugeridor es texto puro.

Uso:  python scripts/smoke_suggest.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from core.context import AssistantContext
from core.event_bus import EventBus
from core.registry import CommandRegistry
from core.router import IntentRouter
from core.skill import SkillRegistry
from core.suggester import CommandSuggester
from core.normalizer import normalize

ctx = AssistantContext(EventBus(), config=None, persona=None, memory=None)
router = IntentRouter(ctx)
_registry = SkillRegistry()
_registry.register_all(router, ctx, package_name="skills")
_registry.register_all(router, ctx, package_name="plugins")

commands = CommandRegistry(router)
suggester = CommandSuggester(commands)

# (texto_del_usuario, nombre_intencion_esperado)
# Casos donde el ROUTER falla (near-miss) pero el sugeridor debería rescatar.
CASOS_OK = [
    ("abreme spotify", "apps.abrir"),    # "abreme" no contiene el trigger "abre "
    ("ke hora es", "prod.hora"),         # transcripción coloquial sin "hora"
    ("que ora es", "prod.hora"),         # "ora" en vez de "hora"
    ("klima", "internet.clima"),         # typo de "clima"
]

# Casos que NO deben sugerir nada (basura / sin parecido).
CASOS_NONE = [
    "asdf qwerty zxcv",
    "xkcd plugh frobnicate",
]

fallos = 0
print(f"Intenciones totales: {len(commands.specs)}")

for texto, esperado in CASOS_OK:
    # Sólo tiene sentido sugerir si el router NO lo resolvió ya.
    cmd = normalize(texto, None)
    if router.match(cmd) is not None:
        print(f"  [SKIP] '{texto}' ya lo resuelve el router (no necesita sugeridor)")
        continue
    s = suggester.suggest(cmd)
    if s is None:
        print(f"  [FALLO] '{texto}' -> sin sugerencia (esperaba {esperado})")
        fallos += 1
    elif s.spec.name != esperado:
        print(f"  [FALLO] '{texto}' -> {s.spec.name} ('{s.phrase}', {s.score:.2f}); esperaba {esperado}")
        fallos += 1
    else:
        print(f"  [OK ] '{texto}' -> {s.spec.name} ('{s.phrase}', {s.score:.2f})")

for texto in CASOS_NONE:
    s = suggester.suggest(normalize(texto, None))
    if s is not None:
        print(f"  [FALLO] '{texto}' -> sugirió {s.spec.name} ('{s.phrase}', {s.score:.2f}); esperaba None")
        fallos += 1
    else:
        print(f"  [OK ] '{texto}' -> sin sugerencia (correcto)")

print(f"\nFallos: {fallos}")
sys.exit(1 if fallos else 0)
