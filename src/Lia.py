#!/usr/bin/env python3
"""
Lia.py  –  Cerebro del asistente
Responsabilidades ÚNICAS de este archivo:
  · Inicializar todos los módulos y conectarlos entre sí
  · Gestionar TTS (hablar)
  · Escuchar comandos de voz y parsearlos (_parse_command)
  · Arrancar el loop de detección de aplausos
  · Exponer registrar_actividad() para que los módulos lo usen

Todo lo demás vive en los módulos:
  mod_audio   → análisis de señal + detección de aplausos
  mod_sistema → apps, URLs, modos de trabajo, sistema operativo
  mod_memoria → pendientes, notas, historial, pomodoro, recordatorios
  mod_internet→ clima, rutina de inicio, búsquedas web
  mod_dev     → git, herramientas de programación
"""

import os
import sys
import threading
import time

import pyttsx3
import speech_recognition as sr

# ── Módulos de Lia ───────────────────────────────────────────
from mod_audio   import ClapDetector
from mod_sistema import SystemTools
from mod_memoria import MemoryTools
from mod_internet import InternetTools
from mod_dev     import DevTools

# ── Rutas ────────────────────────────────────────────────────
_SRC_DIR          = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR         = os.path.dirname(_SRC_DIR)
COMANDOS_TXT_PATH = os.path.join(_ROOT_DIR, "lia_comandos.txt")


class LiaAssistant:

    # ════════════════════════════════════════════════════════
    #  INICIALIZACIÓN
    # ════════════════════════════════════════════════════════

    def __init__(self):
        self.is_active       = True
        self._shutdown_flag  = threading.Event()

        # ── TTS ───────────────────────────────────────────────
        self.lia_hablando    = False
        self.modo_silencioso = False
        self._tts_lock       = threading.Lock()
        self._init_tts()

        # ── Reconocimiento de voz ─────────────────────────────
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        self.recognizer.pause_threshold = 1.1  # Espera un poco más entre palabras
        self.recognizer.non_speaking_duration = 0.6  # Tiempo de silencio antes de procesar
        self.recognizer.dynamic_energy_threshold = True

        # ── Módulos (se pasan 'self' como parent_lia) ─────────
        self.sistema  = SystemTools(self)
        self.memoria  = MemoryTools(self)
        self.internet = InternetTools(self)
        self.dev      = DevTools(self)

        # Inyectar shutdown_flag en mod_memoria para hilos de pomodoro
        self.memoria._shutdown_flag = self._shutdown_flag

        # ── Detector de aplausos ──────────────────────────────
        self.detector = ClapDetector(
            on_sequence=self._handle_clap_sequence
        )

        # ── Arranque ─────────────────────────────────────────
        self.detector.calibrar()
        self._generar_txt_comandos()
        self.hablar("Hola, aquí estoy.")
        self.mostrar_menu()

    # ════════════════════════════════════════════════════════
    #  TTS
    # ════════════════════════════════════════════════════════

    def _init_tts(self):
        """Inicializa el engine TTS una sola vez para toda la sesión."""
        try:
            self.tts_engine = pyttsx3.init('sapi5')
            self.tts_engine.setProperty('rate', 175)
            for v in self.tts_engine.getProperty('voices'):
                if "spanish" in v.name.lower() or "mexico" in v.name.lower():
                    self.tts_engine.setProperty('voice', v.id)
                    break
        except Exception as e:
            print(f"⚠️  Error al iniciar TTS: {e}")
            self.tts_engine = None

    def hablar(self, texto: str):
        """Reproduce texto en voz. Respeta modo silencioso."""
        print(f"🗣️  Lia: {texto}")
        if self.modo_silencioso or self.tts_engine is None:
            return
        try:
            self.lia_hablando = True
            self.detector.set_lia_hablando(True)   # suprime falsos aplausos
            with self._tts_lock:
                self.tts_engine.say(texto)
                self.tts_engine.runAndWait()
            time.sleep(0.15)
        except Exception as e:
            print(f"❌ Error de voz: {e}")
            self._init_tts()
        finally:
            self.lia_hablando = False
            self.detector.set_lia_hablando(False)

    # ════════════════════════════════════════════════════════
    #  HISTORIAL  (delegado a mod_memoria)
    # ════════════════════════════════════════════════════════

    def registrar_actividad(self, actividad: str):
        """Punto único de registro; todos los módulos lo llaman aquí."""
        self.memoria.registrar_actividad(actividad)

    # ════════════════════════════════════════════════════════
    #  MENÚ Y COMANDOS.TXT
    # ════════════════════════════════════════════════════════

    MENU_TEXTO = """
+==============================================================+
|                   ASISTENTE LIA  v3.0                        |
+==============================================================+
|  APLAUSOS                                                    |
|    1 aplauso   ->  Modo Estudio  (ChatGPT + WhatsApp)        |
|    2 aplausos  ->  Modo Codigo   (VS Code + GitHub + Spotify)|
|    3 aplausos  ->  Modo Juego    (Discord + TimerResolution) |
|                                                              |
|  COMANDOS DE VOZ  (di "Lia, ...")                            |
|  -- Rutina --                                                |
|    "Lia, inicio"             -> Rutina de inicio del dia     |
|  -- Voz --                                                   |
|    "Lia, silencio"           -> Solo texto, sin voz          |
|    "Lia, habla"              -> Reactiva la voz              |
|  -- Control --                                               |
|    "Lia, pausate"            -> Pausa (3 aplausos p/volver)  |
|    "Lia, apagate"            -> Apaga el asistente           |
|  -- Aplicaciones --                                          |
|    "Lia, abre [app]"         -> Abre cualquier aplicacion    |
|    "Lia, cierra todo"        -> Cierra apps de trabajo       |
|  -- Pendientes --                                            |
|    "Lia, anota [tarea]"      -> Agrega pendiente             |
|    "Lia, pendientes"         -> Lee tus pendientes           |
|    "Lia, tarea X lista"      -> Marca tarea X como hecha     |
|  -- Productividad --                                         |
|    "Lia, pomodoro"           -> Timer 25 min                 |
|    "Lia, pomodoro de 45"     -> Timer con minutos custom     |
|    "Lia, recuerda X en N minutos" -> Recordatorio            |
|    "Lia, clima"              -> Dice el clima actual         |
|  -- Sistema --                                               |
|    "Lia, comandos"           -> Abre este archivo            |
|    "Lia, recalibra"          -> Recalibra el microfono       |
|    "Lia, sistema"            -> Info de CPU y RAM            |
|    "Lia, disco"              -> Uso del disco                |
|    "Lia, bloquea"            -> Bloquea la PC                |
|  -- Internet --                                              |
|    "Lia, busca [X]"          -> Busca en Google              |
|    "Lia, youtube [X]"        -> Busca en YouTube             |
|  -- Notas rapidas --                                         |
|    "Lia, nota [clave] [txt]" -> Guarda nota rapida           |
|    "gracias"                 -> Cierra el archivo de comandos|
+==============================================================+
"""

    def mostrar_menu(self):
        print(self.MENU_TEXTO)

    def _generar_txt_comandos(self):
        """Crea o actualiza el archivo lia_comandos.txt."""
        try:
            with open(COMANDOS_TXT_PATH, "w", encoding="utf-8") as f:
                f.write(self.MENU_TEXTO)
        except Exception as e:
            print(f"⚠️  No se pudo crear lia_comandos.txt: {e}")

    def abrir_comandos_txt(self):
        """Abre lia_comandos.txt con el Bloc de notas."""
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
        except Exception as e:
            print(f"❌ Error al abrir comandos: {e}")

    def cerrar_comandos_txt(self):
        """Cierra el Bloc de notas (Windows)."""
        import subprocess, platform
        try:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/f", "/im", "notepad.exe"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    # ════════════════════════════════════════════════════════
    #  CALLBACK DE APLAUSOS
    # ════════════════════════════════════════════════════════

    def _handle_clap_sequence(self, count: int):
        """
        ClapDetector llama aquí cuando detecta una secuencia completa.
        count = número de aplausos detectados.
        """
        if not self.is_active and count >= 3:
            self.is_active = True
            self.detector.set_active(True)
            self.hablar("Sistemas reactivados.")
            return

        if not self.is_active:
            return

        if count == 1:
            self.sistema.modo_estudio()
        elif count == 2:
            self.sistema.modo_programacion()
        elif count >= 3:
            self.sistema.modo_juego()

    # ════════════════════════════════════════════════════════
    #  PARSER DE COMANDOS DE VOZ
    # ════════════════════════════════════════════════════════

    def _parse_command(self, cmd: str):
        """
        Recibe el comando de voz ya limpio (sin 'lia', en minúsculas).
        Delega a los módulos correspondientes.
        """

        # ── Comandos.txt ──────────────────────────────────────
        if "comandos" in cmd:
            self.abrir_comandos_txt()
            return
        if "gracias" in cmd:
            self.cerrar_comandos_txt()
            return

        # ── Rutina de inicio ──────────────────────────────────
        if any(k in cmd for k in ("inicio", "rutina", "buenos días", "buen día")):
            self.internet.rutina_inicio()
            return

        # ── Voz ───────────────────────────────────────────────
        if "silencio" in cmd:
            self.modo_silencioso = True
            print("🔇 Modo silencioso activado.")
            return
        if "habla" in cmd or "activa voz" in cmd:
            self.modo_silencioso = False
            self.hablar("Voz reactivada.")
            return

        # ── Control ───────────────────────────────────────────
        if "pausate" in cmd or "pausa" in cmd:
            self.is_active = False
            self.detector.set_active(False)
            self.hablar("Pausada. 3 aplausos para volver.")
            return
        if "apagate" in cmd or "apagar" in cmd:
            self.hablar("Apagando. Hasta luego.")
            self._shutdown_flag.set()
            return

        # ── Aplicaciones ─────────────────────────────────────
        if "abre " in cmd:
            app = cmd.split("abre ", 1)[-1].strip()
            self.sistema.open_application(app)
            return
        if "cierra todo" in cmd or "cerrar todo" in cmd:
            self.sistema.cerrar_todo()
            return

        # ── Pendientes ────────────────────────────────────────
        if "pendientes" in cmd and not any(k in cmd for k in ("anota", "tarea")):
            self.memoria.decir_pendientes()
            return

        for verbo in ("anota", "apunta", "agrega pendiente", "agrega"):
            if verbo in cmd:
                texto = cmd.split(verbo, 1)[-1].strip().strip(",.-: ")
                if texto:
                    self.memoria.agregar_pendiente(texto)
                else:
                    self.hablar("¿Qué quieres que anote?")
                return

        for kw_fin in ("lista", "completada", "hecha", "terminada", "completa"):
            if kw_fin in cmd and "tarea" in cmd:
                tarea = (cmd.replace("tarea", "")
                            .replace(kw_fin, "")
                            .strip().strip(",.-: "))
                self.memoria.completar_tarea(tarea)
                return

        # ── Notas rápidas ─────────────────────────────────────
        if cmd.startswith("nota "):
            partes = cmd[5:].strip().split(" ", 1)
            if len(partes) == 2:
                self.memoria.guardar_nota(partes[0], partes[1])
            else:
                self.hablar("Di: nota [clave] [contenido].")
            return
        if cmd.startswith("recuerda nota "):
            clave = cmd.replace("recuerda nota", "").strip()
            self.memoria.obtener_nota(clave)
            return

        # ── Pomodoro ─────────────────────────────────────────
        if "pomodoro" in cmd:
            minutos = 25
            for p in cmd.split():
                if p.isdigit():
                    minutos = int(p)
                    break
            self.memoria.iniciar_pomodoro(minutos)
            return

        # ── Recordatorio ─────────────────────────────────────
        if "recuerda" in cmd and " en " in cmd:
            try:
                partes  = cmd.split(" en ", 1)
                mensaje = partes[0].replace("recuerda", "").strip()
                resto   = partes[1]
                mins    = float(
                    ''.join(c for c in resto if c.isdigit() or c == '.') or '5'
                )
                self.memoria.recordar_en(mensaje, mins)
            except Exception:
                self.hablar("No entendí el recordatorio.")
            return

        # ── Clima ─────────────────────────────────────────────
        if "clima" in cmd or "tiempo" in cmd:
            self.internet.decir_clima()
            return

        # ── Búsquedas ─────────────────────────────────────────
        if "busca " in cmd or "buscar " in cmd:
            consulta = (cmd.replace("busca", "")
                           .replace("buscar", "")
                           .strip())
            self.internet.buscar_google(consulta)
            return
        if "youtube " in cmd:
            consulta = cmd.split("youtube ", 1)[-1].strip()
            self.internet.buscar_youtube(consulta)
            return

        # ── Sistema ───────────────────────────────────────────
        if "recalibra" in cmd or "calibra" in cmd:
            self.detector.calibrar()
            return
        if "sistema" in cmd or "cpu" in cmd or "ram" in cmd:
            self.sistema.obtener_info_sistema()
            return
        if "disco" in cmd:
            self.sistema.obtener_uso_disco()
            return
        if "bloquea" in cmd or "bloquear" in cmd:
            self.sistema.bloquear_pc()
            return
        if "apaga la pc" in cmd or "apaga el pc" in cmd:
            self.sistema.apagar_pc(segundos=60)
            return
        if "cancela apagado" in cmd:
            self.sistema.cancelar_apagado()
            return

        # ── Dev ───────────────────────────────────────────────
        if "git status" in cmd or "estado del repo" in cmd:
            self.dev.estado_git()
            return
        if "git push" in cmd:
            self.dev.hacer_push()
            return
        if "git pull" in cmd:
            self.dev.hacer_pull()
            return
        if "ramas" in cmd or "ramas git" in cmd:
            self.dev.listar_ramas()
            return

        # ── Ayuda ─────────────────────────────────────────────
        if "ayuda" in cmd or "menú" in cmd or "menu" in cmd:
            self.mostrar_menu()
            self.hablar("Te mostré el menú en pantalla.")
            return

    # ════════════════════════════════════════════════════════
    #  ESCUCHA DE VOZ
    # ════════════════════════════════════════════════════════

    def _listen_loop(self):
        with self.microphone as src:
            # Calibración inicial más corta para no bloquear el inicio
            self.recognizer.adjust_for_ambient_noise(src, duration=1.0)

            while not self._shutdown_flag.is_set():
                if not self.is_active:
                    time.sleep(0.4)
                    continue
                try:
                    # Aumentamos phrase_time_limit a 8 para frases largas
                    audio = self.recognizer.listen(
                        src, timeout=None, phrase_time_limit=8
                    )
                    cmd = self.recognizer.recognize_google(
                        audio, language="es-MX"
                    ).lower()

                    if "gracias" in cmd:
                        self.cerrar_comandos_txt()
                        continue

                    print(f"🎤 Escuché: '{cmd}'")

                    # Si solo detectó "Lia", ignoramos para no procesar comandos vacíos
                    if cmd.strip() in ["lia", "lía"]:
                        continue

                    if "lia" in cmd or "lía" in cmd:
                        # Limpieza mejorada
                        limpio = cmd.replace("lía", "").replace("lia", "").strip(",. ")
                        if limpio:
                            self._parse_command(limpio)

                except sr.UnknownValueError:
                    pass
                except sr.RequestError as e:
                    print(f"⚠️  Reconocimiento: {e}")
                except Exception:
                    time.sleep(0.5)

    # ════════════════════════════════════════════════════════
    #  ARRANQUE
    # ════════════════════════════════════════════════════════

    def run(self):
        """Inicia el hilo de voz y el loop de aplausos (bloqueante)."""
        voz = threading.Thread(target=self._listen_loop, daemon=True)
        voz.start()
        try:
            self.detector.start_loop(shutdown_flag=self._shutdown_flag)
        except KeyboardInterrupt:
            print("\n👋 Lia detenida.")
        finally:
            self._shutdown_flag.set()


# ── Punto de entrada ─────────────────────────────────────────
if __name__ == "__main__":
    print("""
+=======================================+
|       ASISTENTE  LIA  v3.0            |
+=======================================+
""")
    LiaAssistant().run()