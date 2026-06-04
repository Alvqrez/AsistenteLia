#!/usr/bin/env python3
"""
memory_store.py — Memoria unificada de Lia (Fase 4).

El diseño anterior tenía la memoria fragmentada en 5+ lugares sin una capa
común: historial.json, memoria.json (notas), Pendientes.md, recordatorios y
vida (metas/hábitos/proyectos), cada uno con su propio acceso. No existía
memoria a corto plazo ni un punto único de consulta.

`MemoryStore` añade esa capa SIN romper lo existente:

  • Memoria a CORTO PLAZO (volátil): buffer en RAM de la conversación reciente
    e ítems de contexto efímero. Se pierde al cerrar, por diseño.

  • Memoria a LARGO PLAZO (persistente): archivo propio `lia_memory_store.json`
    con `facts`, `preferences`, `projects` y `context`. Escritura atómica.

  • CONSULTA transversal: `recall()` y `snapshot()` leen también las fuentes
    legacy (historial, pendientes) en modo solo-lectura, de modo que cualquier
    módulo obtenga una vista unificada sin duplicar datos.

No es el escritor del historial de actividades legacy (de eso sigue
encargándose `mod_memoria` para no introducir doble escritura); `log_activity`
existe para que el store sea autosuficiente y testeable de forma aislada.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import tempfile
import threading
from collections import deque
from typing import Any, Optional

logger = logging.getLogger("lia.memory")


def _atomic_write_json(ruta: str, data: dict) -> None:
    """Escritura atómica: temporal + os.replace. Evita corrupción ante crash."""
    dir_ = os.path.dirname(ruta) or "."
    fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, ruta)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class MemoryStore:
    def __init__(self, data_dir: str, short_term_size: int = 30, embedder=None) -> None:
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._path = os.path.join(data_dir, "lia_memory_store.json")
        self._historial_path = os.path.join(data_dir, "lia_historial.json")

        self._lock = threading.RLock()
        self._short_term: deque = deque(maxlen=short_term_size)
        self._data = self._load()

        # Embedder para recall semántico. Perezoso: se crea al primer uso para
        # no pagar el coste si nunca se consulta. Inyectable para tests.
        self._embedder = embedder

    # ── Persistencia ──────────────────────────────────────────────────────
    def _load(self) -> dict:
        default = {"facts": {}, "preferences": {}, "projects": [], "context": {}}
        try:
            if os.path.exists(self._path):
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in default.items():
                    data.setdefault(k, v)
                return data
        except Exception as ex:
            logger.error("No se pudo cargar memory_store: %s", ex)
        return default

    def _save(self) -> None:
        try:
            _atomic_write_json(self._path, self._data)
        except Exception as ex:
            logger.error("No se pudo guardar memory_store: %s", ex)

    # ── Corto plazo (volátil) ─────────────────────────────────────────────
    def remember_short(self, role: str, text: str) -> None:
        """Añade una entrada a la memoria de corto plazo (conversación reciente)."""
        with self._lock:
            self._short_term.append({
                "role": role, "text": text,
                "ts": datetime.datetime.now().isoformat(),
            })

    def recent(self, n: int = 10) -> list:
        with self._lock:
            return list(self._short_term)[-n:]

    # ── Largo plazo: hechos / preferencias ────────────────────────────────
    def set_fact(self, clave: str, valor: Any) -> None:
        with self._lock:
            self._data["facts"][clave.lower().strip()] = {
                "valor": valor,
                "ts": datetime.datetime.now().isoformat(),
            }
            self._save()

    def get_fact(self, clave: str, default=None):
        with self._lock:
            entry = self._data["facts"].get(clave.lower().strip())
            return entry["valor"] if entry else default

    def forget_fact(self, clave: str) -> bool:
        with self._lock:
            if clave.lower().strip() in self._data["facts"]:
                del self._data["facts"][clave.lower().strip()]
                self._save()
                return True
            return False

    def set_preference(self, clave: str, valor: Any) -> None:
        with self._lock:
            self._data["preferences"][clave.lower().strip()] = valor
            self._save()

    def get_preference(self, clave: str, default=None):
        with self._lock:
            return self._data["preferences"].get(clave.lower().strip(), default)

    # ── Largo plazo: contexto/proyecto activo ─────────────────────────────
    def set_context(self, clave: str, valor: Any) -> None:
        with self._lock:
            self._data["context"][clave] = valor
            self._save()

    def get_context(self, clave: str, default=None):
        with self._lock:
            return self._data["context"].get(clave, default)

    # ── Historial de actividades (autosuficiente; no es el escritor primario) ──
    def log_activity(self, actividad: str) -> None:
        """
        Registra una actividad en el historial legacy (mismo formato que
        `mod_memoria`). En producción el escritor primario es `mod_memoria`; el
        kernel enruta `registrar_actividad` allí para evitar doble escritura.
        """
        ts = datetime.datetime.now().isoformat()
        try:
            hist = {"actividades": [], "estadisticas": {}}
            if os.path.exists(self._historial_path):
                with open(self._historial_path, "r", encoding="utf-8") as f:
                    hist = json.load(f)
            hist["actividades"].append({"timestamp": ts, "actividad": actividad})
            hist["estadisticas"][actividad] = hist["estadisticas"].get(actividad, 0) + 1
            hist["actividades"] = hist["actividades"][-200:]
            _atomic_write_json(self._historial_path, hist)
        except Exception as ex:
            logger.error("No se pudo registrar actividad: %s", ex)

    def actividades_recientes(self, n: int = 20) -> list:
        try:
            if os.path.exists(self._historial_path):
                with open(self._historial_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("actividades", [])[-n:]
        except Exception as ex:
            logger.debug("No se pudo leer historial: %s", ex)
        return []

    # ── Consulta unificada (semántica) ────────────────────────────────────
    def _get_embedder(self):
        if self._embedder is None:
            from services.embeddings import get_embedder
            self._embedder = get_embedder()
        return self._embedder

    def _candidatos(self) -> list[str]:
        """Reúne el corpus consultable: hechos + corto plazo + actividades."""
        textos: list[str] = []
        with self._lock:
            for clave, entry in self._data["facts"].items():
                textos.append(f"{clave}: {entry.get('valor', '')}")
            for item in self._short_term:
                textos.append(item["text"])
        for act in self.actividades_recientes(50):
            t = act.get("actividad", "")
            if t:
                textos.append(t)
        # Dedup preservando orden.
        vistos, unicos = set(), []
        for t in textos:
            if t not in vistos:
                vistos.add(t)
                unicos.append(t)
        return unicos

    def recall(self, query: str, limite: int = 5, umbral: float = 0.13) -> list[str]:
        """
        Recuerdo semántico: rankea hechos, contexto reciente y actividades por
        similitud coseno con la consulta (embeddings), garantizando además los
        aciertos por subcadena. Sustituye la búsqueda por substring anterior.
        """
        candidatos = self._candidatos()
        if not candidatos:
            return []

        q = query.lower().strip()
        try:
            from services.embeddings import cosine_scores
            emb = self._get_embedder()
            qv = emb.embed([q])[0]
            mat = emb.embed(candidatos)
            sims = cosine_scores(qv, mat)
        except Exception as ex:
            logger.warning("recall semántico falló (%s); uso subcadena.", ex)
            return [c for c in candidatos if q in c.lower()][:limite]

        ranked = []
        for texto, score in zip(candidatos, sims):
            s = float(score)
            if q and q in texto.lower():
                s += 1.0  # garantiza prioridad a coincidencias literales
            if s >= umbral:
                ranked.append((s, texto))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in ranked[:limite]]

    def snapshot(self) -> dict:
        """Vista unificada para dashboards/diagnóstico."""
        with self._lock:
            return {
                "short_term": list(self._short_term),
                "facts": dict(self._data["facts"]),
                "preferences": dict(self._data["preferences"]),
                "projects": list(self._data["projects"]),
                "context": dict(self._data["context"]),
                "actividades_recientes": self.actividades_recientes(10),
            }
