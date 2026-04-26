#!/usr/bin/env python3

import logging
import os
import json
import re
import datetime
import threading
import time

logger = logging.getLogger("lia.memoria")

_SRC_DIR        = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR       = os.path.dirname(_SRC_DIR)
NOTAS_DIR       = os.path.join(os.path.expanduser("~"), "Documents", "Notas")
PENDIENTES_PATH = os.path.join(NOTAS_DIR, "Pendientes.md")
HISTORIAL_PATH  = os.path.join(_ROOT_DIR, "lia_historial.json")
MEMORIA_PATH    = os.path.join(_ROOT_DIR, "lia_memoria.json")


class MemoryTools:

    def __init__(self, parent_lia):
        self.lia             = parent_lia
        self.pomodoro_thread = None
        self._shutdown_flag  = None

        os.makedirs(NOTAS_DIR, exist_ok=True)

        self.historial = self._cargar_json(HISTORIAL_PATH, {"actividades": [], "estadisticas": {}})
        self.memoria   = self._cargar_json(MEMORIA_PATH,   {"notas": {}, "hechos": {}})

    def _cargar_json(self, ruta: str, default: dict) -> dict:
        try:
            if os.path.exists(ruta):
                with open(ruta, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as ex:
            logger.error("No se pudo cargar '%s': %s", ruta, ex)
        return default

    def _guardar_json(self, ruta: str, data: dict):
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as ex:
            logger.error("No se pudo guardar '%s': %s", ruta, ex)

    def registrar_actividad(self, actividad: str):
        ts = datetime.datetime.now().isoformat()
        self.historial["actividades"].append({"timestamp": ts, "actividad": actividad})
        self.historial["estadisticas"][actividad] = \
            self.historial["estadisticas"].get(actividad, 0) + 1
        self.historial["actividades"] = self.historial["actividades"][-200:]
        self._guardar_json(HISTORIAL_PATH, self.historial)

    def _asegurar_pendientes(self):
        os.makedirs(NOTAS_DIR, exist_ok=True)
        if not os.path.exists(PENDIENTES_PATH):
            with open(PENDIENTES_PATH, "w", encoding="utf-8") as f:
                f.write("# Pendientes\n\n")
            logger.info("Archivo de pendientes creado en '%s'.", PENDIENTES_PATH)

    def _parsear_pendiente(self, linea: str):
        linea = linea.strip().lstrip("\ufeff")
        m = re.match(r"^-\s*\[\s*\]\s*(.*)", linea)
        return m.group(1).strip() if m else None

    def agregar_pendiente(self, texto: str):
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
        except Exception as ex:
            logger.error("Error al agregar pendiente: %s", ex)
            self.lia.hablar("No pude guardar el pendiente.")

    def decir_pendientes(self, limite: int = 5):
        logger.debug("Leyendo pendientes de '%s'.", PENDIENTES_PATH)
        try:
            if not os.path.exists(PENDIENTES_PATH):
                self._asegurar_pendientes()
                self.lia.hablar("No encontré tu lista de pendientes. Creé un archivo nuevo.")
                return
            pendientes = []
            with open(PENDIENTES_PATH, "r", encoding="utf-8-sig") as f:
                for linea in f:
                    item = self._parsear_pendiente(linea)
                    if item:
                        pendientes.append(item)
            logger.debug("Pendientes encontrados: %d", len(pendientes))
            if not pendientes:
                self.lia.hablar("No tienes tareas pendientes.")
                return
            total = len(pendientes)
            self.lia.hablar(f"Tienes {total} pendiente{'s' if total != 1 else ''}.")
            for item in pendientes[:limite]:
                self.lia.hablar(item)
                time.sleep(0.25)
            if total > limite:
                self.lia.hablar(f"Y {total - limite} tarea{'s' if total - limite != 1 else ''} más.")
        except Exception as ex:
            logger.error("Error al leer pendientes: %s", ex)
            self.lia.hablar("No pude leer los pendientes.")

    def completar_tarea(self, texto_tarea: str):
        texto_tarea = texto_tarea.lower().strip()
        if not texto_tarea:
            self.lia.hablar("Dime qué tarea completaste.")
            return
        try:
            self._asegurar_pendientes()
            with open(PENDIENTES_PATH, "r", encoding="utf-8-sig") as f:
                lineas = f.readlines()
            encontrada  = False
            nombre_real = ""
            nuevas      = []
            for linea in lineas:
                if not encontrada:
                    item = self._parsear_pendiente(linea)
                    if item and (texto_tarea in item.lower() or item.lower() in texto_tarea):
                        nuevas.append(linea.replace("- [ ]", "- [x]").replace("-[ ]", "-[x]"))
                        encontrada  = True
                        nombre_real = item
                        continue
                nuevas.append(linea)
            if encontrada:
                with open(PENDIENTES_PATH, "w", encoding="utf-8") as f:
                    f.writelines(nuevas)
                self.lia.hablar(f"Marqué '{nombre_real}' como completada.")
                self.registrar_actividad("Completó tarea")
            else:
                self.lia.hablar(f"No encontré ninguna tarea que diga '{texto_tarea}'.")
        except Exception as ex:
            logger.error("Error al completar tarea: %s", ex)
            self.lia.hablar("No pude actualizar los pendientes.")

    def guardar_nota(self, clave: str, contenido: str):
        clave = clave.lower().strip()
        if not clave or not contenido:
            self.lia.hablar("Necesito clave y contenido para la nota.")
            return
        self.memoria["notas"][clave] = {
            "contenido": contenido[:500],
            "timestamp": datetime.datetime.now().isoformat(),
        }
        self._guardar_json(MEMORIA_PATH, self.memoria)
        self.lia.hablar(f"Guardé nota: {clave}.")
        self.registrar_actividad(f"Guardó nota: {clave}")

    def obtener_nota(self, clave: str):
        clave = clave.lower().strip()
        nota  = self.memoria["notas"].get(clave)
        if nota:
            self.lia.hablar(f"Tu nota: {nota['contenido']}")
            return nota["contenido"]
        self.lia.hablar(f"No encontré nota: {clave}.")
        return None

    def listar_notas(self):
        notas = self.memoria.get("notas", {})
        if not notas:
            self.lia.hablar("No tienes notas guardadas.")
            return
        self.lia.hablar(f"Tienes {len(notas)} nota{'s' if len(notas) != 1 else ''}.")
        for clave in list(notas.keys())[:10]:
            self.lia.hablar(clave)
            time.sleep(0.2)

    def eliminar_nota(self, clave: str):
        clave = clave.lower().strip()
        if clave in self.memoria.get("notas", {}):
            del self.memoria["notas"][clave]
            self._guardar_json(MEMORIA_PATH, self.memoria)
            self.lia.hablar(f"Eliminé nota: {clave}.")
            self.registrar_actividad(f"Eliminó nota: {clave}")
        else:
            self.lia.hablar("No encontré esa nota.")

    def iniciar_pomodoro(self, minutos: int = 25):
        if self.pomodoro_thread and self.pomodoro_thread.is_alive():
            self.lia.hablar("Ya hay un pomodoro corriendo.")
            return

        def _run():
            self.lia.hablar(f"Pomodoro de {minutos} minutos iniciado.")
            for _ in range(minutos * 60):
                if self._shutdown_flag and self._shutdown_flag.is_set():
                    return
                time.sleep(1)
            if not (self._shutdown_flag and self._shutdown_flag.is_set()):
                self.lia.hablar("Tiempo. El pomodoro terminó. Toma un descanso.")
                try:
                    self.lia.sistema.notificar("Lia – Pomodoro",
                                               f"{minutos} minutos completados. Descansa 5.")
                except Exception as ex:
                    logger.warning("Error al notificar pomodoro: %s", ex)
                self.registrar_actividad("Pomodoro completado")

        self.pomodoro_thread = threading.Thread(target=_run, daemon=True)
        self.pomodoro_thread.start()
        self.registrar_actividad("Inició Pomodoro")

    def recordar_en(self, mensaje: str, minutos: float):
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
                except Exception as ex:
                    logger.warning("Error al notificar recordatorio: %s", ex)
                self.registrar_actividad(f"Recordatorio disparado: {mensaje}")

        threading.Thread(target=_run, daemon=True).start()
        self.lia.hablar(f"Listo, te recuerdo '{mensaje}' en {minutos:.0f} minutos.")
        self.registrar_actividad(f"Programó recordatorio: {mensaje}")