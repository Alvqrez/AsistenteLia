#!/usr/bin/env python3
"""
smoke_kernel.py — Construye el LiaKernel COMPLETO con el audio simulado.

Valida lo que los otros tests no cubren: que `LiaKernel.__init__` ensambla sin
errores (servicios, activity logger, scheduler, detector, registro de skills,
GUI opcional) y que un comando recorre kernel→router→skill→servicio real.
También verifica que una acción destructiva (apagar) queda gateada por confirmación.

Sustituye micrófono/TTS/detector/sonidos por dobles para no tocar hardware.

Uso:  python scripts/smoke_kernel.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import core.kernel as K


class FakeVoz:
    def __init__(self, *a, **k): pass
    def decir(self, t): pass
    def set_silencioso(self, b): pass


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


# Parchear los puntos que tocan hardware/audio antes de construir el kernel.
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


lia = K.LiaKernel()                       # ← construcción completa
check(len(lia.router.specs) >= 80, f"skills registradas ({len(lia.router.specs)} intenciones)")
check(lia.scheduler.pendientes() is not None, "scheduler operativo")
check(lia.active(), "arranca activo")

dicho = []
lia.bus.subscribe("speak", dicho.append)

lia.handle_text("qué hora es")
check(any("hora" in t.lower() or "son las" in t.lower() for t in dicho),
      f"comando 'qué hora es' produce respuesta hablada -> {dicho[-1:]}")

# Acción destructiva: debe PEDIR confirmación, no apagar.
dicho.clear()
lia.handle_text("apaga la pc")
check(lia.ctx.has_pending(), "‘apaga la pc’ pide confirmación (no apaga)")
lia.handle_text("no")            # respuesta negativa
check(not lia.ctx.has_pending(), "respuesta negativa limpia la pendiente")

# Ciclo de vida.
lia.pause()
check(not lia.active(), "pause() desactiva")
was = lia.resume()
check(lia.active() and was, "resume() reactiva")

print(f"\nFallos: {fallos}")
sys.exit(1 if fallos else 0)
