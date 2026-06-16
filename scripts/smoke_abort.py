#!/usr/bin/env python3
"""
smoke_abort.py — Verifica el kill switch global "aborta" (Fase 14):

  1. Bypassa una acción pendiente (no la trata como respuesta).
  2. Cancela un pomodoro en curso sin disparar el aviso "no hay pomodoro".
  3. Desactiva el modo enfoque si está activo.
  4. El fuzzy match de nombres de apps (typos/STT) resuelve a la app correcta.
  5. El modo TTS mínimo acorta confirmaciones pero no errores/ambigüedad.

Sustituye micrófono/TTS/detector/sonidos por dobles, igual que smoke_kernel.py.

Uso:  python scripts/smoke_abort.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import core.kernel as K


class FakeVoz:
    def __init__(self, *a, **k):
        self.detenido = False

    def decir(self, t): pass
    def set_silencioso(self, b): pass
    def vaciar(self): pass

    def detener_inmediato(self):
        self.detenido = True


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

# 1) Bypass de pending: "aborta" no debe resolverse como respuesta a la pregunta.
respuesta_capturada = []
lia.ctx.ask("¿Cuál es el mensaje del commit?", respuesta_capturada.append)
lia.handle_text("aborta")
check(not lia.ctx.has_pending(), "aborta limpia la acción pendiente")
check(respuesta_capturada == [], "aborta NO se cuela como respuesta de la pendiente")
check(lia.voz.detenido, "aborta detiene la voz (detener_inmediato)")

# 2) Pomodoro: cancela si está corriendo, sin tocar nada si no lo está.
lia.memoria.iniciar_pomodoro(minutos=1)
check(lia.memoria.pomodoro_en_curso(), "pomodoro arrancó para la prueba")
lia.voz.detenido = False
lia.handle_text("aborta")
# cancelar_pomodoro() señaliza un Event que el hilo del pomodoro chequea en su
# siguiente tick (hasta 1s); el efecto inmediato verificable es la señal, no
# que el hilo ya haya salido (misma latencia que el comando "cancela pomodoro").
check(lia.memoria._pomodoro_cancelado.is_set(), "aborta señaliza la cancelación del pomodoro")

# 3) Modo enfoque: se desactiva si estaba activo.
lia.focus.activar(minutos=1)
check(lia.focus.activo, "modo enfoque arrancó para la prueba")
lia.handle_text("aborta")
check(not lia.focus.activo, "aborta desactiva el modo enfoque")

# 4) Fuzzy match de apps (sin ejecutar nada, solo resolución de nombre).
check(lia.sistema._fuzzy_key("espotify", lia.sistema.APP_MAP.keys()) == "spotify",
      "fuzzy match resuelve 'espotify' -> 'spotify'")
check(lia.sistema._fuzzy_key("diskord", lia.sistema._CLOSE_MAP.keys()) == "discord",
      "fuzzy match resuelve 'diskord' -> 'discord'")
check(lia.sistema._fuzzy_key("xyzxyz", lia.sistema.APP_MAP.keys()) is None,
      "fuzzy match no inventa coincidencias para texto irrelevante")

# 5) TTS_MODE minimal: confirmaciones cortas, errores/ambigüedad intactos.
lia.persona.set_modo("minimal")
check(lia.persona.confirmacion() in ("Hecho.", "Listo.", "Ok."),
      "modo mínimo: confirmacion() es corta")
check(len(lia.persona.no_entendi()) > 15,
      "modo mínimo: no_entendi() sigue siendo una frase completa")
lia.persona.set_modo("normal")
check(lia.persona.confirmacion() not in ("Hecho.", "Listo.", "Ok."),
      "modo normal: confirmacion() vuelve a la personalidad completa")

print(f"\nFallos: {fallos}")
sys.exit(1 if fallos else 0)
