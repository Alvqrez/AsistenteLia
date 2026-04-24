import os
import json
import time
import datetime


class ModuloMemoria:
    def __init__(self, funcion_hablar):
        self.hablar = funcion_hablar
        # El archivo se guardará en la raíz del proyecto, tal como lo tienes
        self.archivo_habitos = "../lia_historial.json"
        self.ruta_pendientes = os.path.expandvars(r"%USERPROFILE%\Documents\Notas\Pendientes.md")
        self.habitos = self.cargar_habitos()

    # --- APRENDIZAJE DE HÁBITOS ---
    def cargar_habitos(self):
        if os.path.exists(self.archivo_habitos):
            try:
                with open(self.archivo_habitos, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"interacciones_totales": 0, "rutinas": {}}

    def guardar_habitos(self):
        with open(self.archivo_habitos, 'w', encoding='utf-8') as f:
            json.dump(self.habitos, f, indent=4)

    def registrar_accion(self, accion):
        """Guarda qué haces y a qué hora para aprender de ti"""
        # Validación: Si el JSON viejo no tiene las llaves, las creamos
        if "interacciones_totales" not in self.habitos:
            self.habitos["interacciones_totales"] = 0
        if "rutinas" not in self.habitos:
            self.habitos["rutinas"] = {}

        self.habitos["interacciones_totales"] += 1
        hora_actual = datetime.datetime.now().strftime("%H")

        if accion not in self.habitos["rutinas"]:
            self.habitos["rutinas"][accion] = {"veces_usado": 0, "horas_frecuentes": {}}

        self.habitos["rutinas"][accion]["veces_usado"] += 1

        if hora_actual not in self.habitos["rutinas"][accion]["horas_frecuentes"]:
            self.habitos["rutinas"][accion]["horas_frecuentes"][hora_actual] = 0
        self.habitos["rutinas"][accion]["horas_frecuentes"][hora_actual] += 1

        self.guardar_habitos()

    # --- GESTIÓN DE OBSIDIAN Y RECORDATORIOS ---
    def agregar_pendiente(self, texto):
        try:
            if not texto: return
            os.makedirs(os.path.dirname(self.ruta_pendientes), exist_ok=True)
            mode = "a" if os.path.exists(self.ruta_pendientes) else "w"
            with open(self.ruta_pendientes, mode, encoding="utf-8") as f:
                if mode == "w": f.write("# Pendientes\n\n")
                f.write(f"- [ ] {texto}\n")
            self.hablar(f"Anotado en tus pendientes: {texto}")
            self.registrar_accion("agregar_pendiente")
        except Exception as e:
            print(f"❌ Error al agregar pendiente: {e}")

    def completar_pendiente(self, texto_busqueda):
        try:
            if not os.path.exists(self.ruta_pendientes):
                self.hablar("No tienes archivo de pendientes.")
                return

            with open(self.ruta_pendientes, "r", encoding="utf-8") as file:
                lineas = file.readlines()

            lineas_restantes = []
            tarea_eliminada = False

            for linea in lineas:
                if "- [ ]" in linea and texto_busqueda.lower() in linea.lower():
                    tarea_eliminada = True
                    continue
                lineas_restantes.append(linea)

            if tarea_eliminada:
                with open(self.ruta_pendientes, "w", encoding="utf-8") as file:
                    file.writelines(lineas_restantes)
                self.hablar("Tarea completada y eliminada de Obsidian.")
                self.registrar_accion("completar_pendiente")
            else:
                self.hablar(f"No encontré esa tarea.")
        except Exception as e:
            self.hablar("Hubo un error al modificar tu archivo.")

    def recordar_pendientes_activos(self):
        """Lee los pendientes y te recuerda si tienes cosas importantes"""
        try:
            if not os.path.exists(self.ruta_pendientes): return
            with open(self.ruta_pendientes, "r", encoding="utf-8") as file:
                pendientes = [linea.replace("- [ ]", "").strip() for linea in file if "- [ ]" in linea]

            if pendientes:
                self.hablar(
                    f"Recordatorio: Tienes {len(pendientes)} tareas en espera. La principal es: {pendientes[0]}.")
        except Exception:
            pass