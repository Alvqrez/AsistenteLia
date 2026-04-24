import os
import pyautogui

class ModuloSistema:
    def __init__(self, funcion_hablar):
        self.hablar = funcion_hablar

    def cambiar_volumen(self, accion):
        if "sube" in accion or "subir" in accion:
            pyautogui.press("volumeup", presses=10)
            self.hablar("Subiendo el volumen.")
        elif "baja" in accion or "bajar" in accion:
            pyautogui.press("volumedown", presses=10)
            self.hablar("Bajando el volumen.")
        elif "silencia" in accion or "mute" in accion:
            pyautogui.press("volumemute")
            self.hablar("Volumen silenciado.")

    def apagar_pc(self):
        self.hablar("Atención. Iniciando secuencia de apagado en 15 segundos. Di 'Lia, aborta' si fue un error.")
        os.system("shutdown /s /t 15")

    def reiniciar_pc(self):
        self.hablar("Atención. Reiniciando el sistema en 15 segundos. Di 'Lia, aborta' para cancelar.")
        os.system("shutdown /r /t 15")

    def cancelar_apagado(self):
        os.system("shutdown /a")
        self.hablar("Secuencia de apagado abortada. El sistema continuará en línea.")