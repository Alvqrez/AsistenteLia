# main.py — Punto de entrada de Lia.
#
# Arranca el LiaKernel (nueva arquitectura: EventBus + IntentRouter + Skills) y
# la GUI (PySide6 + React). El antiguo `Lia.py` (god-object) queda como fallback
# hasta validar esta versión; ya no se usa aquí.
import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler

# Fuerza UTF-8 en la consola. Varios módulos imprimen emojis/acentos; en una
# consola cp1252 (Windows) eso provocaba UnicodeEncodeError. reconfigure puede
# no existir si stdout es None (modo windowed) → se ignora con seguridad.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Añade src/ al path para que los módulos hagan "from mod_X import ..." y
# "from core... / from skills..." funcionen tanto en dev como empaquetado.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def setup_logging():
    """
    Configura logging para toda la app. Antes vivía en Lia.py; al cambiar el
    entry point a main.py se había perdido. Consola + archivo rotatorio en
    data/lia.log (observabilidad en producción).
    """
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        os.makedirs(data_dir, exist_ok=True)
        fh = RotatingFileHandler(os.path.join(data_dir, "lia.log"),
                                 maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except Exception as ex:
        logging.getLogger("lia").warning("No se pudo crear el log de archivo: %s", ex)

from PySide6.QtWidgets import QApplication

from core.kernel import LiaKernel
from mod_gui import LiaMainWindow


def main():
    setup_logging()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    print("[MAIN] Iniciando Lia (kernel + skills)...")

    try:
        lia = LiaKernel()
        window = LiaMainWindow(lia)

        # Conecta la ventana al bus de eventos para logs/estado en la GUI.
        lia.set_gui_window(window)

        # Bucle de escucha + detector de aplausos en hilo daemon (no bloquea Qt).
        threading.Thread(target=lia.run, daemon=True).start()

        print("[MAIN] Lia corriendo en el tray. ¡Listo!")
        sys.exit(app.exec())

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()