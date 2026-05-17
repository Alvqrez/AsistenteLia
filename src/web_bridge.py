# src/web_bridge.py
from PySide6.QtCore import QObject, Slot, Signal


class PythonBridge(QObject):
    """Comunica JavaScript con Python"""

    # Signals para enviar datos a JavaScript
    statusChanged = Signal(str)
    logUpdated = Signal(str)

    def __init__(self, lia_instance):
        super().__init__()
        self.lia = lia_instance

    @Slot(str, result=str)
    def executeCommand(self, command):
        """Recibe comandos desde React"""
        print(f"[BRIDGE] Comando: {command}")
        try:
            if command.startswith("cmd:"):
                # Comando de texto
                cmd_text = command[4:]
                self.lia._parse_command(cmd_text)
                return "ok"

            elif command.startswith("action:"):
                # Acciones rápidas
                action = command[7:]
                self._handle_action(action)
                return "ok"

            return "error: comando no reconocido"
        except Exception as e:
            print(f"[ERROR] {e}")
            return f"error: {str(e)}"

    def _handle_action(self, action):
        """Maneja las acciones rápidas del dashboard"""
        print(f"[BRIDGE] Acción: {action}")

        actions = {
            "Pomodoro": lambda: self.lia.focus.activar(25) if hasattr(self.lia, 'focus') else None,
            "Recordatorio": lambda: print("Recordatorio activado"),
            "Clima": lambda: print("Obtener clima"),
            "Búsqueda": lambda: print("Abrir búsqueda"),
        }

        if action in actions and actions[action]:
            actions[action]()

    @Slot(str)
    def log(self, mensaje):
        """Recibe logs desde Python para mostrar en React"""
        self.logUpdated.emit(mensaje)

    @Slot(str)
    def setStatus(self, estado):
        """Cambia el estado de Lia en la interfaz"""
        self.statusChanged.emit(estado)