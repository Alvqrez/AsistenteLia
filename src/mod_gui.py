# src/mod_gui.py
import os
import sys
from PySide6.QtWidgets import QMainWindow, QApplication, QSystemTrayIcon, QMenu
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Qt, Signal, QObject
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtGui import QIcon, QAction

from web_bridge import PythonBridge


class LiaMainWindow(QMainWindow):
    # Señales que el kernel usa para comunicar estado y logs a la GUI
    signal_log    = Signal(str)
    signal_status = Signal(str)
    # Señal para traer la ventana al frente desde otro hilo (comando "dashboard").
    # Emitir señales entre hilos es la forma thread-safe de tocar la UI en Qt.
    signal_show   = Signal()

    def __init__(self, lia_instance=None):
        super().__init__()
        self.lia = lia_instance
        self.signal_show.connect(self._show_window)

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

        # Conecta las señales de la ventana al bridge para reenviarlas a React
        self.signal_log.connect(self.bridge.log)
        self.signal_status.connect(self.bridge.setStatus)

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
                <h1 style='font-family:sans-serif;color:#38bdf8;background:#050810;padding:40px'>
                  Error: Interfaz no compilada
                </h1>
                <p style='font-family:sans-serif;color:#8099b4;padding:0 40px'>
                  Ejecuta en terminal: <code>cd web && npm run build</code>
                </p>
            """)
        else:
            self.web.load(QUrl.fromLocalFile(absolute_path))

        print("[GUI] Interfaz cargada correctamente")

        self._setup_tray()

    def _setup_tray(self):
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "lia_icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QApplication.style().standardIcon(
            QApplication.style().StandardPixmap.SP_ComputerIcon
        )

        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("Lia - Asistente Personal")

        menu = QMenu()
        action_show = QAction("Abrir Lia", self)
        action_show.triggered.connect(self._show_window)
        action_quit = QAction("Salir", self)
        action_quit.triggered.connect(QApplication.quit)
        menu.addAction(action_show)
        menu.addSeparator()
        menu.addAction(action_quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _show_window(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def log(self, texto: str):
        """Envía un mensaje de log a la interfaz"""
        self.bridge.log(texto)

    def set_status(self, estado: str):
        """Actualiza el estado de Lia en la interfaz"""
        self.bridge.setStatus(estado)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage("Lia", "Sigo corriendo en el tray.", QSystemTrayIcon.MessageIcon.Information, 2000)
