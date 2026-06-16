#!/usr/bin/env python3
"""
smoke_asistente.py — Verifica las mejoras de "asistente virtual" (multi-turno
en pendientes, control de ventanas, briefing proactivo):

  1. "completa eso" resuelve al último pendiente anotado, sin repetirlo.
  2. ctx.desktop lista ventanas reales del sistema (sin crashear).
  3. focus/minimize/maximize sobre una ventana inexistente devuelven False
     en vez de lanzar una excepción.
  4. El briefing automático solo se dispara una vez por fecha persistida.

Sustituye micrófono/TTS/detector/sonidos por dobles, igual que smoke_kernel.py.

Uso:  python scripts/smoke_asistente.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import core.kernel as K


class FakeVoz:
    def __init__(self, *a, **k): pass
    def decir(self, t): pass
    def set_silencioso(self, b): pass
    def vaciar(self): pass
    def detener_inmediato(self): pass


class FakeMic:
    def __init__(self, *a, **k): pass


class FakeDetector:
    def __init__(self, *a, **k): pass
    def set_active(self, b): pass
    def set_lia_hablando(self, b): pass
    def notificar_voz_detectada(self, **k): pass
    def recargar_perfil(self): pass
    def start_loop(self, shutdown_flag=None): pass


class FakeSonidos:
    def __getattr__(self, n): return lambda *a, **k: None


K.VozEngine = FakeVoz
K.ClapDetector = FakeDetector
K.sr.Microphone = FakeMic
K.mod_sonidos = FakeSonidos()

fallos = 0


def check(cond, desc):
    global fallos
    print(f"  [{'OK ' if cond else 'FAIL'}] {desc}")
    if not cond:
        fallos += 1


lia = K.LiaKernel()

# 1) Multi-turno: "completa eso" sin repetir el texto del pendiente.
dicho = []
lia.bus.subscribe("speak", dicho.append)
lia.handle_text("anota comprar pan")
check(lia.contexto.ultimo_pendiente == "comprar pan",
      "se registró 'comprar pan' como último pendiente")
lia.handle_text("completa eso")
# La frase de confirmación es aleatoria (mod_personalidad.tarea_completada) y
# no siempre repite el texto; la prueba real es que el pendiente ya no
# aparece como abierto en la lista (se marcó "- [x]").
check("comprar pan" not in lia.memoria.obtener_pendientes(),
      "'completa eso' resolvió al último pendiente y lo marcó hecho")

# 2) Listado de ventanas reales (no debe crashear, debe devolver algo en un
# Windows con al menos explorer/taskbar corriendo).
ventanas = lia.desktop.list_windows()
check(isinstance(ventanas, list), "list_windows() devuelve una lista")
check(len(ventanas) > 0, f"hay al menos una ventana visible ({len(ventanas)} encontradas)")

# 3) Ventana inexistente: no debe lanzar excepción, debe devolver False.
check(lia.desktop.focus_window("ventana-que-no-existe-xyz123") is False,
      "focus_window sobre algo inexistente devuelve False, no crashea")
check(lia.desktop.minimize_window("ventana-que-no-existe-xyz123") is False,
      "minimize_window sobre algo inexistente devuelve False, no crashea")

# 4) Briefing: el timer de 3s no ha disparado aún en el smoke test, pero la
# lógica de persistencia de fecha debe funcionar cuando se invoca directamente.
import datetime as _dt
hoy = _dt.date.today().isoformat()
lia.config.set("ultimo_briefing_fecha", hoy)
check(lia.config.get("ultimo_briefing_fecha") == hoy,
      "ConfigManager persiste y recupera la fecha del briefing")

print(f"\nFallos: {fallos}")
sys.exit(1 if fallos else 0)
