# main.py
import sys
import os

# Añade src/ al path para que Lia.py pueda hacer "from mod_X import ..."
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from Lia import LiaAssistant
from mod_gui import LiaMainWindow


def main():
    app = QApplication(sys.argv)

    print("[MAIN] Iniciando Lia...")

    try:
        lia = LiaAssistant()
        window = LiaMainWindow(lia)
        window.show()

        print("[MAIN] Interfaz mostrada. ¡Listo!")

        sys.exit(app.exec())

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
