# main.py
import sys
from PySide6.QtWidgets import QApplication
from src.Lia import LiaAssistant
from src.mod_gui import LiaMainWindow


def main():
    app = QApplication(sys.argv)

    print("[MAIN] Iniciando Lia...")

    try:
        # Crea la instancia de Lia
        lia = LiaAssistant()

        # Crea y muestra la ventana
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