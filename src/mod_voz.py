#!/usr/bin/env python3
# Motor TTS thread-safe. Resuelve el bug por el que pyttsx3 + SAPI5
# no habla cuando se invoca desde un hilo secundario: ahora hay un
# hilo dedicado al TTS con CoInitialize.

import queue
import threading
import time
import logging

logger = logging.getLogger("lia.voz")

_SENTINEL = object()


class VozEngine:

    def __init__(self, rate=180, on_speak_start=None, on_speak_end=None):
        self._rate       = rate
        self._voice_id   = None
        self._queue      = queue.Queue()
        self._hablando   = False
        self._silencioso = False
        self._on_start   = on_speak_start
        self._on_end     = on_speak_end
        self._lock       = threading.Lock()

        self._voice_id = self._detectar_voz_espanol()

        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="LiaTTS"
        )
        self._thread.start()

    def _detectar_voz_espanol(self):
        try:
            import pyttsx3
            e = pyttsx3.init("sapi5")
            vid = None
            preferidas = ["sabina", "helena", "laura", "mexico", "spanish"]
            voces = e.getProperty("voices")
            for nombre_pref in preferidas:
                for v in voces:
                    if nombre_pref in v.name.lower():
                        vid = v.id
                        break
                if vid:
                    break
            if not vid:
                for v in voces:
                    nombre = (v.name or "").lower()
                    if "espan" in nombre or "spanish" in nombre or "es-" in nombre:
                        vid = v.id
                        break
            e.stop()
            del e
            return vid
        except Exception as ex:
            logger.warning("No se pudo detectar voz: %s", ex)
            return None

    def _loop(self):
        # CRITICO: CoInitialize en el hilo del TTS.
        # Sin esto, pyttsx3 con SAPI5 falla silenciosamente.
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

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
                import pyttsx3
                engine = pyttsx3.init("sapi5")
                engine.setProperty("rate", self._rate)
                if self._voice_id:
                    engine.setProperty("voice", self._voice_id)
                engine.say(texto)
                engine.runAndWait()
                engine.stop()
                del engine
                time.sleep(0.10)
            except Exception as ex:
                logger.error("Error TTS al decir '%s': %s", texto[:40], ex)
                self._fallback_powershell(texto)
            finally:
                with self._lock:
                    self._hablando = False
                if self._on_end:
                    try:
                        self._on_end()
                    except Exception:
                        pass

    def _fallback_powershell(self, texto):
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

    @property
    def hablando(self):
        with self._lock:
            return self._hablando

    @property
    def silencioso(self):
        return self._silencioso

    def set_silencioso(self, estado):
        self._silencioso = estado

    def set_rate(self, rate):
        self._rate = max(80, min(320, int(rate)))

    def decir(self, texto):
        if not texto:
            return
        self._queue.put(str(texto))

    def vaciar(self):
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass

    def detener(self):
        self._queue.put(_SENTINEL)
        self._thread.join(timeout=3)
