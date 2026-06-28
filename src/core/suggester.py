#!/usr/bin/env python3
"""
suggester.py — Sugeridor de comandos para entradas no reconocidas.

100% offline y sin IA. Cuando el IntentRouter no encuentra ninguna intención,
este módulo busca el comando registrado más parecido a lo que dijo el usuario
y devuelve una sugerencia accionable ("¿quisiste decir ...?").

Por qué existe: hasta ahora un comando no reconocido sólo producía "no entendí".
Con 143 intenciones registradas, lo más probable es que el usuario haya dicho
algo MUY cercano a un comando real (un sinónimo no cubierto, una palabra de más,
un error de transcripción que el normalizador no atrapó). Sugerir el comando más
cercano convierte un callejón sin salida en un acierto a un "sí" de distancia.

Combina dos señales léxicas deterministas, ambas baratas:
  • difflib.SequenceMatcher sobre el texto completo (captura typos/orden).
  • solape de tokens (Jaccard de palabras), que rescata frases largas donde
    el ratio global de difflib se diluye por las palabras de relleno.

No usa embeddings ni red: el corpus se construye UNA vez al arrancar a partir de
los `IntentSpec` ya registrados (aliases + ejemplos), y cada consulta es
sub-milisegundo. Sólo se invoca en el camino de "no reconocido", que es raro.
"""

from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass
from typing import Optional

from core.intent import IntentSpec

logger = logging.getLogger("lia.suggester")

# Umbral mínimo de confianza para ofrecer una sugerencia. Calibrado en
# scripts/smoke_suggest.py: alto para evitar sugerir basura ("asdf" → nada),
# bajo para no perder near-misses razonables ("habre spotify" → "abre spotify").
_DEFAULT_THRESHOLD = 0.58

# Peso de cada señal. difflib pesa más (orden + typos); el solape de tokens
# desempata y rescata frases largas.
_W_RATIO = 0.6
_W_OVERLAP = 0.4


@dataclass(frozen=True)
class Suggestion:
    spec: IntentSpec
    phrase: str   # la frase canónica (alias/ejemplo) que más se pareció
    score: float


class CommandSuggester:
    """Encuentra el comando registrado más parecido a un texto no reconocido."""

    def __init__(self, registry, threshold: float = _DEFAULT_THRESHOLD) -> None:
        self._registry = registry
        self._threshold = threshold
        # Corpus: lista de (frase_normalizada, spec). Se construye perezosamente
        # la primera vez y se cachea (las specs no cambian tras el arranque).
        self._corpus: Optional[list[tuple[str, IntentSpec]]] = None

    def _build_corpus(self) -> list[tuple[str, IntentSpec]]:
        corpus: list[tuple[str, IntentSpec]] = []
        for spec in self._registry.specs:
            # No sugerir kill-switches globales ("aborta"): nunca son lo que el
            # usuario "quiso decir" tras un comando no entendido.
            if spec.global_override:
                continue
            frases = set(spec.aliases) | set(spec.examples)
            for frase in frases:
                f = frase.lower().strip()
                if f:
                    corpus.append((f, spec))
        logger.debug("Corpus de sugerencias: %d frases", len(corpus))
        return corpus

    @staticmethod
    def _token_overlap(qt: list[str], pt: list[str]) -> float:
        """
        Solape DIFUSO de tokens: un token de la consulta cuenta si es igual o
        muy parecido (typo) a algún token de la frase. Necesario para que un
        typo de palabra única ('klima' ~ 'clima') no quede en cero por no haber
        intersección exacta de conjuntos.
        """
        if not qt or not pt:
            return 0.0
        aciertos = 0
        for q in qt:
            if any(q == p or difflib.SequenceMatcher(None, q, p).ratio() >= 0.8
                   for p in pt):
                aciertos += 1
        return aciertos / max(len(qt), len(pt))

    def _score(self, query: str, phrase: str) -> float:
        ratio = difflib.SequenceMatcher(None, query, phrase).ratio()
        overlap = self._token_overlap(query.split(), phrase.split())
        return _W_RATIO * ratio + _W_OVERLAP * overlap

    def suggest(self, text: str) -> Optional[Suggestion]:
        """
        Devuelve la mejor `Suggestion` por encima del umbral, o None si nada se
        parece lo suficiente. `text` debe venir ya normalizado (minúsculas).
        """
        q = (text or "").lower().strip()
        if not q:
            return None
        if self._corpus is None:
            self._corpus = self._build_corpus()

        mejor: Optional[Suggestion] = None
        for frase, spec in self._corpus:
            s = self._score(q, frase)
            if mejor is None or s > mejor.score:
                mejor = Suggestion(spec=spec, phrase=frase, score=s)

        if mejor is not None and mejor.score >= self._threshold:
            logger.debug("Sugerencia: '%s' → '%s' (%.2f)", q, mejor.phrase, mejor.score)
            return mejor
        return None
