#!/usr/bin/env python3
"""
build_exe.py — Genera Lia.exe con PyInstaller y lo registra en el
               Registro de Windows para que arranque con el sistema.

Uso:
    python scripts/build_exe.py          # construye el .exe
    python scripts/build_exe.py --no-startup   # construye sin registrar autoarranque
    python scripts/build_exe.py --remove-startup  # elimina el autoarranque

Requisitos:
    pip install pyinstaller
"""

import os
import sys
import subprocess
import winreg
import shutil
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────────────────────────────────
PROYECTO_ROOT = Path(__file__).resolve().parent.parent   # carpeta AsistenteLia/
SRC_DIR       = PROYECTO_ROOT / "src"
DIST_DIR      = PROYECTO_ROOT / "dist"
BUILD_DIR     = PROYECTO_ROOT / "build"
SPEC_DIR      = PROYECTO_ROOT

APP_NAME      = "Lia"
ENTRY_POINT   = SRC_DIR / "main.py"
ICON_PATH     = PROYECTO_ROOT / "assets" / "lia_icon.ico"   # opcional

# Clave del Registro donde Windows guarda los programas de autoarranque
STARTUP_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_REG_NAME = "LiaAsistente"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _pyinstaller_cmd() -> list:
    """Construye la lista de argumentos para PyInstaller."""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",                   # todo en un solo .exe
        "--windowed",                  # sin consola negra al arrancar
        "--name", APP_NAME,
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(SPEC_DIR),
        # Incluir archivos de datos necesarios en runtime
        "--add-data", f"{PROYECTO_ROOT / 'data'}{os.pathsep}data",
        # Módulos ocultos que PyInstaller puede no detectar automáticamente
        "--hidden-import", "pyttsx3.drivers",
        "--hidden-import", "pyttsx3.drivers.sapi5",
        "--hidden-import", "speech_recognition",
        "--hidden-import", "sounddevice",
        "--hidden-import", "pygame",
        "--hidden-import", "PySide6.QtCore",
        "--hidden-import", "PySide6.QtWidgets",
        "--hidden-import", "PySide6.QtGui",
        # Paths de búsqueda para que encuentre los módulos de src/
        "--paths", str(SRC_DIR),
        str(ENTRY_POINT),
    ]

    # Agregar ícono si existe
    if ICON_PATH.exists():
        cmd += ["--icon", str(ICON_PATH)]

    return cmd


def build():
    """Ejecuta PyInstaller y devuelve la ruta del .exe generado."""
    print(f"[LIA BUILD] Compilando {APP_NAME}.exe …")
    print(f"            Fuente : {ENTRY_POINT}")
    print(f"            Salida : {DIST_DIR}")

    result = subprocess.run(_pyinstaller_cmd(), cwd=str(PROYECTO_ROOT))
    if result.returncode != 0:
        print("\n[ERROR] PyInstaller terminó con errores.")
        sys.exit(result.returncode)

    exe_path = DIST_DIR / f"{APP_NAME}.exe"
    if not exe_path.exists():
        print(f"\n[ERROR] No se encontró el ejecutable esperado en:\n  {exe_path}")
        sys.exit(1)

    print(f"\n[OK] Ejecutable generado:\n  {exe_path}")
    return exe_path


def register_startup(exe_path: Path):
    """
    Registra Lia.exe en el Registro de Windows para que inicie con el equipo.
    El valor se escribe en HKCU (no requiere permisos de administrador).
    """
    exe_str = str(exe_path)
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_REG_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, STARTUP_REG_NAME, 0, winreg.REG_SZ, exe_str)
        winreg.CloseKey(key)
        print(f"[OK] Autoarranque registrado en el Registro de Windows.")
        print(f"     Clave : HKCU\\{STARTUP_REG_KEY}")
        print(f"     Valor : {STARTUP_REG_NAME} = {exe_str}")
    except OSError as ex:
        print(f"[ERROR] No se pudo escribir en el Registro: {ex}")


def remove_startup():
    """Elimina la entrada de autoarranque del Registro."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_REG_KEY,
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, STARTUP_REG_NAME)
        winreg.CloseKey(key)
        print(f"[OK] Autoarranque eliminado del Registro.")
    except FileNotFoundError:
        print("[INFO] No había entrada de autoarranque registrada.")
    except OSError as ex:
        print(f"[ERROR] No se pudo modificar el Registro: {ex}")


# ──────────────────────────────────────────────────────────────────────────────
# Entry-point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if sys.platform != "win32":
        print("[ERROR] Este script es solo para Windows.")
        sys.exit(1)

    if "--remove-startup" in sys.argv:
        remove_startup()
        sys.exit(0)

    exe = build()

    if "--no-startup" not in sys.argv:
        register_startup(exe)

    print("\n¡Listo! Lia arrancará automáticamente con Windows.")
