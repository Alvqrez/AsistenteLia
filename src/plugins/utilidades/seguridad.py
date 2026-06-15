#!/usr/bin/env python3
"""
seguridad.py — Utilidades: contraseñas seguras y apagar la pantalla.

La contraseña se genera con `secrets` (criptográficamente segura), se copia
al portapapeles y NO se dice en voz alta (cualquiera podría oírla).
"""

from __future__ import annotations

import ctypes
import logging
import re
import secrets
import string
import subprocess

from core.intent import IntentSpec
from core.matchers import contains_any
from core.skill import Skill

logger = logging.getLogger("lia.plugin.seguridad")

_ALFABETO = string.ascii_letters + string.digits + "!@#$%&*-_=+?"


def _generar_password(ctx, m):
    match = re.search(r"de\s+(\d{1,3})\s*caracteres", m.text)
    largo = max(8, min(128, int(match.group(1)))) if match else 16

    # Garantiza al menos una mayúscula, una minúscula, un dígito y un símbolo.
    while True:
        pwd = "".join(secrets.choice(_ALFABETO) for _ in range(largo))
        if (any(c.islower() for c in pwd) and any(c.isupper() for c in pwd)
                and any(c.isdigit() for c in pwd)
                and any(c in "!@#$%&*-_=+?" for c in pwd)):
            break

    try:
        subprocess.run("clip", input=pwd.encode("utf-8"), check=True, timeout=5)
        ctx.say(f"Generé una contraseña de {largo} caracteres y la copié al "
                "portapapeles. No la digo en voz alta por seguridad.")
    except Exception as ex:
        logger.warning("No se pudo copiar al portapapeles: %s", ex)
        ctx.say("Generé la contraseña pero no pude copiarla al portapapeles. "
                "Está en la consola.")
        print(f"[Lia] Contraseña generada: {pwd}")
    ctx.registrar_actividad(f"Generó contraseña de {largo} caracteres")


def _apagar_pantalla(ctx, m):
    ctx.say("Apagando la pantalla.")
    HWND_BROADCAST = 0xFFFF
    WM_SYSCOMMAND = 0x0112
    SC_MONITORPOWER = 0xF170
    try:
        ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SYSCOMMAND,
                                          SC_MONITORPOWER, 2)  # 2 = apagar
        ctx.registrar_actividad("Apagó la pantalla")
    except Exception as ex:
        logger.error("No se pudo apagar la pantalla: %s", ex)
        ctx.say("No pude apagar la pantalla.")


class SeguridadSkill(Skill):
    name = "seguridad"
    category = "utilidades"

    def intents(self, ctx):
        return [
            IntentSpec(
                name="util.password", priority=440,
                matcher=contains_any(("genera contraseña", "genera una contraseña",
                                      "genera contrasena", "crea una contraseña",
                                      "crea contraseña", "contraseña segura",
                                      "contrasena segura", "genera password")),
                handler=_generar_password,
                description="Genera una contraseña segura y la copia al portapapeles",
                aliases=("genera contraseña segura", "genera contraseña de 20 caracteres"),
                examples=("genera contraseña segura",
                          "genera contraseña de 20 caracteres"),
            ),
            IntentSpec(
                # 515: antes de system.bloquear (520) por si la frase trae "bloquea".
                name="util.apagar_pantalla", priority=515,
                matcher=contains_any(("apaga pantalla", "apaga la pantalla",
                                      "apagar pantalla", "apagar la pantalla")),
                handler=_apagar_pantalla,
                description="Apaga el monitor (se enciende al mover el mouse)",
                aliases=("apaga pantalla", "apaga la pantalla"),
                examples=("apaga la pantalla",),
            ),
        ]
