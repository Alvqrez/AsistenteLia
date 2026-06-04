#!/usr/bin/env python3
"""
lia_agregar_inicio.py — Agrega Lia al inicio automático de Windows.

Crea un launcher VBS en la carpeta Startup del usuario que arranca Lia
al encender la PC, sin mostrar ventana de consola.

Uso:
    python scripts/lia_agregar_inicio.py
    (o doble clic en lia_agregar_inicio.bat)
"""

import os
import sys

# ── Rutas ─────────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIA_ROOT    = os.path.dirname(_SCRIPT_DIR)
LIA_MAIN    = os.path.join(LIA_ROOT, "src", "main.py")

STARTUP_FOLDER = os.path.join(
    os.environ["APPDATA"],
    "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
)
VBS_PATH = os.path.join(STARTUP_FOLDER, "Lia.vbs")

# ── Encontrar pythonw.exe (Python sin ventana de consola) ─────────────────────
# pythonw.exe está junto a python.exe y suprime la consola negra al arrancar.
_python_exe  = sys.executable
_pythonw_exe = _python_exe.replace("python.exe", "pythonw.exe") \
                           .replace("python3.exe", "pythonw.exe")

if not os.path.exists(_pythonw_exe):
    # Si no existe pythonw, usar python normal (aparecerá consola brevemente)
    _pythonw_exe = _python_exe
    print("  [aviso] pythonw.exe no encontrado — se usará python.exe "
          "(aparecerá una consola breve al iniciar).")

PYTHON_EXE = _pythonw_exe


def crear_launcher():
    # Verificar que main.py existe
    if not os.path.exists(LIA_MAIN):
        print(f"ERROR: No se encontró {LIA_MAIN}")
        print("Asegúrate de ejecutar este script desde la carpeta del proyecto.")
        return False

    # El script VBS ejecuta pythonw main.py sin mostrar ninguna ventana.
    # windowStyle=0 → oculto.  bWaitOnReturn=False → no espera.
    # En VBS, "" dentro de una cadena = un " literal; por eso el comando
    # queda como: "pythonw.exe" "main.py"  (rutas con espacios correctamente comilladas).
    vbs_content = (
        "' Launcher silencioso de Lia\n"
        'Set oShell = CreateObject("WScript.Shell")\n'
        f'oShell.Run """{PYTHON_EXE}"" ""{LIA_MAIN}""", 0, False\n'
    )

    os.makedirs(STARTUP_FOLDER, exist_ok=True)
    with open(VBS_PATH, "w", encoding="utf-8") as f:
        f.write(vbs_content)

    print()
    print("=" * 60)
    print("  LIA AGREGADA AL INICIO DE WINDOWS")
    print("=" * 60)
    print(f"  Launcher : {VBS_PATH}")
    print(f"  Python   : {PYTHON_EXE}")
    print(f"  Main     : {LIA_MAIN}")
    print()
    print("  Lia se iniciará automáticamente la próxima vez")
    print("  que enciendas la PC.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    ok = crear_launcher()
    if not ok:
        sys.exit(1)
    # Pausa solo si se ejecutó directamente (no desde bat)
    if sys.stdin.isatty():
        input("\n  Presiona Enter para cerrar...")
