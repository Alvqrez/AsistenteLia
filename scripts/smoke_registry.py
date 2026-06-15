#!/usr/bin/env python3
"""
smoke_registry.py — Verifica el CommandRegistry: carga de skills + plugins,
validación de conflictos (nombres/aliases), búsqueda y help dinámico.

Uso:  python scripts/smoke_registry.py
Sale con código 1 si hay advertencias de validación o fallos.
"""

import os
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from core.context import AssistantContext
from core.event_bus import EventBus
from core.registry import CommandRegistry
from core.router import IntentRouter
from core.skill import SkillRegistry
from skills import _help

ctx = AssistantContext(EventBus(), config=None, persona=None, memory=None)
router = IntentRouter(ctx)
skills = SkillRegistry()
skills.register_all(router, ctx, package_name="skills")
skills.register_all(router, ctx, package_name="plugins")
registry = CommandRegistry(router)

fallos = 0

# 1) Carga: debe haber un número razonable de comandos y categorías.
n = len(registry.specs)
cats = registry.categories()
print(f"[1] {n} comandos en {len(cats)} categorías: {', '.join(cats)}")
if n < 50:
    print(f"    FALLO: se esperaban >= 50 comandos, hay {n}")
    fallos += 1

# 2) Validación: cero advertencias (nombres únicos, aliases que rutean a su dueño).
warnings = registry.validate()
print(f"[2] Validación: {len(warnings)} advertencia(s)")
for w in warnings:
    print(f"    ⚠ {w}")
fallos += len(warnings)

# 3) Búsqueda: debe encontrar comandos por tema, sin acentos.
for consulta, esperado in [("pomodoro", "prod.pomodoro"),
                           ("git", "dev.git_status"),
                           ("musica", None),  # solo no debe explotar
                           ("clima", "internet.clima")]:
    res = [s.name for s in registry.search(consulta)]
    print(f"[3] search('{consulta}') -> {len(res)} resultado(s)")
    if esperado and esperado not in res:
        print(f"    FALLO: '{esperado}' no apareció en {res}")
        fallos += 1

# 4) find por nombre exacto.
if registry.find("apps.abrir") is None:
    print("[4] FALLO: find('apps.abrir') devolvió None")
    fallos += 1
else:
    print("[4] find('apps.abrir') OK")

# 5) Help dinámico: el menú se genera desde el registry e incluye categorías
#    y comandos reales (cero hardcodeo).
menu = _help.build_menu(registry)
for fragmento in ("DESARROLLO", "INTERNET", "CONTROL", "git status", "pomodoro"):
    if fragmento not in menu:
        print(f"[5] FALLO: el menú generado no contiene '{fragmento}'")
        fallos += 1
print(f"[5] Menú dinámico generado: {len(menu.splitlines())} líneas")

# 6) Resumen hablado.
resumen = _help.resumen_hablado(registry)
print(f"[6] Resumen hablado: {resumen[:90]}...")
if "comandos" not in resumen:
    fallos += 1

print()
if fallos:
    print(f"RESULTADO: {fallos} fallo(s)/advertencia(s). ✗")
    sys.exit(1)
print("RESULTADO: CommandRegistry sano. ✓")
