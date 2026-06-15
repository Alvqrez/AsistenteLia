#!/usr/bin/env python3
"""
_help.py — Generación DINÁMICA del menú de comandos + utilidades para abrirlo.

El menú ya no es un texto hardcodeado: se construye desde el CommandRegistry,
agrupado por categoría, con los aliases y ejemplos que cada IntentSpec declaró.
Agregar un comando nuevo (skill o plugin) lo hace aparecer aquí solo.

Solo la sección de APLAUSOS es estática: describe hardware/kernel, no comandos.
"""

import logging
import os
import platform
import subprocess
import sys
import tempfile

logger = logging.getLogger("lia.help")

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT_DIR = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(_SRC_DIR)
_DATA_DIR = os.path.join(_ROOT_DIR, "data")
os.makedirs(_DATA_DIR, exist_ok=True)
COMANDOS_TXT_PATH = os.path.join(_DATA_DIR, "lia_comandos.txt")

_ANCHO = 64

_LINEAS_APLAUSOS = (
    "APLAUSOS",
    "  1 aplauso   ->  Modo Estudio",
    "  2 aplausos  ->  Modo Codigo",
    "  3 aplausos  ->  Modo Juego (o reactivar si esta en pausa)",
)


def _linea(texto: str = "") -> str:
    return f"|  {texto:<{_ANCHO - 4}}|"


def build_menu(registry) -> str:
    """Construye el menú completo desde el CommandRegistry (cero hardcodeo)."""
    grupos = registry.by_category()
    total = len(registry.specs)

    out = ["+" + "=" * (_ANCHO - 2) + "+"]
    titulo = f"ASISTENTE LIA  v5.1  —  {total} comandos"
    out.append(f"|{titulo:^{_ANCHO - 2}}|")
    out.append("+" + "=" * (_ANCHO - 2) + "+")
    out.extend(_linea(t) for t in _LINEAS_APLAUSOS)
    out.append(_linea())
    out.append(_linea('COMANDOS DE VOZ  (di "Lia, ...")'))

    for categoria, specs in grupos.items():
        out.append(_linea())
        out.append(_linea(f"-- {categoria.upper()} " + "-" * max(0, _ANCHO - 10 - len(categoria))))
        for s in specs:
            frase = s.aliases[0] if s.aliases else (s.examples[0] if s.examples else s.name)
            desc = s.description or s.name
            out.append(_linea(f'"{frase}"'))
            out.append(_linea(f"    {desc}"))
            extras = [a for a in s.aliases[1:3]]
            if extras:
                out.append(_linea("    tambien: " + " / ".join(f'"{a}"' for a in extras)))
    out.append("+" + "=" * (_ANCHO - 2) + "+")
    return "\n".join(out) + "\n"


def resumen_hablado(registry, max_categorias: int = 12) -> str:
    """Resumen corto para decirlo por voz: cuántos comandos y qué categorías."""
    grupos = registry.by_category()
    cats = ", ".join(list(grupos.keys())[:max_categorias])
    return (f"Tengo {len(registry.specs)} comandos en estas áreas: {cats}. "
            "Te dejo la lista completa en pantalla.")


def generar_txt_comandos(registry) -> None:
    """Escribe el menú generado a disco de forma atómica."""
    try:
        contenido = build_menu(registry)
        dir_ = os.path.dirname(COMANDOS_TXT_PATH) or "."
        fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(contenido)
        os.replace(tmp, COMANDOS_TXT_PATH)
    except Exception as ex:
        logger.warning("No se pudo crear lia_comandos.txt: %s", ex)


def abrir_txt_comandos(registry=None) -> None:
    try:
        if registry is not None:
            generar_txt_comandos(registry)  # siempre fresco
        if platform.system() == "Windows":
            subprocess.Popen(["notepad.exe", COMANDOS_TXT_PATH])
        else:
            subprocess.Popen(["xdg-open", COMANDOS_TXT_PATH])
    except Exception as ex:
        logger.warning("Error al abrir comandos: %s", ex)


def cerrar_txt_comandos() -> None:
    try:
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/f", "/im", "notepad.exe"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
