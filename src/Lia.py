#!/usr/bin/env python3

import difflib
import logging
import logging.handlers
import os
import queue
import random
import re
import threading
import time

import pyttsx3
import speech_recognition as sr

from mod_audio        import ClapDetector
from mod_sistema      import SystemTools
from mod_memoria      import MemoryTools
from mod_internet     import InternetTools
from mod_dev          import DevTools
from mod_sonidos      import (sonido_inicio, sonido_escuchando,
                               sonido_confirmacion, sonido_error,
                               sonido_apagado, sonido_cancelar)
from mod_recordatorios import RecordatoriosTools
from mod_dashboard     import mostrar_dashboard

_SRC_DIR          = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR         = os.path.dirname(_SRC_DIR)
COMANDOS_TXT_PATH = os.path.join(_ROOT_DIR, "lia_comandos.txt")
LOG_PATH          = os.path.join(_ROOT_DIR, "lia_errores.log")

_SENTINEL = object()

_GRACIAS = [
    "Para eso estoy, con gusto.",
    "De nada, cuando quieras.",
    "Es un placer ayudarte.",
    "Sin problema, aquí estaré.",
    "Claro que sí, para eso soy.",
]

_WAKE_WORDS = {
    "lia", "lía", "lea", "leah", "lear", "liar", "lia,", "lía,",
    "lia:", "lía:", "oye lia", "oye lía", "hey lia", "hey lía",
}

_COMANDOS_CONOCIDOS = [
    "comandos", "inicio", "rutina", "silencio", "habla",
    "pausate", "apagate", "abre", "cierra todo", "pendientes",
    "anota", "apunta", "pomodoro", "recuerda", "clima", "tiempo",
    "busca", "youtube", "recalibra", "sistema", "disco", "bloquea",
    "git status", "git push", "git pull", "ramas", "ayuda",
    "recordatorios", "mis recordatorios", "resumen",
]


def _configurar_logging():
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.WARNING)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(fmt)

    root = logging.getLogger("lia")
    root.setLevel(logging.DEBUG)
    root.addHandler(fh)
    root.addHandler(ch)


logger = logging.getLogger("lia.core")


def _contiene_wake_word(texto: str) -> bool:
    t = texto.lower().strip()
    for ww in _WAKE_WORDS:
        if ww in t:
            return True
    palabras = t.split()
    for p in palabras:
        ratio = difflib.SequenceMatcher(None, p, "lia").ratio()
        if ratio >= 0.80:
            return True
    return False


def _limpiar_wake_word(texto: str) -> str:
    t = texto.lower()
    for ww in sorted(_WAKE_WORDS, key=len, reverse=True):
        t = t.replace(ww, "")
    t = re.sub(r"^[,.\s]+", "", t)
    return t.strip()


def _fuzzy_match_comando(cmd: str) -> str:
    palabras = cmd.split()
    for i in range(len(palabras), 0, -1):
        fragmento = " ".join(palabras[:i])
        matches = difflib.get_close_matches(fragmento, _COMANDOS_CONOCIDOS,
                                            n=1, cutoff=0.72)
        if matches:
            resto = " ".join(palabras[i:])
            return f"{matches[0]} {resto}".strip()
    return cmd


class LiaAssistant:

    MENU_TEXTO = """
+================================================================+
|                    ASISTENTE LIA  v7.0                         |
+================================================================+
|  WAKE WORD: "Lia, ..."  (o aplausos)                          |
|                                                                |
|  APLAUSOS                                                      |
|    1 aplauso   ->  Modo Estudio  (ChatGPT + WhatsApp)          |
|    2 aplausos  ->  Modo Codigo   (VS Code + GitHub + Spotify)  |
|    3 aplausos  ->  Modo Juego    (Discord + TimerResolution)   |
|                                                                |
|  COMANDOS DE VOZ (di "Lia, ...")                               |
|    "inicio"                    -> Rutina del dia + dashboard   |
|    "silencio" / "habla"        -> Activa/desactiva voz         |
|    "pausate"                   -> Pausa                        |
|    "apagate"                   -> Apaga el asistente           |
|    "abre [app]"                -> Abre aplicacion              |
|    "cierra todo"               -> Cierra apps de trabajo       |
|    "pendientes"                -> Lee tus pendientes           |
|    "anota [tarea]"             -> Agrega pendiente             |
|    "tarea X lista"             -> Marca tarea X como hecha     |
|    "pomodoro [N]"              -> Timer de N minutos           |
|    "recuerda [X] el [fecha]"   -> Recordatorio por fecha       |
|    "recuerda [X] en N minutos" -> Recordatorio por minutos     |
|    "recordatorios"             -> Lee tus recordatorios        |
|    "clima"                     -> Dice el clima actual         |
|    "busca [X]"                 -> Busca en Google              |
|    "youtube [X]"               -> Busca en YouTube             |
|    "nota [clave] [texto]"      -> Guarda nota rapida           |
|    "comandos"                  -> Abre este archivo            |
|    "recalibra"                 -> Recalibra el microfono       |
|    "sistema"                   -> CPU y RAM                    |
|    "disco"                     -> Uso del disco                |
|    "bloquea"                   -> Bloquea la PC                |
|    "git status/push/pull"      -> Comandos Git                 |
|    "gracias"                   -> Responde amablemente         |
+================================================================+
"""

    def __init__(self):
        _configurar_logging()
        logger.info("Iniciando Lia v7.0")

        self.is_active       = True
        self._shutdown_flag  = threading.Event()
        self.modo_silencioso = False
        self.lia_hablando    = False

        self._tts_queue  = queue.Queue()
        self._tts_voice_id = None
        self._tts_rate   = 175
        self._tts_thread = threading.Thread(target=self._tts_loop,
                                            daemon=True, name="LiaTTS")
        self._tts_thread.start()
        self._detectar_voz_espanol()

        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.recognizer.pause_threshold          = 1.0
        self.recognizer.non_speaking_duration    = 0.5
        self.recognizer.dynamic_energy_threshold = True

        self.sistema      = SystemTools(self)
        self.memoria      = MemoryTools(self)
        self.internet     = InternetTools(self)
        self.dev          = DevTools(self)
        self.recordatorios = RecordatoriosTools(self)

        self.memoria._shutdown_flag        = self._shutdown_flag
        self.recordatorios._shutdown       = self._shutdown_flag

        self.detector = ClapDetector(on_sequence=self._handle_clap_sequence)

        self.detector.calibrar()
        self._generar_txt_comandos()

        sonido_inicio()
        self.hablar("Hola, aquí estoy.")
        self.mostrar_menu()

        mostrar_dashboard(lia=self, auto_close_ms=20000)

    def _detectar_voz_espanol(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass
        try:
            tmp = pyttsx3.init("sapi5")
            for v in tmp.getProperty("voices"):
                if "spanish" in v.name.lower() or "mexico" in v.name.lower():
                    self._tts_voice_id = v.id
                    break
            tmp.stop()
            del tmp
        except Exception as ex:
            logger.warning("No se pudo detectar voz en español: %s", ex)

    def _tts_loop(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

        while True:
            item = self._tts_queue.get()
            if item is _SENTINEL:
                break
            self.lia_hablando = True
            try:
                self.detector.set_lia_hablando(True)
            except Exception:
                pass
            try:
                engine = pyttsx3.init("sapi5")
                engine.setProperty("rate", self._tts_rate)
                if self._tts_voice_id:
                    engine.setProperty("voice", self._tts_voice_id)
                engine.say(item)
                engine.runAndWait()
                engine.stop()
                del engine
                time.sleep(0.08)
            except Exception as ex:
                logger.error("❌ Error TTS al decir '%s': %s", item[:40], ex)
                print(f"❌ Error TTS: {ex}")
            finally:
                self.lia_hablando = False
                try:
                    self.detector.set_lia_hablando(False)
                except Exception:
                    pass

    def hablar(self, texto: str):
        print(f"🗣️  Lia: {texto}")
        if self.modo_silencioso:
            return
        self._tts_queue.put(texto)

    def registrar_actividad(self, actividad: str):
        self.memoria.registrar_actividad(actividad)

    def mostrar_menu(self):
        print(self.MENU_TEXTO)

    def _generar_txt_comandos(self):
        try:
            with open(COMANDOS_TXT_PATH, "w", encoding="utf-8") as f:
                f.write(self.MENU_TEXTO)
        except Exception as ex:
            logger.error("No se pudo crear lia_comandos.txt: %s", ex)

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
            sonido_confirmacion()
            self.registrar_actividad("Abrió Comandos.txt")
        except Exception as ex:
            logger.error("Error al abrir comandos.txt: %s", ex)
            sonido_error()

    def cerrar_comandos_txt(self):
        import subprocess, platform
        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/f", "/im", "notepad.exe"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except Exception as ex:
            logger.warning("No se pudo cerrar notepad: %s", ex)

    def _handle_clap_sequence(self, count: int):
        logger.debug("Aplausos: %d", count)
        if not self.is_active and count >= 3:
            self.is_active = True
            self.detector.set_active(True)
            sonido_confirmacion()
            self.hablar("Sistemas reactivados.")
            return
        if not self.is_active:
            return
        sonido_confirmacion()
        if count == 1:
            self.sistema.modo_estudio()
        elif count == 2:
            self.sistema.modo_programacion()
        elif count >= 3:
            self.sistema.modo_juego()

    def _parse_command(self, cmd: str):
        if not cmd.strip():
            return

        logger.debug("Comando: '%s'", cmd)

        cmd_fuzzy = _fuzzy_match_comando(cmd)
        if cmd_fuzzy != cmd:
            logger.debug("Fuzzy corregido: '%s' → '%s'", cmd, cmd_fuzzy)
            cmd = cmd_fuzzy

        if "gracias" in cmd:
            self.cerrar_comandos_txt()
            sonido_confirmacion()
            self.hablar(random.choice(_GRACIAS))
            return

        if "comandos" in cmd:
            self.abrir_comandos_txt()
            return

        if any(k in cmd for k in ("inicio", "rutina", "buenos días", "buen día")):
            mostrar_dashboard(lia=self, auto_close_ms=20000)
            self.internet.rutina_inicio()
            return

        if "silencio" in cmd:
            self.modo_silencioso = True
            print("🔇 Modo silencioso activado.")
            sonido_cancelar()
            return

        if "habla" in cmd or "activa voz" in cmd:
            self.modo_silencioso = False
            sonido_confirmacion()
            self.hablar("Voz reactivada.")
            return

        if "pausate" in cmd or cmd.strip() == "pausa":
            self.is_active = False
            self.detector.set_active(False)
            sonido_cancelar()
            self.hablar("Pausada. Da 3 aplausos para volver.")
            return

        if "apagate" in cmd or "apagar" in cmd:
            sonido_apagado()
            time.sleep(0.5)
            self.hablar("Apagando. Hasta luego.")
            self._shutdown_flag.set()
            return

        if "apaga la pc" in cmd or "apaga el pc" in cmd:
            self.sistema.apagar_pc(segundos=60)
            return

        if "cancela apagado" in cmd:
            self.sistema.cancelar_apagado()
            return

        if "cierra todo" in cmd or "cerrar todo" in cmd:
            self.sistema.cerrar_todo()
            return

        if "abre " in cmd or "abrir " in cmd:
            for trigger in ("abre ", "abrir "):
                if trigger in cmd:
                    app = cmd.split(trigger, 1)[-1].strip()
                    if app:
                        sonido_confirmacion()
                        self.sistema.open_application(app)
                    else:
                        sonido_error()
                        self.hablar("¿Qué quieres que abra?")
                    return

        if "pendientes" in cmd and not any(k in cmd for k in ("anota", "tarea")):
            self.memoria.decir_pendientes()
            return

        for verbo in ("anota", "apunta", "agrega pendiente", "agrega"):
            if verbo in cmd:
                texto = cmd.split(verbo, 1)[-1].strip().strip(",.-: ")
                if texto:
                    sonido_confirmacion()
                    self.memoria.agregar_pendiente(texto)
                else:
                    sonido_error()
                    self.hablar("¿Qué quieres que anote?")
                return

        for kw in ("lista", "completada", "hecha", "terminada", "completa"):
            if kw in cmd and "tarea" in cmd:
                tarea = cmd.replace("tarea", "").replace(kw, "").strip().strip(",.-: ")
                self.memoria.completar_tarea(tarea)
                return

        if cmd.startswith("nota "):
            partes = cmd[5:].strip().split(" ", 1)
            if len(partes) == 2:
                sonido_confirmacion()
                self.memoria.guardar_nota(partes[0], partes[1])
            else:
                sonido_error()
                self.hablar("Di: nota [clave] [contenido].")
            return

        if "recuerda nota " in cmd:
            self.memoria.obtener_nota(cmd.split("recuerda nota ", 1)[-1].strip())
            return

        if "pomodoro" in cmd:
            minutos = 25
            for p in cmd.split():
                if p.isdigit():
                    minutos = int(p)
                    break
            sonido_confirmacion()
            self.memoria.iniciar_pomodoro(minutos)
            return

        if any(k in cmd for k in ("recordatorios", "mis recordatorios")):
            self.recordatorios.listar()
            return

        if "completar recordatorio" in cmd or "recordatorio listo" in cmd:
            texto = (cmd.replace("completar recordatorio", "")
                       .replace("recordatorio listo", "")
                       .strip())
            self.recordatorios.completar(texto)
            return

        if "recuerda" in cmd or "recuérdame" in cmd:
            cmd_limpio = cmd.replace("recuérdame", "recuerda")

            if " en " in cmd_limpio and "nota" not in cmd_limpio:
                partes  = cmd_limpio.split(" en ", 1)
                mensaje = partes[0].replace("recuerda", "").strip()
                resto   = partes[1]
                nums    = "".join(c for c in resto if c.isdigit() or c == ".")
                if nums and any(k in resto for k in ("minuto", "hora", "segundo")):
                    try:
                        if "hora" in resto:
                            mins = float(nums) * 60
                        elif "segundo" in resto:
                            mins = float(nums) / 60
                        else:
                            mins = float(nums)
                        sonido_confirmacion()
                        self.memoria.recordar_en(mensaje, mins)
                    except Exception as ex:
                        logger.warning("Error en recordatorio por minutos: %s", ex)
                        sonido_error()
                        self.hablar("No entendí el tiempo.")
                    return

            patrones_fecha = [
                r"\bel\b", r"\bdia\b", r"\bdía\b", r"\bmañana\b",
                r"\bmanana\b", r"\blunes\b", r"\bmartes\b", r"\bmiercoles\b",
                r"\bjueves\b", r"\bviernes\b", r"\bsabado\b", r"\bdomingo\b",
                r"\benero\b", r"\bfebrero\b", r"\bmarzo\b", r"\babril\b",
                r"\bmayo\b", r"\bjunio\b", r"\bjulio\b", r"\bagosto\b",
                r"\bseptiembre\b", r"\boctubre\b", r"\bnoviembre\b", r"\bdiciembre\b",
            ]
            if any(re.search(p, cmd_limpio) for p in patrones_fecha):
                cmd_trabajo = cmd_limpio.replace("recuerda", "").replace("recuérdame", "").strip()
                for kw in ("el día", "el", "para el", "para"):
                    if kw in cmd_trabajo:
                        partes = cmd_trabajo.split(kw, 1)
                        mensaje    = partes[0].strip().strip(",.-: ")
                        texto_fecha = kw + " " + partes[1].strip()
                        if mensaje:
                            sonido_confirmacion()
                            self.recordatorios.agregar(mensaje, texto_fecha)
                        else:
                            self.hablar("¿Qué quieres que te recuerde?")
                        return

                sonido_error()
                self.hablar("Di por ejemplo: recuerda pagar la renta el 30 de abril.")
                return

            sonido_error()
            self.hablar("No entendí el recordatorio. Puedes decir: recuérdame X el 30 de abril, o recuérdame X en 30 minutos.")
            return

        if "clima" in cmd or "tiempo" in cmd:
            self.internet.decir_clima()
            return

        for trigger in ("busca ", "buscar "):
            if trigger in cmd:
                q = cmd.split(trigger, 1)[-1].strip()
                if q:
                    self.internet.buscar_google(q)
                else:
                    sonido_error()
                    self.hablar("¿Qué quieres buscar?")
                return

        if "youtube " in cmd:
            q = cmd.split("youtube ", 1)[-1].strip()
            if q:
                self.internet.buscar_youtube(q)
            else:
                sonido_error()
                self.hablar("¿Qué quieres buscar en YouTube?")
            return

        if "recalibra" in cmd or "calibra" in cmd:
            self.detector.calibrar()
            return

        if any(k in cmd for k in ("sistema", "cpu", "ram")):
            self.sistema.obtener_info_sistema()
            return

        if "disco" in cmd:
            self.sistema.obtener_uso_disco()
            return

        if "bloquea" in cmd or "bloquear" in cmd:
            self.sistema.bloquear_pc()
            return

        if "git status" in cmd or "estado del repo" in cmd:
            self.dev.estado_git()
            return

        if "git push" in cmd:
            self.dev.hacer_push()
            return

        if "git pull" in cmd:
            self.dev.hacer_pull()
            return

        if "ramas" in cmd:
            self.dev.listar_ramas()
            return

        if any(k in cmd for k in ("ayuda", "menú", "menu")):
            self.mostrar_menu()
            self.hablar("Te mostré el menú en pantalla.")
            return

        logger.debug("Comando no reconocido: '%s'", cmd)

    def _listen_loop(self):
        with self.microphone as src:
            self.recognizer.adjust_for_ambient_noise(src, duration=1.0)
            logger.info("Reconocimiento de voz listo.")
            print("✅ Listo para comandos de voz. Di 'Lia, ...' para activarme.\n")

            while not self._shutdown_flag.is_set():
                if self.lia_hablando:
                    time.sleep(0.1)
                    continue

                if not self.is_active:
                    time.sleep(0.4)
                    continue

                try:
                    audio = self.recognizer.listen(
                        src, timeout=None, phrase_time_limit=8
                    )
                    if self.lia_hablando:
                        continue

                    try:
                        texto = self.recognizer.recognize_google(
                            audio, language="es-MX"
                        ).lower()
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError as ex:
                        logger.error("❌ Error de reconocimiento (API): %s", ex)
                        print(f"❌ Error reconocimiento de voz: {ex}")
                        continue

                    print(f"🎤 Escuché: '{texto}'")
                    logger.debug("Reconocido: '%s'", texto)

                    if "gracias" in texto and "lia" not in texto:
                        self.cerrar_comandos_txt()
                        sonido_confirmacion()
                        self.hablar(random.choice(_GRACIAS))
                        continue

                    if _contiene_wake_word(texto):
                        sonido_escuchando()
                        limpio = _limpiar_wake_word(texto)

                        if not limpio:
                            audio2 = self.recognizer.listen(
                                src, timeout=4, phrase_time_limit=8
                            )
                            try:
                                limpio = self.recognizer.recognize_google(
                                    audio2, language="es-MX"
                                ).lower()
                                print(f"🎤 Comando (2da etapa): '{limpio}'")
                            except sr.UnknownValueError:
                                continue
                            except sr.RequestError as ex:
                                logger.error("❌ Error reconocimiento 2da etapa: %s", ex)
                                print(f"❌ Error en segunda escucha: {ex}")
                                continue

                        if limpio:
                            self._parse_command(limpio)

                except sr.WaitTimeoutError:
                    pass
                except Exception as ex:
                    logger.exception("❌ Error inesperado en _listen_loop: %s", ex)
                    print(f"❌ Error en escucha: {ex}")
                    time.sleep(0.5)

    def run(self):
        voz = threading.Thread(target=self._listen_loop,
                               daemon=True, name="LiaVoz")
        voz.start()
        try:
            self.detector.start_loop(shutdown_flag=self._shutdown_flag)
        except KeyboardInterrupt:
            print("\n👋 Lia detenida.")
        finally:
            self._shutdown_flag.set()
            self._tts_queue.put(_SENTINEL)
            self._tts_thread.join(timeout=3)
            logger.info("Lia apagada.")


if __name__ == "__main__":
    print("""
+=======================================+
|       ASISTENTE  LIA  v7.0            |
+=======================================+
""")
    LiaAssistant().run()