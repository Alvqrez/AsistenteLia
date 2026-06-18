#!/usr/bin/env python3
"""
macros.py — Secuencias de comandos guardadas y ejecutables por nombre.

Permite al usuario crear "macros": grupos de comandos que se ejecutan en
secuencia con una sola frase. Ejemplo:

  "Lia, crea macro modo trabajo"
  → Lia pregunta los comandos
  → usuario: "abre vs code; abre spotify; activa modo enfoque"
  → "Macro 'modo trabajo' creada con 3 comandos."

  "Lia, ejecuta macro modo trabajo"
  → ejecuta los 3 comandos en orden

Las macros se persisten en data/lia_macros.json.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sys
import tempfile

import re

from core.intent import IntentSpec
from core.matchers import contains_any, starts_with
from core.skill import Skill

logger = logging.getLogger("lia.skill.macros")

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT_DIR = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(_SRC_DIR)
_MACROS_FILE = os.path.join(_ROOT_DIR, "data", "lia_macros.json")

# Separadores que el usuario puede usar al dictar los comandos de la macro
_CMD_SEPS = ["; ", ";", " luego ", " después ", " y luego ", " y después "]

# ── Normalización de verbos en comandos individuales ─────────────────────────
# Mapea subjuntivo/infinitivo → imperativo para cada segmento de comando.
# El orden importa: formas más largas primero para no cortar "abrir" antes que "abre".
_VERB_MAP: dict[str, str] = {
    "abre ": "abre ",     "abrir ": "abre ",    "abra ": "abre ",
    "cierra ": "cierra ", "cerrar ": "cierra ",  "cierre ": "cierra ",
    "pausa ": "pausa ",   "pausar ": "pausa ",   "pause ": "pausa ",
    "activa ": "activa ", "activar ": "activa ", "active ": "activa ",
    "sube ": "sube ",     "subir ": "sube ",     "suba ": "sube ",
    "baja ": "baja ",     "bajar ": "baja ",     "baje ": "baja ",
    "busca ": "busca ",   "buscar ": "busca ",   "busque ": "busca ",
    "pon ": "pon ",       "poner ": "pon ",      "ponga ": "pon ",
    "reproduce ": "reproduce ", "reproducir ": "reproduce ",
    "lanza ": "lanza ",   "lanzar ": "lanza ",
    "inicia ": "inicia ", "iniciar ": "inicia ",
}


def _normalizar_verbo(texto: str) -> tuple[str, str | None]:
    """
    Devuelve (texto_normalizado, verbo_imperativo|None).
    verbo_imperativo se usa para herencia cuando el siguiente segmento no tiene verbo.
    """
    for forma, imperativo in _VERB_MAP.items():
        if texto.startswith(forma):
            return (imperativo + texto[len(forma):], imperativo)
    return (texto, None)


def _parse_inline_commands(texto: str) -> list[str]:
    """
    Convierte una cadena como "abra Teams y chatgpt" en ["abre Teams", "abre chatgpt"].

    Pasos:
      1. Divide en segmentos por conjunciones/separadores.
      2. Normaliza el verbo de cada segmento (subjuntivo → imperativo).
      3. Si un segmento no tiene verbo propio, hereda el del anterior.
    """
    if not texto:
        return []

    # Dividir por separadores (de más específicos a menos)
    partes = re.split(r'\s*[;,]\s*|\s+y\s+luego\s+|\s+y\s+después\s+|\s+luego\s+|\s+después\s+|\s+y\s+', texto)
    partes = [p.strip() for p in partes if p.strip()]

    resultado: list[str] = []
    ultimo_verbo: str | None = None

    for parte in partes:
        normalizado, verbo = _normalizar_verbo(parte)
        if verbo is not None:
            ultimo_verbo = verbo
            resultado.append(normalizado)
        elif ultimo_verbo is not None:
            # Sin verbo propio: hereda el último (p.ej. "chatgpt" → "abre chatgpt")
            resultado.append(ultimo_verbo + parte)
        else:
            # Sin verbo y sin herencia: usar tal cual (p.ej. "modo enfoque")
            resultado.append(parte)

    return resultado


class MacroEngine:
    """Lee/escribe lia_macros.json con escritura atómica."""

    def load(self) -> dict:
        if not os.path.exists(_MACROS_FILE):
            return {}
        try:
            with open(_MACROS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as ex:
            logger.warning("No se pudo leer macros: %s", ex)
            return {}

    def save(self, data: dict) -> None:
        dir_ = os.path.dirname(_MACROS_FILE)
        os.makedirs(dir_, exist_ok=True)
        try:
            fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, _MACROS_FILE)
        except Exception as ex:
            logger.error("No se pudo guardar macros: %s", ex)

    def add(self, nombre: str, comandos: list[str]) -> None:
        data = self.load()
        data[nombre] = {
            "comandos": comandos,
            "creado": datetime.date.today().isoformat(),
        }
        self.save(data)

    def delete(self, nombre: str) -> bool:
        data = self.load()
        if nombre not in data:
            return False
        del data[nombre]
        self.save(data)
        return True

    def get(self, nombre: str) -> list[str] | None:
        data = self.load()
        entry = data.get(nombre)
        return entry["comandos"] if entry else None

    def all_names(self) -> list[str]:
        return list(self.load().keys())


def _split_commands(texto: str) -> list[str]:
    """Divide el texto de comandos por cualquiera de los separadores conocidos."""
    import re
    # Normalizar separadores: reemplazarlos todos por "|SEP|" y luego split
    resultado = texto
    for sep in _CMD_SEPS:
        resultado = resultado.replace(sep, "|||")
    partes = [p.strip() for p in resultado.split("|||") if p.strip()]
    return partes


# ── Handlers ──────────────────────────────────────────────────────────────────

def _crear(ctx, m):
    nombre = m.slots.get("resto", "").strip()
    if not nombre:
        def _on_nombre(n):
            _crear_con_nombre(ctx, n.strip().lower())
        ctx.ask("¿Cómo se llamará la macro?", _on_nombre)
        return

    # Soporte para "crea macro [nombre] que [comandos]"
    if " que " in nombre:
        partes = nombre.split(" que ", 1)
        nombre_real = partes[0].strip().lower()
        comandos = _parse_inline_commands(partes[1].strip())
        if nombre_real and comandos:
            engine: MacroEngine = ctx.service("macro_engine")
            engine.add(nombre_real, comandos)
            ctx.say(
                f"Macro '{nombre_real}' creada con {len(comandos)} "
                f"comando{'s' if len(comandos) != 1 else ''}: {'; '.join(comandos)}."
            )
            ctx.registrar_actividad(f"Macro creada: {nombre_real} ({len(comandos)} pasos)")
            return

    _crear_con_nombre(ctx, nombre.lower())


def _crear_inline(ctx, m):
    """
    Creación inline: "crea una macro que abra Teams y chatgpt"
    Extrae los comandos del slot, normaliza verbos/herencia, luego pide el nombre.
    """
    commands_text = m.slots.get("resto", "").strip()
    comandos = _parse_inline_commands(commands_text)
    if not comandos:
        ctx.say("No entendí los comandos. Prueba: 'crea macro' y te voy preguntando.")
        return

    engine: MacroEngine = ctx.service("macro_engine")
    preview = "; ".join(comandos)
    # Nombre sugerido: extraído del primer comando (el app/acción principal)
    sugerido = comandos[0].split()[-1] if comandos else "nueva"

    def _on_nombre(nombre: str) -> None:
        nombre = nombre.strip().lower() or sugerido
        engine.add(nombre, comandos)
        ctx.say(
            f"Macro '{nombre}' creada con {len(comandos)} "
            f"comando{'s' if len(comandos) != 1 else ''}: {preview}."
        )
        ctx.registrar_actividad(f"Macro creada inline: {nombre} ({len(comandos)} pasos)")

    ctx.ask(
        f"Los comandos serían: {preview}. ¿Cómo quieres llamar esta macro?",
        _on_nombre,
    )


def _crear_con_nombre(ctx, nombre: str) -> None:
    engine: MacroEngine = ctx.service("macro_engine")

    def _on_comandos(texto: str) -> None:
        comandos = _split_commands(texto)
        if not comandos:
            ctx.say("No recibí ningún comando. Macro no creada.")
            return
        engine.add(nombre, comandos)
        ctx.say(
            f"Macro '{nombre}' creada con {len(comandos)} "
            f"comando{'s' if len(comandos) != 1 else ''}."
        )
        ctx.registrar_actividad(f"Macro creada: {nombre} ({len(comandos)} pasos)")

    ctx.ask(
        f"¿Qué comandos ejecuta la macro '{nombre}'? "
        "Dílos separados por punto y coma o por 'luego'.",
        _on_comandos,
    )


def _ejecutar(ctx, m):
    nombre = m.slots.get("resto", "").strip().lower()
    if not nombre:
        ctx.say("¿Cuál macro quieres ejecutar?")
        return
    engine: MacroEngine = ctx.service("macro_engine")
    comandos = engine.get(nombre)
    if comandos is None:
        macros = engine.all_names()
        if macros:
            ctx.say(f"No encontré la macro '{nombre}'. Tienes: {', '.join(macros)}.")
        else:
            ctx.say("No tienes macros guardadas. Crea una con 'crea macro'.")
        return
    ctx.say(f"Ejecutando macro '{nombre}'.")
    kernel = ctx.kernel
    for cmd in comandos:
        try:
            kernel.handle_text(cmd)
        except Exception as ex:
            logger.error("Error en paso de macro '%s' → '%s': %s", nombre, cmd, ex)
    ctx.registrar_actividad(f"Ejecutó macro: {nombre}")


def _listar(ctx, m):
    engine: MacroEngine = ctx.service("macro_engine")
    nombres = engine.all_names()
    if not nombres:
        ctx.say("No tienes macros guardadas. Crea una con 'crea macro'.")
        return
    data = engine.load()
    partes = []
    for n in nombres:
        n_cmds = len(data[n].get("comandos", []))
        partes.append(f"'{n}' ({n_cmds} pasos)")
    ctx.say(f"Tienes {len(nombres)} macro{'s' if len(nombres) != 1 else ''}: {', '.join(partes)}.")


def _borrar(ctx, m):
    nombre = m.slots.get("resto", "").strip().lower()
    if not nombre:
        def _on_nombre(n):
            _borrar_con_nombre(ctx, n.strip().lower())
        ctx.ask("¿Qué macro quieres borrar?", _on_nombre)
        return
    _borrar_con_nombre(ctx, nombre)


def _borrar_con_nombre(ctx, nombre: str) -> None:
    engine: MacroEngine = ctx.service("macro_engine")
    if engine.delete(nombre):
        ctx.say(f"Macro '{nombre}' eliminada.")
        ctx.registrar_actividad(f"Macro eliminada: {nombre}")
    else:
        ctx.say(f"No encontré una macro llamada '{nombre}'.")


# ── Skill ─────────────────────────────────────────────────────────────────────

class MacrosSkill(Skill):
    name = "macros"
    category = "automatización"

    def on_load(self, ctx) -> None:
        ctx.attach_service("macro_engine", MacroEngine())

    def intents(self, ctx):
        return [
            IntentSpec(
                name="macros.crear_inline",
                priority=375,
                matcher=starts_with((
                    "crea una macro que ", "crea una macros que ",
                    "crear una macro que ", "haz una macro que ",
                    "hacer una macro que ", "nueva macro que ",
                    "crea una macro con ", "crea una macros con ",
                )),
                handler=_crear_inline,
                description="Crea una macro directamente con los comandos en la frase",
                aliases=("crea una macro que abra spotify y discord",),
                examples=(
                    "crea una macro que abra teams y chatgpt",
                    "haz una macro que abra vs code y spotify",
                ),
            ),
            IntentSpec(
                name="macros.crear",
                priority=380,
                matcher=starts_with((
                    "crea macro ", "nueva macro ", "crea una macro ",
                    "crear macro ", "agregar macro ",
                    "crea macros ", "crea una macros ",
                    "crear una macro ", "crear una macros ",
                    "quiero una macro ", "quiero crear una macro ",
                    "graba macro ", "graba una macro ",
                )),
                handler=_crear,
                description="Crea una macro: secuencia de comandos ejecutable por nombre",
                aliases=("crea macro modo trabajo",),
                examples=("crea macro inicio del día",
                          "crea macro modo trabajo que abra vs code y spotify"),
            ),
            IntentSpec(
                name="macros.ejecutar",
                priority=390,
                matcher=starts_with(("ejecuta macro ", "activa macro ", "corre macro ",
                                     "ejecutar macro ", "macro ")),
                handler=_ejecutar,
                description="Ejecuta una macro guardada por su nombre",
                aliases=("ejecuta macro modo trabajo",),
                examples=("ejecuta macro inicio del día",),
            ),
            IntentSpec(
                name="macros.listar",
                priority=700,
                matcher=contains_any(("lista macros", "mis macros", "ver macros",
                                      "qué macros", "que macros", "mostrar macros")),
                handler=_listar,
                description="Lista todas las macros guardadas",
                aliases=("mis macros",),
                examples=("lista mis macros",),
            ),
            IntentSpec(
                name="macros.borrar",
                priority=400,
                matcher=starts_with(("borra macro ", "elimina macro ", "eliminar macro ",
                                     "borrar macro ", "quita macro ")),
                handler=_borrar,
                description="Borra una macro guardada",
                aliases=("borra macro modo trabajo",),
                examples=("borra macro inicio del día",),
            ),
        ]
