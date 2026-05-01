#!/usr/bin/env python3

import os
import sys
import threading
import time

import pyttsx3
import speech_recognition as sr

from mod_audio         import ClapDetector
from mod_sistema       import SystemTools
from mod_memoria       import MemoryTools
from mod_internet      import InternetTools
from mod_dev           import DevTools
from mod_voz           import VozEngine
from mod_personalidad  import Persona
from mod_productividad import ProductividadTools
from mod_focus         import FocusTools
from mod_resumen       import ResumenTools

_SRC_DIR          = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR         = os.path.dirname(_SRC_DIR)
COMANDOS_TXT_PATH = os.path.join(_ROOT_DIR, "lia_comandos.txt")

_SINONIMOS_VSCODE = {
    "necesito programar", "quiero programar", "a programar",
    "vscode", "vs code", "visual studio", "código", "editor",
    "modo código", "modo programacion", "a codear", "codear",
    "abre el editor", "entorno de desarrollo"
}
_SINONIMOS_ESTUDIO = {
    "modo estudio", "a estudiar", "necesito estudiar",
    "quiero estudiar", "tiempo de estudiar", "hora de estudiar",
    "a trabajar", "modo trabajo", "chatgpt y whatsapp"
}
_SINONIMOS_JUEGO = {
    "modo juego", "a jugar", "quiero jugar", "hora de jugar",
    "gaming", "videojuegos", "necesito discord", "abre discord"
}
_SINONIMOS_PENDIENTES = {
    "pendientes", "mis pendientes", "qué tengo pendiente",
    "que tengo pendiente", "mis tareas", "lista de tareas",
    "qué debo hacer", "que debo hacer"
}
_SINONIMOS_CLIMA = {
    "clima", "tiempo", "cómo está el clima", "como esta el clima",
    "qué temperatura hace", "que temperatura hace",
    "va a llover", "llueve hoy", "hace frío", "hace calor"
}
_SINONIMOS_INICIO = {
    "inicio", "rutina", "buenos días", "buen día", "buenas",
    "empecemos", "comencemos", "arranquemos el día",
    "empezar el día", "empezar el dia"
}
_SINONIMOS_SISTEMA = {
    "sistema", "cpu", "ram", "recursos", "cómo está la pc",
    "como esta la pc", "uso del sistema", "rendimiento"
}
_SINONIMOS_PAUSA = {
    "pausate", "pausa", "detente", "para", "descansa",
    "modo descanso", "silencia los aplausos"
}
_SINONIMOS_SILENCIO_VOZ = {
    "silencio", "cállate", "callate", "modo silencioso",
    "sin voz", "no hables", "mute"
}


def _coincide(cmd: str, sinonimos: set) -> bool:
    cmd_l = cmd.lower()
    return any(s in cmd_l for s in sinonimos)


class LiaAssistant:

    MENU_TEXTO = """
+==============================================================+
|                   ASISTENTE LIA  v4.5.0                        |
+==============================================================+
|  APLAUSOS                                                    |
|    1 aplauso   ->  Modo Estudio  (ChatGPT + WhatsApp)        |
|    2 aplausos  ->  Modo Codigo   (VS Code + GitHub + Spotify)|
|    3 aplausos  ->  Modo Juego    (Discord + TimerResolution) |
|                                                              |
|  COMANDOS Y VARIACIONES  (di "Lia, ...")                     |
|  -- Modos rápidos ---                                        |
|    "necesito programar" / "a codear" / "modo código"         |
|    "a estudiar" / "modo estudio" / "tiempo de estudiar"      |
|    "a jugar" / "gaming" / "modo juego"                       |
|  -- Rutina ---                                               |
|    "inicio" / "buenos días" / "empecemos"                    |
|  -- Voz ---                                                  |
|    "silencio" / "cállate" / "mute"                           |
|    "habla" / "activa voz"                                    |
|  -- Control ---                                              |
|    "pausate" / "detente" / "descansa"                        |
|    "apagate"                                                 |
|  -- Aplicaciones ---                                         |
|    "abre [app]"                                              |
|    "cierra todo"                                             |
|  -- Pendientes ---                                           |
|    "pendientes" / "mis tareas" / "qué debo hacer"            |
|    "anota [tarea]"                                           |
|    "tarea X lista"                                           |
|  -- Dev ---                                                  |
|    "crea proyecto React en [carpeta]"                        |
|    "git status / push / pull"                                |
|  -- Productividad ---                                        |
|    "pomodoro [N]"                                            |
|    "recuerda X en N minutos"                                 |
|    "clima" / "cómo está el clima" / "va a llover"            |
|  -- Sistema ---                                              |
|    "sistema" / "cpu" / "rendimiento"                         |
|    "disco"                                                   |
|    "bloquea"                                                 |
|  -- Internet ---                                             |
|    "busca [X]"                                               |
|    "youtube [X]"                                             |
|  -- Notas ---                                                |
|    "nota [clave] [texto]"                                    |
|    "comandos"                                                |
|    "gracias"                                                 |
+==============================================================+
"""

    def __init__(self):
        self.is_active       = True
        self._shutdown_flag  = threading.Event()
        self._gui_window     = None

        # Personalidad J.A.R.V.I.S.
        self.persona = Persona(nombre="Leonardo")

        self.voz = VozEngine(
            on_speak_start=lambda: self.detector.set_lia_hablando(True) if hasattr(self, 'detector') else None,
            on_speak_end=lambda: self.detector.set_lia_hablando(False) if hasattr(self, 'detector') else None
        )

        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.recognizer.pause_threshold          = 1.1
        self.recognizer.non_speaking_duration    = 0.6
        self.recognizer.dynamic_energy_threshold = True

        self.sistema       = SystemTools(self)
        self.memoria       = MemoryTools(self)
        self.internet      = InternetTools(self)
        self.dev           = DevTools(self)
        self.productividad = ProductividadTools(self)
        self.focus         = FocusTools(self)
        self.resumen       = ResumenTools(self)

        self.memoria._shutdown_flag = self._shutdown_flag

        self.detector = ClapDetector(on_sequence=self._handle_clap_sequence)

        self.detector.calibrar()
        self._generar_txt_comandos()
        self.hablar(self.persona.saludo_inicio())

    def hablar(self, texto: str):
        print(f"Lia: {texto}")
        if self._gui_window:
            try:
                self._gui_window.signal_log.emit(f"🗣 {texto}")
            except Exception:
                pass

        self.voz.decir(texto)

    def registrar_actividad(self, actividad: str):
        self.memoria.registrar_actividad(actividad)
        if self._gui_window:
            try:
                self._gui_window.signal_log.emit(f"✓ {actividad}")
            except Exception:
                pass

    def mostrar_menu(self):
        # El menú está en lia_comandos.txt. No se imprime en terminal.
        pass

    def _generar_txt_comandos(self):
        try:
            with open(COMANDOS_TXT_PATH, "w", encoding="utf-8") as f:
                f.write(self.MENU_TEXTO)
        except Exception as ex:
            print(f"No se pudo crear lia_comandos.txt: {ex}")

    def abrir_comandos_txt(self):
        import subprocess, platform
        try:
            if not os.path.exists(COMANDOS_TXT_PATH):
                self._generar_txt_comandos()
            if platform.system() == "Windows":
                subprocess.Popen(["notepad.exe", COMANDOS_TXT_PATH])
            else:
                subprocess.Popen(["xdg-open", COMANDOS_TXT_PATH])
            self.hablar("Aquí tienes todos mis comandos.")
            self.registrar_actividad("Abrió Comandos.txt")
        except Exception as ex:
            print(f"Error al abrir comandos: {ex}")

    def cerrar_comandos_txt(self):
        import subprocess, platform
        try:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/f", "/im", "notepad.exe"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _handle_clap_sequence(self, count: int):
        import json
        modos_path = os.path.join(_ROOT_DIR, "../lia_modos.json")
        modos = []
        try:
            if os.path.exists(modos_path):
                with open(modos_path, "r", encoding="utf-8") as f:
                    modos = json.load(f).get("modos", [])
        except Exception:
            pass

        if not self.is_active and count >= 3:
            self.is_active = True
            self.detector.set_active(True)
            self.hablar(self.persona.reactivacion())
            if self._gui_window:
                self._gui_window.signal_status.emit("activa")
            return

        if not self.is_active:
            return

        modo = next((m for m in modos if m.get("aplausos") == count), None)

        if modo:
            accion = modo.get("accion", "")
            if accion == "modo_estudio":
                self.sistema.modo_estudio()
            elif accion == "modo_programacion":
                self.sistema.modo_programacion()
            elif accion == "modo_juego":
                self.sistema.modo_juego()
            else:
                if count == 1:
                    self.sistema.modo_estudio()
                elif count == 2:
                    self.sistema.modo_programacion()
                elif count >= 3:
                    self.sistema.modo_juego()
        else:
            if count == 1:
                self.sistema.modo_estudio()
            elif count == 2:
                self.sistema.modo_programacion()
            elif count >= 3:
                self.sistema.modo_juego()

    def _parse_command(self, cmd: str):
        if not cmd.strip():
            return

        cmd_l = cmd.lower()

        if "gracias" in cmd_l:
            self.cerrar_comandos_txt()
            self.hablar(self.persona.gracias())
            return

        if "comandos" in cmd_l:
            self.abrir_comandos_txt()
            return

        if _coincide(cmd_l, _SINONIMOS_INICIO):
            self.internet.rutina_inicio()
            return

        if _coincide(cmd_l, _SINONIMOS_SILENCIO_VOZ):
            self.voz.set_silencioso(True)
            print("Modo silencioso activado.")
            return

        if "habla" in cmd_l or "activa voz" in cmd_l or "voz normal" in cmd_l:
            self.voz.set_silencioso(False)
            self.hablar(self.persona.voz_reactivada())
            return

        if _coincide(cmd_l, _SINONIMOS_PAUSA):
            self.is_active = False
            self.detector.set_active(False)
            self.hablar(self.persona.pausa())
            if self._gui_window:
                self._gui_window.signal_status.emit("pausada")
            return

        if "apagate" in cmd_l or "apagar" in cmd_l or "ciérrate" in cmd_l:
            self.hablar(self.persona.apagado())
            self._shutdown_flag.set()
            if self._gui_window:
                self._gui_window.signal_status.emit("apagada")
            return

        if _coincide(cmd_l, _SINONIMOS_VSCODE) and "abre" not in cmd_l:
            self.sistema.modo_programacion()
            return

        if _coincide(cmd_l, _SINONIMOS_ESTUDIO) and "abre" not in cmd_l:
            self.sistema.modo_estudio()
            return

        if _coincide(cmd_l, _SINONIMOS_JUEGO) and "abre" not in cmd_l:
            self.sistema.modo_juego()
            return

        if "crea proyecto react" in cmd_l or "crear proyecto react" in cmd_l:
            for kw in ("crea proyecto react en ", "crear proyecto react en ",
                       "crea proyecto react ", "crear proyecto react "):
                if kw in cmd_l:
                    nombre = cmd_l.split(kw, 1)[-1].strip()
                    self.dev.crear_proyecto_react(nombre)
                    return
            self.hablar("¿En qué carpeta quieres crear el proyecto React?")
            return

        if "abre " in cmd_l or "abrir " in cmd_l:
            for trigger in ("abre ", "abrir "):
                if trigger in cmd_l:
                    app = cmd_l.split(trigger, 1)[-1].strip()
                    if app:
                        self.sistema.open_application(app)
                    else:
                        self.hablar("¿Qué quieres que abra?")
                    return

        if "cierra todo" in cmd_l or "cerrar todo" in cmd_l:
            self.sistema.cerrar_todo()
            return

        if _coincide(cmd_l, _SINONIMOS_PENDIENTES):
            self.memoria.decir_pendientes()
            return

        for verbo in ("anota", "apunta", "agrega pendiente", "agrega"):
            if verbo in cmd_l:
                texto = cmd_l.split(verbo, 1)[-1].strip().strip(",.-: ")
                if texto:
                    self.memoria.agregar_pendiente(texto)
                else:
                    self.hablar("¿Qué quieres que anote?")
                return

        for kw in ("lista", "completada", "hecha", "terminada", "completa"):
            if kw in cmd_l and "tarea" in cmd_l:
                tarea = (cmd_l.replace("tarea", "").replace(kw, "")
                              .strip().strip(",.-: "))
                self.memoria.completar_tarea(tarea)
                return

        if cmd_l.startswith("nota "):
            partes = cmd_l[5:].strip().split(" ", 1)
            if len(partes) == 2:
                self.memoria.guardar_nota(partes[0], partes[1])
            else:
                self.hablar("Di: nota [clave] [contenido].")
            return

        if "recuerda nota " in cmd_l:
            clave = cmd_l.replace("recuerda nota", "").strip()
            self.memoria.obtener_nota(clave)
            return

        if "pomodoro" in cmd_l:
            minutos = 25
            for p in cmd_l.split():
                if p.isdigit():
                    minutos = int(p)
                    break
            self.memoria.iniciar_pomodoro(minutos)
            return

        if "recuerda" in cmd_l and " en " in cmd_l:
            try:
                partes  = cmd_l.split(" en ", 1)
                mensaje = partes[0].replace("recuerda", "").strip()
                resto   = partes[1]
                mins    = float("".join(c for c in resto if c.isdigit() or c == ".") or "5")
                self.memoria.recordar_en(mensaje, mins)
            except Exception:
                self.hablar("No entendí el recordatorio.")
            return

        if _coincide(cmd_l, _SINONIMOS_CLIMA):
            self.internet.decir_clima()
            return

        if "busca " in cmd_l or "buscar " in cmd_l:
            consulta = cmd_l.replace("busca", "").replace("buscar", "").strip()
            if consulta:
                self.internet.buscar_google(consulta)
            return

        if "youtube " in cmd_l:
            consulta = cmd_l.split("youtube ", 1)[-1].strip()
            if consulta:
                self.internet.buscar_youtube(consulta)
            return

        if "recalibra" in cmd_l or "calibra" in cmd_l:
            self.detector.calibrar()
            return

        if _coincide(cmd_l, _SINONIMOS_SISTEMA):
            self.sistema.obtener_info_sistema()
            return

        if "disco" in cmd_l:
            self.sistema.obtener_uso_disco()
            return

        if "bloquea" in cmd_l or "bloquear" in cmd_l:
            self.sistema.bloquear_pc()
            return

        if "apaga la pc" in cmd_l or "apaga el pc" in cmd_l:
            self.sistema.apagar_pc(segundos=60)
            return

        if "cancela apagado" in cmd_l:
            self.sistema.cancelar_apagado()
            return

        if "git status" in cmd_l or "estado del repo" in cmd_l:
            self.dev.estado_git()
            return

        if "git push" in cmd_l:
            self.dev.hacer_push()
            return

        if "git pull" in cmd_l:
            self.dev.hacer_pull()
            return

        if "ramas" in cmd_l:
            self.dev.listar_ramas()
            return

        if "ayuda" in cmd_l or "menú" in cmd_l or "menu" in cmd_l:
            self.abrir_comandos_txt()
            return

        # ── Resumen del día (mod_resumen) ──────────────────────────
        if "resumen" in cmd_l or "qué hice hoy" in cmd_l or "que hice hoy" in cmd_l:
            self.resumen.resumen_del_dia()
            return

        # ── Hora y fecha (mod_productividad) ───────────────────────
        if "qué hora" in cmd_l or "que hora" in cmd_l or "la hora" in cmd_l:
            self.productividad.decir_hora()
            return

        if "qué fecha" in cmd_l or "que fecha" in cmd_l or "qué día es" in cmd_l or "que dia es" in cmd_l:
            self.productividad.decir_fecha()
            return

        # ── Calculadora por voz (mod_productividad) ────────────────
        if any(kw in cmd_l for kw in ("cuánto es", "cuanto es", "calcula", "resultado de")):
            if self.productividad.calcular(cmd_l):
                return

        # ── Conversiones (mod_productividad) ───────────────────────
        if "convierte " in cmd_l:
            self.productividad.convertir(cmd_l)
            return

        # ── Modo Enfoque (mod_focus) ────────────────────────────────
        if "modo enfoque" in cmd_l or "modo focus" in cmd_l:
            minutos = 25
            for p in cmd_l.split():
                if p.isdigit():
                    minutos = int(p)
                    break
            self.focus.activar(minutos)
            return

        if "termina enfoque" in cmd_l or "fin enfoque" in cmd_l or "desbloquea sitios" in cmd_l:
            self.focus.desactivar()
            return

    def _listen_loop(self):
        with self.microphone as src:
            self.recognizer.adjust_for_ambient_noise(src, duration=1.0)

            while not self._shutdown_flag.is_set():
                if not self.is_active:
                    time.sleep(0.4)
                    continue
                try:
                    audio = self.recognizer.listen(src, timeout=None, phrase_time_limit=8)
                    cmd = self.recognizer.recognize_google(audio, language="es-MX").lower()

                    if "gracias" in cmd:
                        self.cerrar_comandos_txt()
                        self.hablar(self.persona.gracias())
                        continue

                    print(f"Escuché: '{cmd}'")

                    if cmd.strip() in ("lia", "lía"):
                        continue

                    if "lia" in cmd or "lía" in cmd:
                        limpio = (cmd
                                  .replace("lía,", "").replace("lia,", "")
                                  .replace("lía", "").replace("lia", "")
                                  .strip().strip(",. "))
                        if limpio:
                            self._parse_command(limpio)

                except sr.UnknownValueError:
                    pass
                except sr.RequestError as ex:
                    print(f"Error reconocimiento: {ex}")
                except Exception:
                    time.sleep(0.5)

    def run(self):
        voz = threading.Thread(target=self._listen_loop, daemon=True)
        voz.start()
        try:
            self.detector.start_loop(shutdown_flag=self._shutdown_flag)
        except KeyboardInterrupt:
            print("\nLia detenida.")
        finally:
            self._shutdown_flag.set()


if __name__ == "__main__":
    LiaAssistant().run()