#!/usr/bin/env python3
"""
_help.py — Texto del menú de comandos y utilidades para abrirlo/cerrarlo.

Helper compartido por la skill de control de voz. Extraído del antiguo
LiaAssistant para que la generación del `lia_comandos.txt` no viva en el núcleo.
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

MENU_TEXTO = """\
+==============================================================+
|                   ASISTENTE LIA  v5.0.0                      |
+==============================================================+
|  APLAUSOS                                                     |
|    1 aplauso   ->  Modo Estudio  (ChatGPT + WhatsApp)        |
|    2 aplausos  ->  Modo Codigo   (VS Code + GitHub + Spotify)|
|    3 aplausos  ->  Modo Juego    (Discord + TimerResolution) |
|                                                               |
|  COMANDOS DE VOZ  (di "Lia, ...")                             |
|  -- Modos --------------------------------------------------- |
|    "a estudiar" / "modo estudio" / "voy a trabajar"          |
|    "a programar" / "modo código" / "quiero codear"           |
|    "a jugar" / "gaming" / "modo juego"                       |
|  -- Rutina -------------------------------------------------- |
|    "inicio" / "buenos días" / "empecemos"                    |
|  -- Voz y control ------------------------------------------ |
|    "silencio" / "cállate" / "mute" / "habla"                 |
|    "pausate" / "ya regresé" / "apagate" / "cancela"          |
|  -- Aplicaciones ------------------------------------------- |
|    "abre [app]" / "cierra todo"                              |
|  -- Archivos y carpetas ------------------------------------ |
|    "crea archivo python [nombre] en [carpeta]"               |
|    "crea carpeta [nombre] en [carpeta]"                      |
|    "abre carpeta [nombre]" / "busca [término] en [carpeta]"  |
|  -- Pendientes / Notas ------------------------------------- |
|    "pendientes" / "anota [tarea]" / "tarea X lista"          |
|    "nota [clave] [texto]" / "recuerda nota [clave]"          |
|  -- Dev ---------------------------------------------------- |
|    "crea proyecto React en [carpeta]"                        |
|    "git status / push / pull / log / commit [msg]"           |
|    "nueva rama [x]" / "cambia rama [x]" / "clona [url]"       |
|    "abre vscode en [carpeta]" / "docs python" / "mdn"        |
|  -- Productividad ------------------------------------------ |
|    "pomodoro [N]" / "recuerda [X] en [N] minutos"            |
|    "qué hora" / "qué fecha" / "calcula [op]"                 |
|    "convierte [N] [unidad] a [unidad]"                       |
|  -- Clima e internet --------------------------------------- |
|    "clima" / "busca [X]" / "youtube [X]" / "wikipedia [X]"   |
|    "maps [lugar]" / "mi ip" / "noticias" / "traduce [texto]" |
|  -- Sistema ------------------------------------------------ |
|    "sistema" / "disco" / "procesos pesados"                  |
|    "bloquea" / "apaga la pc" / "cancela apagado"             |
|  -- Modo Enfoque ------------------------------------------- |
|    "modo enfoque [N]" / "desbloquea sitios"                  |
|  -- Recordatorios ------------------------------------------ |
|    "recuerda [X] mañana / el 15 de julio"                    |
|    "mis recordatorios" / "recordatorio completado [X]"       |
|  -- Metas / Hábitos / Proyectos ----------------------------- |
|    "mis metas" / "agrega meta [texto]"                       |
|    "mis hábitos" / "hice el hábito X"                        |
|    "mis proyectos" / "resumen personal"                      |
|  -- Contexto de trabajo ------------------------------------- |
|    "abre el proyecto [nombre]" / "ejecuta"                    |
|    "qué estoy haciendo" / "abre/cierra lo último" / "abortar"|
|  -- Misc --------------------------------------------------- |
|    "dashboard" / "configuracion" / "resumen" / "comandos"    |
|    "gracias" / "recalibra"                                   |
+==============================================================+
"""


def generar_txt_comandos() -> None:
    """Escribe el menú a disco de forma atómica."""
    try:
        dir_ = os.path.dirname(COMANDOS_TXT_PATH) or "."
        fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(MENU_TEXTO)
        os.replace(tmp, COMANDOS_TXT_PATH)
    except Exception as ex:
        logger.warning("No se pudo crear lia_comandos.txt: %s", ex)


def abrir_txt_comandos() -> None:
    try:
        if not os.path.exists(COMANDOS_TXT_PATH):
            generar_txt_comandos()
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
