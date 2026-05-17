# src/mod_gui.py
import os
import sys
from PySide6.QtWidgets import QMainWindow, QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Qt
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtGui import QIcon

from .web_bridge import PythonBridge


class LiaMainWindow(QMainWindow):
    def __init__(self, lia_instance=None):
        super().__init__()
        self.lia = lia_instance

        self.setWindowTitle("Lia - Asistente Personal")
        self.setGeometry(100, 100, 1400, 850)
        self.setMinimumSize(1000, 700)

        # Crea el view web
        self.web = QWebEngineView()
        self.setCentralWidget(self.web)

        # Crea el bridge Python-JavaScript
        self.bridge = PythonBridge(lia_instance)
        channel = QWebChannel()
        channel.registerObject("pythonBridge", self.bridge)
        self.web.page().setWebChannel(channel)

        # Carga la interfaz React compilada
        dist_path = os.path.join(
            os.path.dirname(__file__),
            "..", "web", "dist", "index.html"
        )
        absolute_path = os.path.abspath(dist_path)

        if not os.path.exists(absolute_path):
            print(f"[ERROR] No se encontró: {absolute_path}")
            print("Ejecuta: cd web && npm run build")
            self.web.setHtml("""
                <h1>Error: Interfaz no compilada</h1>
                <p>Ejecuta en terminal: <code>cd web && npm run build</code></p>
            """)
        else:
            self.web.load(QUrl.fromLocalFile(absolute_path))

        # Opcional: descomenta para ver la consola de desarrollador
        # self.web.page().setDevToolsEnabled(True)

        print("[GUI] Interfaz cargada correctamente")

    def log(self, texto: str):
        """Envía un mensaje de log a la interfaz"""
        self.bridge.log(texto)

    def set_status(self, estado: str):
        """Actualiza el estado en la interfaz"""
        self.bridge.setStatus(estado)

    def closeEvent(self, event):
        """Cuando cierras la ventana"""
        if self.lia and hasattr(self.lia, '_shutdown_flag'):
            self.lia._shutdown_flag.set()
        event.accept()