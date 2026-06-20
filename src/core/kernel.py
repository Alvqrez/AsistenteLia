#!/usr/bin/env python3
"""
kernel.py — LiaKernel: orquestador delgado (reemplaza al god-object LiaAssistant).

Responsabilidades, deliberadamente acotadas:
  • Ensamblar infraestructura (EventBus, Config, Persona, MemoryStore, Context).
  • Instanciar los servicios `mod_*` ya probados y registrarlos en el contexto.
  • Cablear voz (TTS/STT) y detector de aplausos.
  • Descubrir y registrar las skills en el IntentRouter.
  • Exponer ciclo de vida (pause/resume/shutdown) y el bucle de escucha.

Toda la lógica de "qué hace cada comando" vive en `skills/`; el ruteo, en
`core/router.py`. El kernel ya NO conoce comandos concretos.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import platform
import sys
import threading
import time

import speech_recognition as sr

from core.context import AssistantContext
from core.event_bus import Event, EventBus
from core.registry import CommandRegistry
from core.router import IntentRouter
from core.skill import SkillRegistry

# Servicios legacy reutilizados como capa de implementación.
from mod_audio import ClapDetector
from mod_config import ConfigManager
from mod_contexto import ContextoConversacional
from mod_dev import DevTools
from mod_focus import FocusTools
from mod_internet import InternetTools
from mod_memoria import MemoryTools
from mod_personalidad import Persona
from mod_productividad import ProductividadTools
from mod_recordatorios import RecordatoriosTools
from mod_resumen import ResumenTools
from mod_sistema import SystemTools
from mod_sistema_extra import FileOpsTools
from mod_vida import VidaTools
from mod_voz import VozEngine
import mod_sonidos

from services.command_history import CommandHistory
from services.unrecognized_log import UnrecognizedLog
from services.webhook_server import WebhookServer
from services.desktop.base import NullDesktopService
from services.desktop.windows import WindowsDesktopService
from services.memory_store import MemoryStore
from services.scheduler import PersistentScheduler

logger = logging.getLogger("lia.kernel")

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT_DIR = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(_SRC_DIR)
_DATA_DIR = os.path.join(_ROOT_DIR, "data")
os.makedirs(_DATA_DIR, exist_ok=True)


class ExtendedSystemTools(FileOpsTools, SystemTools):
    """Combina SystemTools con las operaciones de archivo/carpeta (igual que antes)."""
    pass


class LiaKernel:
    def __init__(self, gui_window=None) -> None:
        self.is_active = True
        self._last_sin_conexion_ts = 0.0
        self._active_lock = threading.Lock()
        self._shutdown_flag = threading.Event()
        self._resume_event = threading.Event()
        self._resume_event.set()  # activa al inicio

        # ── Infraestructura ──────────────────────────────────────────────
        self.bus = EventBus()
        self.config = ConfigManager(_ROOT_DIR)
        self.persona = Persona(nombre=self.config.get("usuario", "Leonardo")
                               if self.config.get("usuario") else "Leonardo")
        self.persona.set_modo(self.config.get("tts_mode", "normal"))
        self.memory = MemoryStore(_DATA_DIR)

        self.ctx = AssistantContext(self.bus, self.config, self.persona, self.memory)
        self.ctx.kernel = self

        # ── GUI: la ventana se suscribe al bus para logs/estado (Fase 11) ─
        self._gui_window = gui_window
        self.ctx._gui_window = gui_window
        self._wire_gui(gui_window)

        # ── Voz (TTS) ────────────────────────────────────────────────────
        # Resiliencia: si falla un subsistema de audio, Lia arranca igual en
        # modo degradado (la GUI y los comandos por texto siguen funcionando).
        try:
            self.voz = VozEngine(
                on_speak_start=lambda: self.detector.set_lia_hablando(True)
                               if getattr(self, "detector", None) else None,
                on_speak_end=lambda: self.detector.set_lia_hablando(False)
                             if getattr(self, "detector", None) else None,
            )
        except Exception as ex:
            logger.error("TTS no disponible (%s). Lia funcionará sin voz.", ex)
            self.voz = None
        self.ctx.voz = self.voz

        # ── Reconocimiento de voz (STT) ──────────────────────────────────
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            # Umbral configurable en lia_config.json con "mic_energy_threshold".
            # Con aplausos desactivados, sounddevice no compite por el mic y los
            # niveles pueden ser distintos. 1500 es más permisivo que 3500.
            energy = int(self.config.get("mic_energy_threshold", 1500))
            self.recognizer.energy_threshold = energy
            # dynamic=True: el reconocedor ajusta el umbral automáticamente según
            # el ruido ambiente. Más robusto que un valor fijo cuando se cambia
            # de entorno o se desactiva sounddevice.
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.dynamic_energy_adjustment_damping = 0.10
            # Bajados de 1.2/0.7 para reducir la latencia percibida al final de
            # cada frase. Trade-off: frases con pausas internas largas (pensar
            # en voz alta a media oración) se pueden cortar antes; si molesta
            # en uso real, estos son los primeros valores a revertir.
            self.recognizer.pause_threshold = 0.9
            self.recognizer.non_speaking_duration = 0.5
            logger.info("STT: energy_threshold=%d, dynamic=True", energy)
        except Exception as ex:
            logger.error("Micrófono no disponible (%s). Modo solo-texto (GUI).", ex)
            self.recognizer = None
            self.microphone = None

        # ── Servicios (mod_* legacy, reciben el contexto como parent_lia) ─
        self._build_services()

        # ── Scheduler persistente (arregla recordatorios efímeros) ───────
        self.scheduler = PersistentScheduler(
            _DATA_DIR, on_fire=self._on_timer_fire,
            shutdown_flag=self._shutdown_flag,
        )
        self.ctx.attach_service("scheduler", self.scheduler)
        self.scheduler.start()

        # ── Detector de aplausos ─────────────────────────────────────────
        # Para desactivarlo temporalmente: "clap_enabled": false en lia_config.json
        _clap_on = self.config.get("clap_enabled", True)
        if not _clap_on:
            logger.info("Detector de aplausos DESACTIVADO (clap_enabled=false en config).")
            print("   Aplausos desactivados. Solo control por voz.")
            self.detector = None
        else:
            try:
                self.detector = ClapDetector(on_sequence=self._handle_clap_sequence)
            except Exception as ex:
                logger.error("Detector de aplausos no disponible (%s).", ex)
                self.detector = None
        self.ctx.detector = self.detector

        # ── Router + skills + plugins (sustituye el if/elif) ─────────────
        self.router = IntentRouter(self.ctx)
        self.router.on_unhandled = self._on_unhandled
        self.registry = SkillRegistry()
        self.registry.register_all(self.router, self.ctx, package_name="skills")
        self.registry.register_all(self.router, self.ctx, package_name="plugins")

        # Catálogo consultable de comandos (help dinámico, búsqueda, validación).
        self.commands = CommandRegistry(self.router)
        self.ctx.attach_service("commands", self.commands)

        # Historial de comandos de la sesión (para "repite el último", etc.)
        self.command_history = CommandHistory(self.bus)
        self.ctx.attach_service("command_history", self.command_history)

        # Registro de comandos NO reconocidos: alimenta el aprendizaje de aliases
        # (las frases que más se repiten sin entenderse son candidatas a alias).
        self.unrecognized = UnrecognizedLog(_DATA_DIR)
        self.ctx.attach_service("unrecognized", self.unrecognized)
        problemas = self.commands.validate()
        if problemas:
            # ASCII puro: este print va a la consola, que en Windows puede ser
            # cp1252; un carácter como "⚠" lanzaba UnicodeEncodeError y abortaba
            # el arranque en terminales no reconfiguradas a UTF-8.
            print(f"   [!] Validacion de comandos: {len(problemas)} advertencia(s) "
                  "(detalle en data/lia.log)")

        # ── Servidor webhook (integración con sistemas externos) ──────────
        _webhook_port = int(self.config.get("webhook_port", 7845))
        self.webhook = WebhookServer(self, port=_webhook_port)
        self.webhook.start()

        # ── Feedback sonoro en modo TTS mínimo ────────────────────────────
        self._wire_audio_feedback()

        # ── Arranque ─────────────────────────────────────────────────────
        from skills import _help
        _help.generar_txt_comandos(self.commands)
        self.ctx.say(self.persona.saludo_inicio())
        mod_sonidos.sonido_inicio()

        # Briefing corto proactivo: una vez por día calendario, sin abrir el
        # navegador (eso queda exclusivo de "buenos días" cuando el usuario
        # lo pide explícitamente). Se lanza en un hilo demorado para que el
        # STT tenga tiempo de calibrar adjust_for_ambient_noise sin interferencia
        # del audio TTS del propio saludo (si se ejecutara aquí de forma síncrona,
        # el recognizer calibraría con la voz de Lia como "ruido ambiente" y el
        # umbral de energía quedaría demasiado alto, impidiendo escuchar comandos).
        def _lanzar_briefing():
            try:
                hoy = datetime.date.today().isoformat()
                if self.config.get("ultimo_briefing_fecha") != hoy:
                    self.internet.briefing_corto()
                    self.config.set("ultimo_briefing_fecha", hoy)
            except Exception as ex:
                logger.error("Error en briefing automático: %s", ex)

        t = threading.Timer(3.0, _lanzar_briefing)
        t.daemon = True
        t.start()

    # ── Construcción de servicios ──────────────────────────────────────────
    def _build_services(self) -> None:
        ctx = self.ctx
        self.sistema = ExtendedSystemTools(ctx)
        self.memoria = MemoryTools(ctx)
        self.internet = InternetTools(ctx)
        self.dev = DevTools(ctx)
        self.productividad = ProductividadTools(ctx)
        self.focus = FocusTools(ctx)
        self.resumen = ResumenTools(ctx)
        self.contexto = ContextoConversacional(ctx)
        self.recordatorios = RecordatoriosTools(ctx)
        self.recordatorios._shutdown = self._shutdown_flag
        self.vida = VidaTools(ctx)
        self.memoria._shutdown_flag = self._shutdown_flag
        self.desktop = (WindowsDesktopService() if platform.system() == "Windows"
                        else NullDesktopService())

        for nombre in ("sistema", "memoria", "internet", "dev", "productividad",
                       "focus", "resumen", "contexto", "recordatorios", "vida",
                       "desktop"):
            ctx.attach_service(nombre, getattr(self, nombre))

        # El escritor primario del historial sigue siendo mod_memoria (evita
        # doble escritura con MemoryStore).
        ctx.set_activity_logger(self.memoria.registrar_actividad)

    # ── GUI / EventBus ─────────────────────────────────────────────────────
    def set_gui_window(self, window) -> None:
        """Conecta la ventana después de construirla (resuelve el orden ventana↔kernel)."""
        self._gui_window = window
        self.ctx._gui_window = window
        self._wire_gui(window)

    def _wire_gui(self, gui_window) -> None:
        if gui_window is None:
            return

        def _on_speak(texto):
            try:
                gui_window.signal_log.emit(f"🗣 {texto}")
            except Exception as ex:
                logger.debug("signal_log.emit falló: %s", ex)

        def _on_activity(act):
            try:
                gui_window.signal_log.emit(f"✓ {act}")
            except Exception as ex:
                logger.debug("signal_log.emit falló: %s", ex)

        def _on_status(estado):
            try:
                gui_window.signal_status.emit(estado)
            except Exception as ex:
                logger.debug("signal_status.emit falló: %s", ex)

        self.bus.subscribe(Event.SPEAK, _on_speak)
        self.bus.subscribe(Event.ACTIVITY, _on_activity)
        self.bus.subscribe(Event.STATUS, _on_status)

    # ── Feedback sonoro ───────────────────────────────────────────────────
    # Categorías de acción "muda" en modo mínimo: el éxito se confirma con un
    # beep en vez de una frase larga. Se excluyen categorías informativas
    # (ayuda, control) donde la respuesta hablada YA es el contenido pedido.
    _CATEGORIAS_BEEP_EXITO = {"aplicaciones", "sistema", "desarrollo", "internet"}

    def _wire_audio_feedback(self) -> None:
        def _on_command_executed(payload):
            if self.persona.modo_tts != "minimal":
                return
            categoria = (payload or {}).get("category", "")
            if categoria in self._CATEGORIAS_BEEP_EXITO:
                mod_sonidos.sonido_confirmacion()

        self.bus.subscribe(Event.COMMAND_EXECUTED, _on_command_executed)

    # ── Fallback de intención no reconocida ───────────────────────────────
    def _on_unhandled(self, cmd_l: str) -> None:
        # Persistir antes de responder: así Lia "aprende" qué frases falla y
        # puede sugerir aliases nuevos ("qué no entendiste").
        try:
            self.unrecognized.record(cmd_l)
        except Exception as ex:
            logger.debug("No se pudo registrar comando no reconocido: %s", ex)
        mod_sonidos.sonido_error()
        self.ctx.say(self.persona.no_entendi())

    # ── Scheduler ──────────────────────────────────────────────────────────
    def _on_timer_fire(self, timer: dict) -> None:
        msg = timer.get("mensaje", "")
        self.ctx.say(self.persona.recordatorio_disparado(msg))
        try:
            self.sistema.notificar("Lia – Recordatorio", msg)
        except Exception:
            pass
        try:
            mod_sonidos.sonido_confirmacion()
        except Exception:
            pass
        self.ctx.registrar_actividad(f"Recordatorio disparado: {msg}")

    # ── API pública usada por skills y GUI ─────────────────────────────────
    def handle_text(self, raw: str) -> bool:
        """Punto de entrada de un comando ya limpio. Lo usa el bucle STT y la GUI."""
        return self.router.handle_text(raw)

    # Compat: el bridge web llamaba lia._parse_command(...).
    def _parse_command(self, cmd: str) -> None:
        self.handle_text(cmd)

    # ── Ciclo de vida ──────────────────────────────────────────────────────
    def pause(self) -> None:
        with self._active_lock:
            self.is_active = False
        self._resume_event.clear()
        # Desactiva el análisis de audio del detector; el stream de sounddevice
        # sigue abierto pero el callback sale inmediatamente sin hacer FFT.
        # Reactivación exclusivamente via tray o voz (cuando se reanude).
        if self.detector is not None:
            self.detector.set_active(False)
        self.ctx.set_status("pausada")

    def resume(self) -> bool:
        """Reactiva. Devuelve True si estaba en pausa."""
        with self._active_lock:
            estaba_en_pausa = not self.is_active
            self.is_active = True
        if self.detector is not None:
            self.detector.set_active(True)
        self._resume_event.set()
        if estaba_en_pausa:
            self.ctx.set_status("activa")
        return estaba_en_pausa

    def request_shutdown(self) -> None:
        self._shutdown_flag.set()
        self.ctx.set_status("apagada")

    def active(self) -> bool:
        with self._active_lock:
            return self.is_active

    # ── Aplausos ───────────────────────────────────────────────────────────
    def _handle_clap_sequence(self, count: int) -> None:
        modos_path = os.path.join(_DATA_DIR, "lia_modos.json")
        modos = []
        try:
            if os.path.exists(modos_path):
                with open(modos_path, "r", encoding="utf-8") as f:
                    modos = json.load(f).get("modos", [])
        except Exception:
            pass

        with self._active_lock:
            if not self.is_active and count >= 3:
                self.is_active = True
                reactivar = True
            else:
                reactivar = False
            activo = self.is_active

        if reactivar:
            self.detector.set_active(True)
            self.ctx.say(self.persona.reactivacion())
            self.ctx.set_status("activa")
            return

        if not activo:
            return

        modo = next((m for m in modos if m.get("aplausos") == count), None)
        accion = modo.get("accion", "") if modo else ""

        if accion == "modo_estudio" or count == 1:
            self.sistema.modo_estudio()
        elif accion == "modo_programacion" or count == 2:
            self.sistema.modo_programacion()
        elif count >= 3:
            self.sistema.modo_juego()

    # ── Bucle de escucha (STT) ─────────────────────────────────────────────
    def _listen_loop(self) -> None:
        if self.microphone is None or self.recognizer is None:
            logger.warning("Sin micrófono: el bucle de voz no arranca (usa la GUI por texto).")
            return
        with self.microphone as src:
            self.recognizer.adjust_for_ambient_noise(src, duration=2.0)
            print(f"   [STT] Umbral de energía: {self.recognizer.energy_threshold:.0f}  (dynamic=ON)")
            print("   [STT] Escuchando... di 'Lia' seguido de tu comando")

            while not self._shutdown_flag.is_set():

                if not self.active():
                    # En pausa: dormir sin capturar audio. El bucle despierta
                    # cuando resume() dispara _resume_event o cada 60s para
                    # re-chequear el flag de shutdown.
                    self._resume_event.wait(timeout=60)
                    continue

                try:
                    audio = self.recognizer.listen(src, timeout=None,
                                                   phrase_time_limit=10)
                    # Suprimir clap detector INMEDIATAMENTE al capturar audio,
                    # antes del reconocimiento. Evita que la "L" plosiva de "Lia"
                    # llegue al detector mientras el API procesa la respuesta.
                    if self.detector is not None:
                        self.detector.notificar_voz_detectada(duracion_supresion=2.0)

                    cmd = self.recognizer.recognize_google(audio, language="es-MX").lower()
                    print(f"[STT] Escuché: '{cmd}'")
                    self.bus.publish(Event.LISTENING, cmd)

                    # Wake word: Google a veces transcribe "Lia" como "Leah",
                    # "Lea" u otras variantes fonéticas en es-MX. Las aceptamos
                    # todas para no perder comandos.
                    _WW = ("lia", "lía", "leah", "lea")
                    if cmd.strip() in _WW:
                        self.ctx.say(self.persona.saludo_corto())
                        continue

                    # Si hay acción pendiente, cualquier respuesta la completa.
                    if self.ctx.has_pending():
                        limpio = self._limpiar(cmd)
                        if limpio:
                            self.handle_text(limpio)
                        continue

                    # Palabra de activación obligatoria.
                    if not any(w in cmd for w in _WW):
                        continue

                    mod_sonidos.sonido_escuchando()
                    limpio = self._limpiar(cmd)
                    if limpio:
                        self.memory.remember_short("user", limpio)
                        if hasattr(self, "contexto"):
                            self.contexto.registrar_comando(limpio)
                        self.handle_text(limpio)

                except sr.UnknownValueError:
                    pass
                except sr.RequestError as ex:
                    # Si no avisamos, el usuario percibe esto como "Lia no
                    # escucha": el microfono SI capturo el audio, pero la API
                    # de reconocimiento (red) fallo. Throttle de 15s para no
                    # repetir el aviso si varios intentos fallan en cadena
                    # durante un corte de conexion sostenido.
                    print(f"Error reconocimiento: {ex}")
                    logger.warning("STT RequestError (red): %s", ex)
                    ahora = time.time()
                    if ahora - self._last_sin_conexion_ts > 15:
                        self._last_sin_conexion_ts = ahora
                        mod_sonidos.sonido_error()
                        self.ctx.say(self.persona.sin_conexion())
                except Exception as ex:
                    logger.warning("Error inesperado en listen_loop: %s", ex, exc_info=True)
                    time.sleep(0.5)

    @staticmethod
    def _limpiar(cmd: str) -> str:
        return (cmd.replace("lía,", "").replace("lia,", "")
                .replace("leah,", "").replace("lea,", "")
                .replace("lía", "").replace("lia", "")
                .replace("leah", "").replace("lea ", "")
                .strip().strip(",. "))

    def run(self) -> None:
        threading.Thread(target=self._listen_loop, daemon=True, name="LiaSTT").start()
        try:
            if self.detector is not None:
                self.detector.start_loop(shutdown_flag=self._shutdown_flag)
            else:
                # Sin detector de aplausos: el hilo se mantiene vivo hasta el apagado
                # (la GUI sigue operando por texto).
                self._shutdown_flag.wait()
        except KeyboardInterrupt:
            print("\nLia detenida.")
        finally:
            self._shutdown_flag.set()
