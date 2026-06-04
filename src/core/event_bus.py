#!/usr/bin/env python3
"""
event_bus.py — Bus de eventos pub/sub thread-safe.

Desacopla la lógica de la interfaz (Fase 11). En lugar de que cada módulo
conozca a la GUI (`self.lia._gui_window.signal_log.emit(...)`), los módulos
publican eventos y quien quiera reaccionar se suscribe.

Eventos estándar (constantes en `Event`):
    SPEAK     — Lia va a decir algo (payload: texto str)
    ACTIVITY  — se registró una actividad (payload: texto str)
    STATUS    — cambió el estado de Lia (payload: "activa"|"pausada"|"apagada"...)
    INTENT    — se resolvió una intención (payload: dict)
    LISTENING — el reconocedor capturó audio/comando (payload: texto str)

El bus es agnóstico: cualquier string puede ser un tópico. Los callbacks se
ejecutan de forma síncrona en el hilo que publica; los suscriptores que hagan
trabajo pesado deben delegar a su propio hilo (la GUI Qt, por ejemplo, reenvía
a señales Qt que cruzan al hilo de UI).
"""

import logging
import threading
from typing import Any, Callable

logger = logging.getLogger("lia.bus")

Subscriber = Callable[[Any], None]


class Event:
    """Nombres canónicos de eventos. Evita strings mágicos dispersos."""
    SPEAK = "speak"
    ACTIVITY = "activity"
    STATUS = "status"
    INTENT = "intent"
    LISTENING = "listening"
    ERROR = "error"


class EventBus:
    """Bus de publicación/suscripción simple y thread-safe."""

    def __init__(self) -> None:
        self._subs: dict[str, list[Subscriber]] = {}
        self._lock = threading.RLock()

    def subscribe(self, topic: str, callback: Subscriber) -> Callable[[], None]:
        """Suscribe `callback` a `topic`. Devuelve una función para desuscribir."""
        with self._lock:
            self._subs.setdefault(topic, []).append(callback)

        def _unsubscribe() -> None:
            self.unsubscribe(topic, callback)

        return _unsubscribe

    def unsubscribe(self, topic: str, callback: Subscriber) -> None:
        with self._lock:
            handlers = self._subs.get(topic)
            if handlers and callback in handlers:
                handlers.remove(callback)

    def publish(self, topic: str, payload: Any = None) -> None:
        """Publica un evento. Los errores de un suscriptor no afectan a los demás."""
        with self._lock:
            handlers = list(self._subs.get(topic, ()))
        for handler in handlers:
            try:
                handler(payload)
            except Exception as ex:  # un suscriptor roto no debe tumbar al publisher
                logger.warning("Suscriptor de '%s' falló: %s", topic, ex, exc_info=True)
