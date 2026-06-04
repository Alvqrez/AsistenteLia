#!/usr/bin/env python3
"""
embeddings.py — Embeddings para memoria semántica (Fase 4).

Abstracción `Embedder` con dos implementaciones:

  • HashingEmbedder (default, OFFLINE, solo numpy): feature hashing sobre
    palabras y trigramas de caracteres con L2-normalización. No requiere
    descargar modelos ni red. Captura similitud léxica/morfológica (p. ej.
    "programar" ~ "programación", tolera orden de palabras y typos) — muy por
    encima de la coincidencia por subcadena que había antes.

  • SentenceTransformerEmbedder (opcional): embeddings semánticos reales si
    `sentence-transformers` está instalado. Se activa por configuración; el
    resto del sistema no cambia (mismo contrato `Embedder`).

Esto da "memoria semántica" hoy, sin conectar ningún proveedor de IA, y deja
la puerta abierta a embeddings de modelo cuando se desee.
"""

from __future__ import annotations

import hashlib
import logging
import re
from abc import ABC, abstractmethod

import numpy as np

logger = logging.getLogger("lia.embeddings")

_WORD_RX = re.compile(r"\w+", re.UNICODE)


class Embedder(ABC):
    name: str = "abstract-embedder"
    dim: int = 0

    @abstractmethod
    def embed(self, textos: list[str]) -> np.ndarray:
        """Devuelve una matriz (n, dim) de vectores L2-normalizados."""
        ...


class HashingEmbedder(Embedder):
    """Feature hashing con signo sobre palabras + trigramas de caracteres."""

    name = "hashing"

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    @staticmethod
    def _hash(token: str) -> int:
        # Hash determinista entre procesos (hash() de Python está saltado).
        return int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)

    def _tokens(self, texto: str) -> list[str]:
        t = texto.lower().strip()
        palabras = _WORD_RX.findall(t)
        trigramas = [t[i:i + 3] for i in range(max(0, len(t) - 2))]
        return palabras + trigramas

    def embed(self, textos: list[str]) -> np.ndarray:
        out = np.zeros((len(textos), self.dim), dtype=np.float32)
        for i, txt in enumerate(textos):
            for tok in self._tokens(txt):
                h = self._hash(tok)
                idx = h % self.dim
                signo = 1.0 if (h // self.dim) % 2 == 0 else -1.0
                out[i, idx] += signo
            norma = np.linalg.norm(out[i])
            if norma > 0:
                out[i] /= norma
        return out


class SentenceTransformerEmbedder(Embedder):
    """Embeddings semánticos reales (opcional, requiere sentence-transformers)."""

    name = "sentence-transformer"

    def __init__(self, model: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer  # import perezoso
        self._model = SentenceTransformer(model)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, textos: list[str]) -> np.ndarray:
        vecs = self._model.encode(textos, normalize_embeddings=True)
        return np.asarray(vecs, dtype=np.float32)


def get_embedder(config=None) -> Embedder:
    """
    Selecciona el embedder. Default: HashingEmbedder (offline). Si la config
    pide 'sentence-transformer' y la librería está instalada, lo usa.
    """
    nombre = "hashing"
    if config is not None:
        try:
            nombre = config.get("embedder", "hashing") or "hashing"
        except Exception:
            nombre = "hashing"
    if nombre == "sentence-transformer":
        try:
            return SentenceTransformerEmbedder()
        except Exception as ex:
            logger.warning("sentence-transformers no disponible (%s). Uso HashingEmbedder.", ex)
    return HashingEmbedder()


def cosine_scores(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Similitud coseno de un vector contra cada fila (todos ya normalizados)."""
    if matrix.shape[0] == 0:
        return np.array([], dtype=np.float32)
    return matrix @ query_vec
