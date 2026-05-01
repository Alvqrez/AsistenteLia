#!/usr/bin/env python3
"""
main.py — Punto de entrada de Lia v10.
Lanza la GUI y arranca el asistente en un hilo de fondo.
"""

import sys
import os
import threading

# Asegura que el directorio del script esté en el path
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from mod_gui import LiaMainWindow, LiaWorker, STYLE_GLOBAL


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Lia")
    app.setApplicationDisplayName("Lia Asistente Personal")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(STYLE_GLOBAL)

    # Escalar a DPI en Windows
    try:
        app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    except Exception:
        pass

    # Ventana GUI primero (sin lia todavía)
    window = LiaMainWindow(lia_instance=None)
    window.signal_status.emit("iniciando")
    window.show()

    # Inicializar Lia en hilo separado para no bloquear la GUI
    def _init_lia():
        try:
            from Lia import LiaAssistant
            lia = LiaAssistant()
            lia._gui_window = window
            window.lia = lia
            window.signal_status.emit("activa")
            window.signal_log.emit("Lia v10 en linea. A su servicio, Leonardo.")

            worker = LiaWorker(lia)
            window.worker = worker
            worker.log_updated.connect(window.signal_log)
            worker.start()
        except Exception as ex:
            window.signal_log.emit(f"[ERROR al iniciar Lia] {ex}")
            window.signal_status.emit("apagada")
            import traceback
            traceback.print_exc()

    t = threading.Thread(target=_init_lia, daemon=True)
    t.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
