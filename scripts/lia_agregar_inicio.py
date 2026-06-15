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

# ── Crear wrapper script para iniciar desde el directorio correcto ────────────
# El VBS ejecuta desde C:\Windows\System32 → necesitamos cambiar al directorio
# del proyecto antes de importar módulos. Creamos un script intermedio que hace esto.
WRAPPER_SCRIPT = os.path.join(LIA_ROOT, "_lia_startup_wrapper.py")
WRAPPER_CONTENT = f'''#!/usr/bin/env python3
import os
import sys
import runpy

# Cambiar al directorio raíz del proyecto
os.chdir({repr(LIA_ROOT)})

# Agregar src/ al path para que las importaciones funcionen
sys.path.insert(0, os.path.join({repr(LIA_ROOT)}, "src"))

# Ejecutar main.py de forma segura con runpy
try:
    runpy.run_path({repr(LIA_MAIN)}, run_name="__main__")
except Exception as e:
    # Log cualquier error (aunque sea en una ventana oculta)
    import traceback
    log_path = os.path.join({repr(LIA_ROOT)}, "data", "startup_error.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"Error al iniciar Lia:\\n{{traceback.format_exc()}}\\n\\n")
    sys.exit(1)
'''


def crear_launcher():
    # Verificar que main.py existe
    if not os.path.exists(LIA_MAIN):
        print(f"ERROR: No se encontró {LIA_MAIN}")
        print("Asegúrate de ejecutar este script desde la carpeta del proyecto.")
        return False

    # Crear el wrapper script que cambia de directorio correctamente
    try:
        with open(WRAPPER_SCRIPT, "w", encoding="utf-8") as f:
            f.write(WRAPPER_CONTENT)
    except Exception as e:
        print(f"ERROR: No se pudo crear el wrapper script: {e}")
        return False

    # El script VBS ejecuta pythonw wrapper sin mostrar ninguna ventana.
    # windowStyle=0 → oculto.  bWaitOnReturn=False → no espera.
    # El wrapper se encarga de cambiar al directorio correcto antes de ejecutar main.py
    vbs_content = (
        "' Launcher silencioso de Lia\n"
        'Set oShell = CreateObject("WScript.Shell")\n'
        f'oShell.Run """{PYTHON_EXE}"" ""{WRAPPER_SCRIPT}""", 0, False\n'
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
    print(f"  Wrapper  : {WRAPPER_SCRIPT}")
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
