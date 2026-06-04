# src/web_bridge.py — Puente Python ↔ JavaScript (React) para la GUI.
#
# La GUI ya NO conoce los internals del asistente: envía texto/acciones y el
# kernel los enruta por el IntentRouter (misma vía que la voz). Esto mantiene la
# lógica separada de la interfaz (Fase 11).
import json
import logging

from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger("lia.bridge")


class PythonBridge(QObject):
    """Comunica JavaScript con Python."""

    statusChanged = Signal(str)
    logUpdated = Signal(str)

    # Acciones rápidas del dashboard → comando equivalente que entiende el router.
    _ACTION_COMMANDS = {
        "Pomodoro": "pomodoro 25",
        "Recordatorio": "mis recordatorios",
        "Clima": "clima",
        "Búsqueda": "abre google",
    }

    def __init__(self, lia_instance):
        super().__init__()
        self.lia = lia_instance

    def _route(self, texto: str):
        """Enruta texto al kernel (handle_text) con compatibilidad hacia atrás."""
        if hasattr(self.lia, "handle_text"):
            self.lia.handle_text(texto)
        elif hasattr(self.lia, "_parse_command"):
            self.lia._parse_command(texto)

    @Slot(str, result=str)
    def executeCommand(self, command):
        """Recibe comandos desde React."""
        print(f"[BRIDGE] Comando: {command}")
        try:
            if command.startswith("cmd:"):
                self._route(command[4:])
                return "ok"
            elif command.startswith("action:"):
                self._handle_action(command[7:])
                return "ok"
            return "error: comando no reconocido"
        except Exception as e:
            print(f"[ERROR] {e}")
            return f"error: {str(e)}"

    def _handle_action(self, action):
        """Maneja las acciones rápidas del dashboard enrutándolas como comandos."""
        print(f"[BRIDGE] Acción: {action}")
        comando = self._ACTION_COMMANDS.get(action)
        if comando:
            self._route(comando)

    @Slot(result=str)
    def getDashboardData(self):
        """Devuelve datos REALES del asistente para que React deje de usar mocks."""
        try:
            from services.dashboard_data import build
            return json.dumps(build(self.lia), ensure_ascii=False)
        except Exception as e:
            logger.debug("getDashboardData falló: %s", e)
            return json.dumps({"error": str(e)})

    @Slot(str)
    def log(self, mensaje):
        """Recibe logs desde Python para mostrar en React."""
        self.logUpdated.emit(mensaje)

    @Slot(str)
    def setStatus(self, estado):
        """Cambia el estado de Lia en la interfaz."""
        self.statusChanged.emit(estado)
