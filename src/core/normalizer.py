#!/usr/bin/env python3
"""
normalizer.py — Pipeline de normalización de texto pre-router.

Transforma el texto de entrada ANTES de que el IntentRouter lo evalúe.
Dos etapas:
  1. Correcciones fonéticas para errores STT comunes en español/es-MX.
  2. Aliases personales del usuario (exactos, desde lia_config.json).

No toca matchers ni handlers: solo normaliza el texto de entrada.
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger("lia.normalizer")

# ── Reglas fonéticas ──────────────────────────────────────────────────────────
# (regex compilado, reemplazo). Orden importa: específicos/largos primero.
# Todos operan sobre texto ya en minúsculas.
_PHONETIC_RULES: list[tuple[re.Pattern, str]] = [
    # Spotify
    (re.compile(r"\bespotifai\b"),        "spotify"),
    (re.compile(r"\bspotifay\b"),         "spotify"),
    (re.compile(r"\bspotifai\b"),         "spotify"),
    (re.compile(r"\bspotifi\b"),          "spotify"),
    # VS Code (visual primero para no cortar "visual studio")
    (re.compile(r"\bvisual\s+co\b"),      "vs code"),
    (re.compile(r"\bvs\s+co\b"),          "vs code"),
    (re.compile(r"\bviscode\b"),          "vs code"),
    # YouTube
    (re.compile(r"\byou\s+tube\b"),       "youtube"),
    (re.compile(r"\byutub\b"),            "youtube"),
    (re.compile(r"\byutu\b"),             "youtube"),
    # WhatsApp (incluye variante mexicana "guasap")
    (re.compile(r"\bwats\s+app\b"),       "whatsapp"),
    (re.compile(r"\bwatsap\b"),           "whatsapp"),
    (re.compile(r"\bguasapp\b"),          "whatsapp"),
    (re.compile(r"\bguasap\b"),           "whatsapp"),
    # Microsoft Edge (variantes STT en español)
    (re.compile(r"\bedch\b"),             "edge"),
    (re.compile(r"\bedye\b"),             "edge"),
    (re.compile(r"\bedyé\b"),             "edge"),
    (re.compile(r"\bedyj\b"),             "edge"),
    # Microsoft Teams
    (re.compile(r"\btims\b"),             "teams"),
    (re.compile(r"\btim\b"),              "teams"),
    # ChatGPT
    (re.compile(r"\bchat\s+gpt\b"),       "chatgpt"),
    (re.compile(r"\bchatget\b"),          "chatgpt"),
    (re.compile(r"\bchat\s+get\b"),       "chatgpt"),
    # GitHub
    (re.compile(r"\bgit\s+hub\b"),        "github"),
    (re.compile(r"\bgitjub\b"),           "github"),
    # Flutter
    (re.compile(r"\bflu\s+ter\b"),        "flutter"),
    (re.compile(r"\bfluter\b"),           "flutter"),
    # Discord
    (re.compile(r"\bdiscort\b"),          "discord"),
    # Chrome
    (re.compile(r"\bcromo\b"),            "chrome"),
    # Notion
    (re.compile(r"\bnoshon\b"),           "notion"),
    # Claude
    (re.compile(r"\bclaut\b"),            "claude"),
    (re.compile(r"\bclod\b"),             "claude"),
    # PowerShell
    (re.compile(r"\bpower\s+shell\b"),    "powershell"),
    # Android Studio
    (re.compile(r"\bandroid\s+estudio\b"), "android studio"),
    # Git (sin hub — al final para no interferir con github)
    (re.compile(r"\bgiht\b"),             "git"),
    (re.compile(r"\bguit\b"),             "git"),
]

# ── Prefijos de cortesía ──────────────────────────────────────────────────────
# Se eliminan del inicio del texto. El orden importa: los más largos primero.
_POLITENESS_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^me\s+podr[ií]as\s+"),  ""),
    (re.compile(r"^me\s+puedes\s+"),       ""),
    (re.compile(r"^podr[ií]as\s+"),        ""),
    (re.compile(r"^puedes\s+"),            ""),
    (re.compile(r"^por\s+favor\s+"),       ""),
]

# ── Normalización de verbo inicial ────────────────────────────────────────────
# Mapea subjuntivo e infinitivo al imperativo cuando aparecen al INICIO del texto.
# Solo formas que NO son ya triggers (para no crear trabajo redundante).
_VERB_START_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^abra\s+"),        "abre "),
    (re.compile(r"^cierre\s+"),      "cierra "),
    (re.compile(r"^pause\s+"),       "pausa "),
    (re.compile(r"^active\s+"),      "activa "),
    (re.compile(r"^suba\s+"),        "sube "),
    (re.compile(r"^baje\s+"),        "baja "),
    (re.compile(r"^busque\s+"),      "busca "),
    (re.compile(r"^abrir\s+"),       "abre "),
    (re.compile(r"^cerrar\s+"),      "cierra "),
    (re.compile(r"^pausar\s+"),      "pausa "),
    (re.compile(r"^activar\s+"),     "activa "),
    (re.compile(r"^buscar\s+"),      "busca "),
    (re.compile(r"^lanzar\s+"),      "lanza "),
    (re.compile(r"^iniciar\s+"),     "inicia "),
]


def _apply_phonetic(text: str) -> str:
    for pattern, replacement in _PHONETIC_RULES:
        new_text = pattern.sub(replacement, text)
        if new_text != text:
            logger.debug("STT fix: '%s' → '%s'", text, new_text)
            text = new_text
    return text


def _apply_politeness(text: str) -> str:
    for pattern, replacement in _POLITENESS_RULES:
        new_text = pattern.sub(replacement, text)
        if new_text != text:
            logger.debug("Cortesía eliminada: '%s' → '%s'", text, new_text)
            return new_text.strip()
    return text


def _apply_verb_start(text: str) -> str:
    for pattern, replacement in _VERB_START_RULES:
        new_text = pattern.sub(replacement, text)
        if new_text != text:
            logger.debug("Verbo normalizado: '%s' → '%s'", text, new_text)
            return new_text
    return text


def _apply_user_aliases(text: str, config) -> str:
    """
    Sustituye un alias personal si el texto completo coincide exactamente
    con alguna clave en config["aliases_usuario"].
    """
    aliases: dict = config.get("aliases_usuario", {}) or {}
    if not aliases:
        return text
    canonical = text.strip()
    if canonical in aliases:
        expanded = aliases[canonical]
        logger.debug("Alias usuario: '%s' → '%s'", canonical, expanded)
        return expanded
    return text


def normalize(raw: str, config=None) -> str:
    """
    Normaliza texto antes del ruteo:
      1. Minúsculas + strip.
      2. Aliases personales del usuario (primero: tienen prioridad sobre fonética).
      3. Correcciones fonéticas STT.

    Los aliases van antes de la fonética para que el usuario pueda registrar
    sus propias abreviaciones sin que el corrector las transforme primero.
    Ejemplo: alias 'fluter' no se toca antes de buscarlo en el diccionario,
    aunque exista una regla fonética que lo convertiría en 'flutter'.
    """
    if not raw:
        return raw
    text = raw.lower().strip()
    if config is not None:
        text = _apply_user_aliases(text, config)
    text = _apply_phonetic(text)
    text = _apply_politeness(text)
    text = _apply_verb_start(text)
    return text
