#!/usr/bin/env python3

import queue
import threading
import time
import logging

logger = logging.getLogger("lia.voz")

_SENTINEL = object()


class VozEngine:
    def __init__(self, rate: int = 175):
        self._rate        = rate
        self._voice_id    = None
        self._queue       = queue.Queue()
        self._hablando    = False
        self._thread      = threading.Thread(target=self._loop, daemon=True, name="LiaTTS")
        self._thread.start()
        self._voice_id    = self._detectar_voz_espanol()

    def _detectar_voz_espanol(self) -> str | None:
        try:
            import pyttsx3
            e = pyttsx3.init("sapi5")
            vid = None
            for v in e.getProperty("voices"):
                if "spanish" in v.name.lower() or "mexico" in v.name.lower():
                    vid = v.id
                    break
            e.stop()
            del e
            return vid
        except Exception as ex:
            logger.warning("No se pudo detectar voz en español: %s", ex)
            return None

    def _loop(self):
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

        while True:
            texto = self._queue.get()
            if texto is _SENTINEL:
                break
            self._hablando = True
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
                time.sleep(0.08)
            except Exception as ex:
                logger.error("Error TTS al decir '%s': %s", texto[:40], ex)
            finally:
                self._hablando = False

    @property
    def hablando(self) -> bool:
        return self._hablando

    def decir(self, texto: str):
        self._queue.put(texto)

    def detener(self):
        self._queue.put(_SENTINEL)
        self._thread.join(timeout=3)