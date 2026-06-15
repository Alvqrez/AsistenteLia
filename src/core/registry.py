#!/usr/bin/env python3
"""
registry.py — CommandRegistry: catálogo consultable de todos los comandos.

El IntentRouter sabe *despachar*; este registry sabe *qué existe*. Es la única
fuente de verdad para el help dinámico, la búsqueda de comandos y la validación
de conflictos. Nada de listas hardcodeadas: todo se deriva de los `IntentSpec`
que las skills/plugins registraron.

API:
    list_commands(category=None)  — specs ordenadas por categoría y nombre.
    by_category()                 — dict {categoria: [specs]} para el help.
    find(name)                    — spec por nombre exacto.
    search(query)                 — busca en nombre, descripción, aliases y ejemplos.
    execute(text)                 — delega en el router (mismo camino que la voz).
    validate()                    — detecta nombres duplicados, aliases duplicados
                                    y aliases "secuestrados" (rutean a otra intención
                                    de mayor prioridad). Devuelve advertencias.
"""

from __future__ import annotations

import logging
import unicodedata
from collections import defaultdict
from typing import Optional

from core.intent import IntentSpec

logger = logging.getLogger("lia.registry")

_SIN_CATEGORIA = "otros"


def _norm(texto: str) -> str:
    """minúsculas + sin acentos, para búsqueda tolerante ('via' == 'vía')."""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class CommandRegistry:
    """Fachada de consulta sobre los IntentSpec registrados en el router."""

    def __init__(self, router) -> None:
        self._router = router

    # ── Consulta ───────────────────────────────────────────────────────────
    @property
    def specs(self) -> list[IntentSpec]:
        return self._router.specs

    def list_commands(self, category: Optional[str] = None) -> list[IntentSpec]:
        specs = self.specs
        if category is not None:
            cat = _norm(category)
            specs = [s for s in specs if _norm(s.category or _SIN_CATEGORIA) == cat]
        return sorted(specs, key=lambda s: (s.category or _SIN_CATEGORIA, s.name))

    def by_category(self) -> dict[str, list[IntentSpec]]:
        grupos: dict[str, list[IntentSpec]] = defaultdict(list)
        for s in self.specs:
            grupos[s.category or _SIN_CATEGORIA].append(s)
        return {cat: sorted(specs, key=lambda s: s.name)
                for cat, specs in sorted(grupos.items())}

    def categories(self) -> list[str]:
        return list(self.by_category().keys())

    def find(self, name: str) -> Optional[IntentSpec]:
        return next((s for s in self.specs if s.name == name), None)

    def search(self, query: str) -> list[IntentSpec]:
        """Busca por subcadena (sin acentos) en toda la metadata del comando."""
        q = _norm(query.strip())
        if not q:
            return []
        resultados = []
        for s in self.specs:
            corpus = " ".join((s.name, s.description, s.category,
                               *s.aliases, *s.examples))
            if q in _norm(corpus):
                resultados.append(s)
        return resultados

    # ── Ejecución ──────────────────────────────────────────────────────────
    def execute(self, text: str) -> bool:
        """Ejecuta un comando de texto por el mismo camino que la voz/GUI."""
        return self._router.handle_text(text)

    # ── Validación ─────────────────────────────────────────────────────────
    def validate(self) -> list[str]:
        """
        Devuelve una lista de advertencias (vacía = sano):
          • nombre de intención duplicado;
          • alias declarado por más de una intención;
          • alias que el router resuelve a OTRA intención (colisión real de
            matchers/prioridades: el dueño nunca recibiría esa frase);
          • intención sin descripción (no aparecería bien en el help).
        """
        warnings: list[str] = []
        specs = self.specs

        vistos: dict[str, str] = {}
        for s in specs:
            if s.name in vistos:
                warnings.append(f"Nombre duplicado: '{s.name}' "
                                f"(skills '{vistos[s.name]}' y '{s.skill}').")
            vistos[s.name] = s.skill

        duenos_alias: dict[str, str] = {}
        for s in specs:
            for alias in s.aliases:
                a = _norm(alias)
                if a in duenos_alias and duenos_alias[a] != s.name:
                    warnings.append(f"Alias duplicado: '{alias}' declarado por "
                                    f"'{duenos_alias[a]}' y '{s.name}'.")
                duenos_alias.setdefault(a, s.name)

        for s in specs:
            for alias in s.aliases:
                match = self._router.match(alias.lower().strip())
                if match is None:
                    warnings.append(f"Alias muerto: '{alias}' de '{s.name}' "
                                    f"no coincide con ningún matcher.")
                elif match.name != s.name:
                    warnings.append(f"Alias secuestrado: '{alias}' de '{s.name}' "
                                    f"lo captura '{match.name}' "
                                    f"(prioridad {match.spec.priority} < {s.priority}).")

        for s in specs:
            if not s.description:
                warnings.append(f"Sin descripción: '{s.name}' (skill '{s.skill}').")

        for w in warnings:
            logger.warning("Validación de comandos: %s", w)
        return warnings
