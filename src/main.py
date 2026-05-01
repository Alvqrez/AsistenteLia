#!/usr/bin/env python3
"""
main.py — Punto de entrada de Lia v4.4.1
Arranca Lia en segundo plano. La GUI NO se abre al iniciar;
solo aparece el icono en el System Tray.
    - Doble clic en el icono  → abre la GUI
    - Clic derecho            → menú contextual
    - python main.py --show   → abre la GUI directamente al iniciar
"""

import sys
import os
import threading

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from mod_gui import LiaMainWindow, LiaWorker, STYLE_GLOBAL


def main():
    # --show abre la GUI inmediatamente (util para debug manual)
    abrir_gui = "--show" in sys.argv

    app = QApplication(sys.argv)
    app.setApplicationName("Lia")
    app.setApplicationDisplayName("Lia Asistente Personal")
    app.setQuitOnLastWindowClosed(False)  # no cerrar aunque se cierre la ventana
    app.setStyleSheet(STYLE_GLOBAL)

    try:
        app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    except Exception:
        pass

    # Crear la ventana PERO no mostrarla todavia
    window = LiaMainWindow(lia_instance=None)
    window.signal_status.emit("iniciando")

    if abrir_gui:
        window.show()

    # Inicializar Lia en hilo separado para no bloquear el tray
    def _init_lia():
        try:
            from Lia import LiaAssistant
            lia = LiaAssistant()
            lia._gui_window = window
            window.lia = lia
            window.signal_status.emit("activa")
            window.signal_log.emit("Lia v4.4.1 en linea. A su servicio, Leonardo.")

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
