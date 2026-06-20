#!/usr/bin/env python3
"""
unrecognized_log.py — Registro de comandos que Lia no entendió (Fase auditoría).

Cuando el IntentRouter no encuentra ninguna intención para una frase, el kernel
la entrega aquí. El servicio:

  • Acumula un contador de frecuencia por frase normalizada (data/unrecognized.json).
  • Deja una bitácora legible en data/unrecognized_commands.txt (fecha + texto + nº).
  • Ofrece `top()` para sugerir qué aliases nuevos valdría la pena crear: las
    frases que más se repiten son las que Lia debería aprender a entender.

Diseño:
  • Thread-safe: lo invocan el hilo STT y el hilo de la GUI.
  • Escritura atómica del JSON (tmp + os.replace), igual que ConfigManager/macros.
  • Ignora ruido trivial (frases vacías o de 1–2 caracteres) para no inflar el log.
  • Cota de memoria: conserva como máximo `max_entries` frases distintas (las más
    frecuentes), evitando crecimiento ilimitado del diccionario y del archivo.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import tempfile
import threading

logger = logging.getLogger("lia.unrecognized")

_MIN_LEN = 3          # frases más cortas se consideran ruido de STT
_MAX_ENTRIES = 200    # tope de frases distintas que se conservan


class UnrecognizedLog:
    def __init__(self, data_dir: str, max_entries: int = _MAX_ENTRIES) -> None:
        self._json_path = os.path.join(data_dir, "unrecognized.json")
        self._txt_path = os.path.join(data_dir, "unrecognized_commands.txt")
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._counts: dict[str, dict] = self._load()

    # ── Persistencia ────────────────────────────────────────────────────────
    def _load(self) -> dict[str, dict]:
        try:
            if os.path.exists(self._json_path):
                with open(self._json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("frases", {}) if isinstance(data, dict) else {}
        except Exception as ex:
            logger.warning("No se pudo leer unrecognized.json: %s", ex)
        return {}

    def _save(self) -> None:
        # Conserva solo las N frases más frecuentes (cota de memoria/archivo).
        if len(self._counts) > self._max_entries:
            top = sorted(self._counts.items(),
                         key=lambda kv: kv[1].get("count", 0), reverse=True)
            self._counts = dict(top[: self._max_entries])
        try:
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self._json_path), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"frases": self._counts}, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self._json_path)
        except Exception as ex:
            logger.error("No se pudo guardar unrecognized.json: %s", ex)

    # ── API ──────────────────────────────────────────────────────────────────
    def record(self, texto: str) -> None:
        """Registra una frase no reconocida (ya normalizada por el router)."""
        frase = (texto or "").strip()
        if len(frase) < _MIN_LEN:
            return
        ahora = datetime.datetime.now().isoformat(timespec="seconds")
        with self._lock:
            entry = self._counts.get(frase, {"count": 0, "primero": ahora})
            entry["count"] = int(entry.get("count", 0)) + 1
            entry["ultimo"] = ahora
            self._counts[frase] = entry
            count = entry["count"]
            self._save()
            try:
                with open(self._txt_path, "a", encoding="utf-8") as f:
                    f.write(f"{ahora}\t(x{count})\t{frase}\n")
            except Exception as ex:
                logger.debug("No se pudo escribir unrecognized_commands.txt: %s", ex)
        logger.info("Comando no reconocido (x%d): '%s'", count, frase)

    def top(self, n: int = 5, min_count: int = 2) -> list[tuple[str, int]]:
        """Frases no reconocidas más frecuentes (candidatas a alias nuevo)."""
        with self._lock:
            items = [(frase, e.get("count", 0)) for frase, e in self._counts.items()
                     if e.get("count", 0) >= min_count]
        items.sort(key=lambda kv: kv[1], reverse=True)
        return items[:n]

    def clear(self) -> None:
        with self._lock:
            self._counts = {}
            self._save()
