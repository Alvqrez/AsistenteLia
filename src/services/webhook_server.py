#!/usr/bin/env python3
"""
webhook_server.py — Servidor HTTP minimalista para integración con sistemas externos.

Expone dos endpoints en localhost (127.0.0.1) sin dependencias extra
(solo la librería estándar de Python):

  POST /command  {"text": "abre spotify"}
    → llama kernel.handle_text(text) y devuelve {"ok": true}

  GET  /status
    → devuelve {"active": true/false, "version": "5.1"}

Casos de uso:
  • Script de build/CI que avisa a Lia cuando termina:
      curl -X POST http://127.0.0.1:7845/command -d '{"text":"el build terminó"}'
  • GitHub Actions, Flutter hot-reload, cualquier herramienta externa.
  • Automatizaciones desde AutoHotkey, PowerShell, batch, etc.

El puerto por defecto es 7845, configurable con "webhook_port" en lia_config.json.
Se inicia como hilo daemon: se cierra solo cuando el proceso principal termina.
"""

from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger("lia.webhook")

_LIA_VERSION = "5.1"


class _Handler(BaseHTTPRequestHandler):
    """Handler sin estado — usa `_Handler.kernel` como referencia compartida."""
    kernel = None

    # ── POST ──────────────────────────────────────────────────────────────────
    def do_POST(self) -> None:
        if self.path != "/command":
            self._respond(404, {"error": "endpoint no encontrado"})
            return

        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            self._respond(400, {"error": "body vacío"})
            return

        try:
            body = self.rfile.read(length)
            data = json.loads(body)
        except (json.JSONDecodeError, Exception) as ex:
            self._respond(400, {"error": f"JSON inválido: {ex}"})
            return

        text = (data.get("text") or "").strip()
        if not text:
            self._respond(400, {"error": "campo 'text' vacío o ausente"})
            return

        kernel = _Handler.kernel
        if kernel is None:
            self._respond(503, {"error": "kernel no disponible"})
            return

        try:
            handled = kernel.handle_text(text)
            self._respond(200, {"ok": True, "handled": handled, "text": text})
            logger.info("Webhook: comando ejecutado → '%s' (handled=%s)", text, handled)
        except Exception as ex:
            logger.error("Webhook: error al ejecutar '%s': %s", text, ex)
            self._respond(500, {"error": str(ex)})

    # ── GET ───────────────────────────────────────────────────────────────────
    def do_GET(self) -> None:
        if self.path == "/status":
            kernel = _Handler.kernel
            if kernel is None:
                self._respond(503, {"error": "kernel no disponible"})
                return
            self._respond(200, {
                "active": kernel.active(),
                "version": _LIA_VERSION,
            })
        else:
            self._respond(404, {"error": "endpoint no encontrado"})

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _respond(self, code: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        # Redirigir logs de acceso al logger estándar de Lia (no stdout).
        logger.debug(fmt, *args)


class WebhookServer:
    def __init__(self, kernel, port: int = 7845) -> None:
        _Handler.kernel = kernel
        self._port = port
        try:
            self._server = HTTPServer(("127.0.0.1", port), _Handler)
        except OSError as ex:
            logger.warning("Webhook: no se pudo abrir puerto %d: %s", port, ex)
            self._server = None

    def start(self) -> None:
        if self._server is None:
            return
        t = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="LiaWebhook",
        )
        t.start()
        logger.info("Webhook escuchando en http://127.0.0.1:%d", self._port)
        print(f"   [Webhook] Escuchando en http://127.0.0.1:{self._port}")
        print(f"   [Webhook] POST /command  {{\"text\": \"tu comando\"}}  →  ejecuta en Lia")
        print(f"   [Webhook] GET  /status   →  estado del kernel")

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
