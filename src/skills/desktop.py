#!/usr/bin/env python3
"""
desktop.py — Control de ventanas (minimizar/maximizar/enfocar/listar).

Delega en `ctx.desktop` (WindowsDesktopService o NullDesktopService según el
SO, inyectado por el kernel). El control de medios (play/pausa/volumen) ya
vive en `plugins/musica/spotify.py` — esta skill solo cubre ventanas, que
antes no tenían ninguna implementación real (services/desktop era un scaffold
sin uso).
"""

from __future__ import annotations

from core.intent import IntentSpec
from core.matchers import after_trigger, contains_any, without
from core.skill import Skill


def _minimizar(ctx, m):
    nombre = m.slot("resto", "").strip()
    if not nombre:
        ctx.say("¿Qué ventana quieres que minimice?")
        return
    if ctx.desktop.minimize_window(nombre):
        ctx.say(f"Minimicé {nombre}.")
    else:
        ctx.say(f"No encontré ninguna ventana de {nombre}.")


def _maximizar(ctx, m):
    nombre = m.slot("resto", "").strip()
    if not nombre:
        ctx.say("¿Qué ventana quieres que maximice?")
        return
    if ctx.desktop.maximize_window(nombre):
        ctx.say(f"Maximicé {nombre}.")
    else:
        ctx.say(f"No encontré ninguna ventana de {nombre}.")


def _enfocar(ctx, m):
    nombre = m.slot("resto", "").strip()
    if not nombre:
        ctx.say("¿A qué ventana quieres que cambie?")
        return
    if ctx.desktop.focus_window(nombre):
        ctx.say(f"Listo, {nombre} al frente.")
    else:
        ctx.say(f"No encontré ninguna ventana de {nombre}.")


def _listar(ctx, m):
    titulos = ctx.desktop.list_windows()
    if not titulos:
        ctx.say("No veo ventanas abiertas.")
        return
    if len(titulos) > 6:
        ctx.say(f"Tienes {len(titulos)} ventanas abiertas: " + ", ".join(titulos[:6]) + "...")
    else:
        ctx.say("Ventanas abiertas: " + ", ".join(titulos))


class DesktopSkill(Skill):
    name = "desktop"
    category = "sistema"

    def intents(self, ctx):
        return [
            IntentSpec(
                name="desktop.minimizar", priority=700,
                matcher=after_trigger(("minimiza ", "minimizar "), require_text=True),
                handler=_minimizar,
                description="Minimiza una ventana por nombre",
                aliases=("minimiza spotify",),
                examples=("minimiza spotify", "minimiza el bloc de notas"),
            ),
            IntentSpec(
                name="desktop.maximizar", priority=710,
                matcher=after_trigger(("maximiza ", "maximizar "), require_text=True),
                handler=_maximizar,
                description="Maximiza una ventana por nombre",
                # "vscode" no se usa de ejemplo: lo captura system.modo_codigo
                # (sinónimo de "modo código", prioridad más alta).
                aliases=("maximiza el bloc de notas",),
                examples=("maximiza el bloc de notas",),
            ),
            IntentSpec(
                # without(..., "rama"): "cambia a rama X" es de dev.cambiar_rama,
                # no de esta skill.
                name="desktop.enfocar", priority=720,
                matcher=without(
                    after_trigger(("cambia a ", "enfoca ", "trae al frente "),
                                  require_text=True),
                    ("rama",),
                ),
                handler=_enfocar,
                description="Trae una ventana al frente por nombre",
                # "vscode" no se usa de ejemplo: lo captura system.modo_codigo.
                aliases=("cambia a chrome", "enfoca spotify"),
                examples=("cambia a chrome", "enfoca spotify", "trae al frente el bloc de notas"),
            ),
            IntentSpec(
                name="desktop.listar", priority=730,
                # Nota: NO usar "qué tengo abierto" — ws.que_hago (prioridad 140)
                # ya captura esa frase con otro significado (contexto de trabajo).
                matcher=contains_any(("qué ventanas tengo abiertas", "que ventanas tengo abiertas",
                                      "lista ventanas", "lista las ventanas")),
                handler=_listar,
                description="Lista las ventanas abiertas",
                aliases=("lista ventanas",),
                examples=("lista ventanas", "qué ventanas tengo abiertas"),
            ),
        ]
