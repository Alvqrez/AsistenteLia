#!/usr/bin/env python3
"""
lia_quitar_inicio.py — Elimina Lia del inicio automático de Windows.

Borra el launcher VBS de la carpeta Startup del usuario.

Uso:
    python scripts/lia_quitar_inicio.py
    (o doble clic en lia_quitar_inicio.bat)
"""

import os
import sys

STARTUP_FOLDER = os.path.join(
    os.environ["APPDATA"],
    "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
)
VBS_PATH = os.path.join(STARTUP_FOLDER, "Lia.vbs")


def quitar_launcher():
    print()
    print("=" * 60)
    if os.path.exists(VBS_PATH):
        os.remove(VBS_PATH)
        print("  LIA ELIMINADA DEL INICIO DE WINDOWS")
        print("=" * 60)
        print(f"  Archivo eliminado: {VBS_PATH}")
        print()
        print("  Lia ya NO se iniciará automáticamente.")
        print("  Para volver a agregarla: lia_agregar_inicio.bat")
    else:
        print("  LIA NO ESTABA EN EL INICIO")
        print("=" * 60)
        print(f"  No se encontró: {VBS_PATH}")
        print()
        print("  No hay nada que eliminar.")
    print("=" * 60)


if __name__ == "__main__":
    quitar_launcher()
    if sys.stdin.isatty():
        input("\n  Presiona Enter para cerrar...")
