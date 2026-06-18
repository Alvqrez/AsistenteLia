#!/usr/bin/env python3
"""
context.py — AssistantContext: la fachada que ven las skills.

Resuelve la violación de DIP del diseño anterior. Antes cada módulo recibía el
god-object `LiaAssistant` completo y dependía de su implementación concreta.
Ahora las skills (y, por compatibilidad, los módulos `mod_*` existentes)
dependen de esta fachada estable.

Doble rol, deliberado, para una migración sin romper nada:

  • API nueva y limpia para las skills:
        ctx.say(...)            ctx.bus           ctx.memory
        ctx.ask(...)            ctx.config        ctx.persona
        ctx.service("dev")      ctx.emit(...)

  • API legacy idéntica a la que esperaba `parent_lia`, de modo que los módulos
    `mod_sistema`, `mod_dev`, etc. funcionen SIN CAMBIOS al recibir `ctx` como
    su `parent_lia`:
        ctx.hablar(...)         ctx.registrar_actividad(...)
        ctx.persona             ctx.sistema / ctx.dev / ctx.contexto / ...

Los servicios concretos (sistema, dev, internet, ...) los inyecta el kernel
con `attach_service()`; quedan accesibles como atributos (`ctx.sistema`) y por
nombre (`ctx.service("sistema")`).
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable, Optional

from core.event_bus import Event, EventBus
from core.session_context import SessionContext

logger = logging.getLogger("lia.context")


@dataclass
class PendingAction:
    """Una acción incompleta: Lia hizo una pregunta y espera la respuesta."""
    question: str
    on_answer: Callable[[str], None]
    cancel_words: tuple = (
        "cancela", "cancel", "olvida", "olvídalo", "olvidalo",
        "nada", "no importa", "déjalo", "dejalo",
    )


class AssistantContext:
    def __init__(self, bus: EventBus, config, persona, memory) -> None:
        self.bus = bus
        self.config = config
        self.persona = persona
        self.memory = memory

        # Servicios inyectados por el kernel (sistema, dev, internet, ...).
        self._services: dict[str, object] = {}

        # Referencia al kernel para operaciones de ciclo de vida (pausar,
        # reactivar, apagar). El kernel se asigna a sí mismo al arrancar. Es la
        # raíz de composición de la app, así que es legítimo que las skills de
        # control la usen a través de la fachada.
        self.kernel = None

        # Motor TTS y ventana GUI: los conecta el kernel cuando existen.
        self.voz = None
        self.detector = None
        self._gui_window = None  # compat: algunos módulos lo consultan

        # Escritor primario del historial de actividades. El kernel lo apunta al
        # servicio legacy `mod_memoria` para que haya UN solo escritor de
        # historial.json (evita doble escritura con MemoryStore).
        self._activity_logger = None

        # Contexto de sesión: estado de corta duración de la conversación.
        # Handlers anotan claves como "last_app", "current_topic", etc.
        self.session = SessionContext()

        # Estado de acción pendiente (pregunta de seguimiento).
        self._pending: Optional[PendingAction] = None
        self._pending_lock = threading.Lock()

    # ── Inyección de servicios (DI) ───────────────────────────────────────
    def attach_service(self, nombre: str, instancia: object) -> None:
        self._services[nombre] = instancia
        # Exponer también como atributo para compatibilidad legacy (ctx.sistema).
        setattr(self, nombre, instancia)

    def service(self, nombre: str):
        return self._services.get(nombre)

    # ── Salida de voz / logs (API nueva) ──────────────────────────────────
    def say(self, texto: str) -> None:
        """Dice algo: lo registra, lo publica al bus (GUI) y lo manda al TTS."""
        if not texto:
            return
        print(f"Lia: {texto}")
        self.bus.publish(Event.SPEAK, texto)
        if self.voz is not None:
            self.voz.decir(texto)

    def emit(self, topic: str, payload=None) -> None:
        self.bus.publish(topic, payload)

    def set_activity_logger(self, fn: Callable[[str], None]) -> None:
        self._activity_logger = fn

    def registrar_actividad(self, actividad: str) -> None:
        """Registra una actividad (escritor primario legacy) y avisa a la GUI."""
        try:
            if self._activity_logger is not None:
                self._activity_logger(actividad)
            else:
                self.memory.log_activity(actividad)
        except Exception as ex:
            logger.debug("No se pudo registrar actividad '%s': %s", actividad, ex)
        self.bus.publish(Event.ACTIVITY, actividad)

    def set_status(self, estado: str) -> None:
        self.bus.publish(Event.STATUS, estado)

    # ── API legacy (para que mod_* funcionen sin cambios) ─────────────────
    # Los módulos existentes llaman self.lia.hablar(...). Lo mapeamos a say().
    def hablar(self, texto: str) -> None:
        self.say(texto)

    # ── Preguntas de seguimiento (sustituye _pedir/_resolver_pendiente) ───
    def ask(self, question: str, on_answer: Callable[[str], None]) -> None:
        """
        Hace una pregunta y guarda un callback que se ejecutará con la respuesta.
        En lugar del antiguo dispatch central por `tipo` string, cada skill pasa
        su propio closure → menos acoplamiento, abierto a extensión.
        """
        with self._pending_lock:
            self._pending = PendingAction(question=question, on_answer=on_answer)
        self.say(question)

    def has_pending(self) -> bool:
        with self._pending_lock:
            return self._pending is not None

    def cancel_pending(self) -> None:
        with self._pending_lock:
            self._pending = None

    def resolve_pending(self, respuesta: str) -> None:
        with self._pending_lock:
            pending = self._pending
            self._pending = None
        if pending is None:
            return  # otro hilo ya lo resolvió (race prevenida)

        resp = respuesta.lower().strip()
        if any(w in resp for w in pending.cancel_words):
            self.say("Entendido, cancelado.")
            return
        try:
            pending.on_answer(respuesta.strip())
        except Exception as ex:
            logger.error("Error al resolver acción pendiente: %s", ex, exc_info=True)
            self.say(self.persona.error_generico("completar lo que pediste"))
