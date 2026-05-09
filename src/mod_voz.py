#!/usr/bin/env python3
# mod_voz.py — Motor TTS con Microsoft Edge TTS (voz neural humana).
#
# Requiere:  pip install edge-tts pygame
#
# Voces en español incluidas:
#   es-MX-DaliaNeural   — Mexicana, femenina  ← default
#   es-MX-JorgeNeural   — Mexicano, masculino
#   es-ES-ElviraNeural  — Española, femenina
#   es-ES-AlvaroNeural  — Español, masculino
#   es-AR-ElenaNeural   — Argentina, femenina
#
# Arquitectura:
#   • Un hilo TTS dedicado procesa textos de la cola.
#   • edge_tts genera un MP3 en archivo temporal.
#   • pygame.mixer reproduce el MP3 de forma bloqueante.
#   • Fallback a pyttsx3/SAPI5 si edge-tts no está disponible.

import asyncio
import queue
import threading
import time
import tempfile
import os
import platform
import logging

logger = logging.getLogger("lia.voz")

_SENTINEL = object()

# ── Catálogo de voces disponibles ────────────────────────────────────────────
VOCES = {
    "dalia":   "es-MX-DaliaNeural",    # default — mexicana, clara y natural
    "jorge":   "es-MX-JorgeNeural",    # mexicano masculino
    "elvira":  "es-ES-ElviraNeural",   # española femenina
    "alvaro":  "es-ES-AlvaroNeural",   # español masculino
    "elena":   "es-AR-ElenaNeural",    # argentina femenina
}


def _check_module(nombre: str) -> bool:
    import importlib
    try:
        importlib.import_module(nombre)
        return True
    except ImportError:
        return False


class VozEngine:

    def __init__(self,
                 voice: str = "es-MX-DaliaNeural",
                 rate:  str = "+0%",
                 volume: str = "+0%",
                 on_speak_start=None,
                 on_speak_end=None):
        """
        voice  — identificador de voz Edge TTS (o alias del catálogo VOCES).
        rate   — velocidad relativa: "-10%" más lento, "+10%" más rápido.
        volume — volumen relativo: "-20%" más bajo, "+20%" más alto.
        """
        # Resolver alias
        self._voice  = VOCES.get(voice.lower(), voice)
        self._rate   = rate
        self._volume = volume
        self._queue  = queue.Queue()

        self._hablando   = False
        self._silencioso = False
        self._lock       = threading.Lock()

        self._on_start = on_speak_start
        self._on_end   = on_speak_end

        # Detectar disponibilidad
        self._edge_ok  = _check_module("edge_tts")
        self._pygame_ok = _check_module("pygame")

        if not self._edge_ok:
            logger.warning(
                "edge-tts no instalado. Instala con:  pip install edge-tts pygame\n"
                "Usando fallback pyttsx3 mientras tanto."
            )
        if self._edge_ok and not self._pygame_ok:
            logger.warning(
                "pygame no instalado — la reproducción puede fallar.\n"
                "Instala con:  pip install pygame"
            )

        # Inicializar pygame.mixer una sola vez aquí (hilo principal)
        if self._pygame_ok:
            self._init_pygame()

        self._thread = threading.Thread(target=self._loop, daemon=True, name="LiaTTS")
        self._thread.start()

    # ── Pygame ────────────────────────────────────────────────────────────────

    def _init_pygame(self):
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=512)
                logger.debug("pygame.mixer inicializado.")
        except Exception as ex:
            logger.warning("No se pudo inicializar pygame.mixer: %s", ex)
            self._pygame_ok = False

    def _reproducir_mp3(self, filepath: str):
        """Reproduce un MP3 de forma bloqueante. Prueba pygame → PowerShell."""
        # Intento 1: pygame
        if self._pygame_ok:
            try:
                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=512)
                pygame.mixer.music.load(filepath)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.04)
                pygame.mixer.music.stop()
                return
            except Exception as ex:
                logger.debug("pygame falló al reproducir: %s", ex)

        # Intento 2: playsound
        try:
            from playsound import playsound
            playsound(filepath, block=True)
            return
        except Exception as ex:
            logger.debug("playsound falló: %s", ex)

        # Intento 3: PowerShell MediaPlayer (sólo Windows)
        if platform.system() == "Windows":
            try:
                import subprocess, urllib.request
                # Convertir ruta a URI correcta
                uri = filepath.replace("\\", "/")
                if not uri.startswith("/"):
                    uri = "/" + uri
                script = (
                    "Add-Type -AssemblyName presentationCore;"
                    "$mp = New-Object System.Windows.Media.MediaPlayer;"
                    f"$mp.Open([uri]::new('file://{uri}'));"
                    "$mp.Play();"
                    "Start-Sleep -Seconds 30;"
                    "$mp.Stop()"
                )
                subprocess.run(
                    ["powershell", "-WindowStyle", "Hidden", "-Command", script],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=35,
                )
                return
            except Exception as ex:
                logger.debug("PowerShell MediaPlayer falló: %s", ex)

        logger.error("No se encontró ningún reproductor de audio disponible.")

    # ── Loop TTS ──────────────────────────────────────────────────────────────

    def _loop(self):
        # Crear event loop de asyncio dedicado a este hilo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while True:
            texto = self._queue.get()
            if texto is _SENTINEL:
                break
            if self._silencioso:
                continue

            with self._lock:
                self._hablando = True
            if self._on_start:
                try:
                    self._on_start()
                except Exception:
                    pass

            try:
                if self._edge_ok:
                    loop.run_until_complete(self._hablar_edge(texto))
                else:
                    self._fallback_pyttsx3(texto)
            except Exception as ex:
                logger.error("Error TTS: %s | texto='%s'", ex, texto[:40])
                try:
                    self._fallback_pyttsx3(texto)
                except Exception:
                    pass
            finally:
                with self._lock:
                    self._hablando = False
                if self._on_end:
                    try:
                        self._on_end()
                    except Exception:
                        pass

        loop.close()

    async def _hablar_edge(self, texto: str):
        import edge_tts

        # Archivo temporal (se borra al terminar)
        fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)

        try:
            communicate = edge_tts.Communicate(
                texto,
                self._voice,
                rate=self._rate,
                volume=self._volume,
            )
            await communicate.save(tmp_path)
            self._reproducir_mp3(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    # ── Fallback pyttsx3 ──────────────────────────────────────────────────────

    def _fallback_pyttsx3(self, texto: str):
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass
        try:
            import pyttsx3
            engine = pyttsx3.init("sapi5")
            engine.setProperty("rate", 175)
            # Intentar encontrar voz en español
            for v in engine.getProperty("voices"):
                nombre = (v.name or "").lower()
                if any(s in nombre for s in ("sabina", "helena", "laura", "mexico", "spanish", "espanol")):
                    engine.setProperty("voice", v.id)
                    break
            engine.say(texto)
            engine.runAndWait()
            engine.stop()
            del engine
        except Exception as ex:
            logger.error("Fallback pyttsx3 falló: %s", ex)
            self._fallback_powershell(texto)

    def _fallback_powershell(self, texto: str):
        try:
            import subprocess
            t = texto.replace("'", "''")
            script = (
                "Add-Type -AssemblyName System.Speech;"
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                f"$s.Rate = 1; $s.Speak('{t}')"
            )
            subprocess.run(
                ["powershell", "-WindowStyle", "Hidden", "-Command", script],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=30,
            )
        except Exception:
            pass

    # ── API pública ───────────────────────────────────────────────────────────

    @property
    def hablando(self) -> bool:
        with self._lock:
            return self._hablando

    @property
    def silencioso(self) -> bool:
        return self._silencioso

    def set_silencioso(self, estado: bool):
        self._silencioso = estado

    def set_voice(self, voice: str):
        """Cambia la voz en tiempo de ejecución."""
        self._voice = VOCES.get(voice.lower(), voice)
        logger.info("Voz cambiada a: %s", self._voice)

    def set_rate(self, rate: str):
        """Ejemplo: '+10%' para hablar más rápido, '-10%' para más lento."""
        self._rate = rate

    def decir(self, texto: str):
        if not texto:
            return
        self._queue.put(str(texto))

    def vaciar(self):
        """Vacía la cola de TTS pendiente."""
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass

    def detener(self):
        self._queue.put(_SENTINEL)
        self._thread.join(timeout=3)
