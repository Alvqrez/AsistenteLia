#!/usr/bin/env python3
"""
mod_memoria.py  –  Módulo de Memoria
Responsabilidades:
  · Pendientes (agregar, leer, completar)
  · Historial de actividades de Lia
  · Notas rápidas en memoria persistente (JSON)
  · Pomodoro y recordatorios con voz + notificación
"""

import os
import json
import datetime
import threading
import time


# ── Rutas de archivos ────────────────────────────────────────
_SRC_DIR       = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR      = os.path.dirname(_SRC_DIR)
NOTAS_DIR      = os.path.join(os.path.expanduser("~"), "Documents", "Notas")
PENDIENTES_PATH = os.path.join(NOTAS_DIR, "Pendientes.md")
HISTORIAL_PATH  = os.path.join(_ROOT_DIR, "lia_historial.json")
MEMORIA_PATH    = os.path.join(_ROOT_DIR, "lia_memoria.json")


class MemoryTools:
    """
    Todo lo que Lia necesita recordar entre sesiones y en tiempo real.
    Recibe 'parent_lia' para hablar() y acceder a mod_sistema.notificar().
    """

    def __init__(self, parent_lia):
        self.lia             = parent_lia
        self.pomodoro_thread = None
        self._shutdown_flag  = None   # se asigna desde Lia.py en run()

        # Crear directorio de notas si no existe
        os.makedirs(NOTAS_DIR, exist_ok=True)

        # Cargar historial y memoria
        self.historial = self._cargar_json(HISTORIAL_PATH,
                                           default={"actividades": [], "estadisticas": {}})
        self.memoria   = self._cargar_json(MEMORIA_PATH,
                                           default={"notas": {}, "hechos": {}})

    # ════════════════════════════════════════════════════════
    #  UTILIDADES JSON
    # ════════════════════════════════════════════════════════

    def _cargar_json(self, ruta: str, default: dict) -> dict:
        try:
            if os.path.exists(ruta):
                with open(ruta, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️  No se pudo cargar {ruta}: {e}")
        return default

    def _guardar_json(self, ruta: str, data: dict):
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error al guardar {ruta}: {e}")

    # ════════════════════════════════════════════════════════
    #  HISTORIAL DE ACTIVIDADES
    # ════════════════════════════════════════════════════════

    def registrar_actividad(self, actividad: str):
        """Guarda una actividad en el historial con timestamp."""
        ts = datetime.datetime.now().isoformat()
        self.historial["actividades"].append({"timestamp": ts, "actividad": actividad})
        self.historial["estadisticas"][actividad] = \
            self.historial["estadisticas"].get(actividad, 0) + 1
        # Mantener solo las últimas 200 entradas
        self.historial["actividades"] = self.historial["actividades"][-200:]
        self._guardar_json(HISTORIAL_PATH, self.historial)

    # ════════════════════════════════════════════════════════
    #  PENDIENTES  (Obsidian/Markdown)
    # ════════════════════════════════════════════════════════

    def _asegurar_pendientes(self):
        """Crea el archivo de pendientes si no existe."""
        os.makedirs(NOTAS_DIR, exist_ok=True)
        if not os.path.exists(PENDIENTES_PATH):
            with open(PENDIENTES_PATH, "w", encoding="utf-8") as f:
                f.write("# Pendientes\n\n")

    def agregar_pendiente(self, texto: str):
        """Añade una tarea como '- [ ] texto' al archivo de pendientes."""
        texto = texto.strip().rstrip(".").strip()
        if not texto:
            self.lia.hablar("No entendí qué quieres anotar.")
            return
        try:
            self._asegurar_pendientes()
            with open(PENDIENTES_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n- [ ] {texto}\n")
            self.lia.hablar(f"Listo, anoté: {texto}.")
            self.registrar_actividad("Agregó pendiente")
        except Exception as e:
            self.lia.hablar("No pude guardar el pendiente.")
            print(f"❌ {e}")

    def decir_pendientes(self, limite: int = 5):
        """Lee en voz alta los pendientes sin completar."""
        try:
            if not os.path.exists(PENDIENTES_PATH):
                self.lia.hablar("No encontré tu lista de pendientes.")
                return
            pendientes = []
            with open(PENDIENTES_PATH, "r", encoding="utf-8") as f:
                for linea in f:
                    if "- [ ]" in linea:
                        item = linea.replace("- [ ]", "").strip()
                        if item:
                            pendientes.append(item)
            if not pendientes:
                self.lia.hablar("No tienes pendientes.")
                return
            self.lia.hablar(f"Tienes {len(pendientes)} pendiente{'s' if len(pendientes) != 1 else ''}.")
            for item in pendientes[:limite]:
                self.lia.hablar(item)
                time.sleep(0.25)
        except Exception as e:
            self.lia.hablar("No pude leer los pendientes.")
            print(f"❌ {e}")

    def completar_tarea(self, texto_tarea: str):
        """
        Marca como completada la tarea que más se parezca al texto dado.
        Cambia '- [ ]' por '- [x]'.
        """
        texto_tarea = texto_tarea.lower().strip()
        if not texto_tarea:
            self.lia.hablar("Dime qué tarea completaste.")
            return
        try:
            self._asegurar_pendientes()
            with open(PENDIENTES_PATH, "r", encoding="utf-8") as f:
                lineas = f.readlines()

            encontrada  = False
            nombre_real = ""
            nuevas      = []

            for linea in lineas:
                if "- [ ]" in linea and not encontrada:
                    contenido = linea.replace("- [ ]", "").strip().lower()
                    if texto_tarea in contenido or contenido in texto_tarea:
                        nuevas.append(linea.replace("- [ ]", "- [x]"))
                        encontrada  = True
                        nombre_real = linea.replace("- [ ]", "").strip()
                        continue
                nuevas.append(linea)

            if encontrada:
                with open(PENDIENTES_PATH, "w", encoding="utf-8") as f:
                    f.writelines(nuevas)
                self.lia.hablar(f"Perfecto, marqué '{nombre_real}' como completada.")
                self.registrar_actividad("Completó tarea")
            else:
                self.lia.hablar(f"No encontré ninguna tarea que diga '{texto_tarea}'.")
        except Exception as e:
            self.lia.hablar("No pude actualizar los pendientes.")
            print(f"❌ {e}")

    # ════════════════════════════════════════════════════════
    #  NOTAS RÁPIDAS  (en memoria JSON)
    # ════════════════════════════════════════════════════════

    def guardar_nota(self, clave: str, contenido: str):
        """Guarda una nota rápida con clave personalizada."""
        clave = clave.lower().strip()
        if not clave or not contenido:
            self.lia.hablar("Necesito clave y contenido para la nota.")
            return
        self.memoria["notas"][clave] = {
            "contenido": contenido[:500],
            "timestamp": datetime.datetime.now().isoformat()
        }
        self._guardar_json(MEMORIA_PATH, self.memoria)
        self.lia.hablar(f"Guardé nota: {clave}.")
        self.registrar_actividad(f"Guardó nota: {clave}")

    def obtener_nota(self, clave: str):
        """Recupera y dice una nota guardada."""
        clave = clave.lower().strip()
        nota  = self.memoria["notas"].get(clave)
        if nota:
            self.lia.hablar(f"Tu nota: {nota['contenido']}")
            return nota["contenido"]
        self.lia.hablar(f"No encontré nota: {clave}.")
        return None

    def listar_notas(self):
        """Lista las claves de todas las notas guardadas."""
        notas = self.memoria.get("notas", {})
        if not notas:
            self.lia.hablar("No tienes notas guardadas.")
            return
        self.lia.hablar(f"Tienes {len(notas)} nota{'s' if len(notas) != 1 else ''}.")
        for clave in list(notas.keys())[:10]:
            self.lia.hablar(clave)
            time.sleep(0.2)

    def eliminar_nota(self, clave: str):
        """Elimina una nota por clave."""
        clave = clave.lower().strip()
        if clave in self.memoria.get("notas", {}):
            del self.memoria["notas"][clave]
            self._guardar_json(MEMORIA_PATH, self.memoria)
            self.lia.hablar(f"Eliminé nota: {clave}.")
            self.registrar_actividad(f"Eliminó nota: {clave}")
        else:
            self.lia.hablar("No encontré esa nota.")

    # ════════════════════════════════════════════════════════
    #  POMODORO  ⏱️
    # ════════════════════════════════════════════════════════

    def iniciar_pomodoro(self, minutos: int = 25):
        """
        Inicia un timer Pomodoro en un hilo daemon.
        Al terminar avisa con voz y notificación toast.
        """
        if self.pomodoro_thread and self.pomodoro_thread.is_alive():
            self.lia.hablar("Ya hay un pomodoro corriendo.")
            return

        def _run():
            self.lia.hablar(f"Pomodoro de {minutos} minutos iniciado.")
            # Espera en intervalos de 1 s para poder detectar shutdown
            for _ in range(minutos * 60):
                if self._shutdown_flag and self._shutdown_flag.is_set():
                    return
                time.sleep(1)
            if not (self._shutdown_flag and self._shutdown_flag.is_set()):
                self.lia.hablar("Tiempo. El pomodoro terminó. Toma un descanso.")
                # Intentar notificación via mod_sistema
                try:
                    self.lia.sistema.notificar(
                        "Lia – Pomodoro",
                        f"{minutos} minutos completados. Descansa 5."
                    )
                except Exception:
                    pass
                self.registrar_actividad("Pomodoro completado")

        self.pomodoro_thread = threading.Thread(target=_run, daemon=True)
        self.pomodoro_thread.start()
        self.registrar_actividad("Inició Pomodoro")

    # ════════════════════════════════════════════════════════
    #  RECORDATORIOS  ⏰
    # ════════════════════════════════════════════════════════

    def recordar_en(self, mensaje: str, minutos: float):
        """
        Programa una alarma en N minutos.
        Avisa con voz y notificación toast al dispararse.
        """
        if minutos <= 0:
            self.lia.hablar("El tiempo debe ser mayor que cero.")
            return

        def _run():
            for _ in range(int(minutos * 60)):
                if self._shutdown_flag and self._shutdown_flag.is_set():
                    return
                time.sleep(1)
            if not (self._shutdown_flag and self._shutdown_flag.is_set()):
                self.lia.hablar(f"Recordatorio: {mensaje}.")
                try:
                    self.lia.sistema.notificar("Lia – Recordatorio", mensaje)
                except Exception:
                    pass
                self.registrar_actividad(f"Recordatorio disparado: {mensaje}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        self.lia.hablar(f"Listo, te recuerdo '{mensaje}' en {minutos:.0f} minutos.")
        self.registrar_actividad(f"Programó recordatorio: {mensaje}")