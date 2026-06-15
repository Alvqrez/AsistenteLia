#!/usr/bin/env python3
"""
skill.py — Skill base + SkillRegistry con auto-descubrimiento (Fase 3).

Objetivo central del rediseño: **agregar una habilidad nueva NO debe requerir
tocar el núcleo**. Para añadir, por ejemplo, una skill de Spotify, basta con
crear `skills/spotify.py` con una subclase de `Skill`; el registry la descubre
e registra automáticamente al arrancar.

    class SpotifySkill(Skill):
        name = "spotify"
        def intents(self, ctx):
            return [IntentSpec(name="spotify.play", matcher=..., handler=...)]

El registry recorre el paquete `skills/`, instancia toda subclase de `Skill`,
pide sus `IntentSpec`s y los inscribe en el `IntentRouter`.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Iterable

from core.intent import IntentSpec

logger = logging.getLogger("lia.skills")


class Skill:
    """Clase base de una habilidad. Las subclases declaran sus intenciones."""

    #: identificador legible de la skill (lo usan logs y el registry)
    name: str = "skill"

    #: categoría por defecto de las intenciones de esta skill. Cada IntentSpec
    #: puede sobreescribirla con su propio `category`; si lo deja vacío, el
    #: registry sella esta. Alimenta el help dinámico agrupado.
    category: str = ""

    def intents(self, ctx) -> Iterable[IntentSpec]:
        """Devuelve los IntentSpec que aporta esta skill. Sobreescribir."""
        return ()

    def on_load(self, ctx) -> None:
        """Hook opcional tras instanciar la skill (suscripciones al bus, etc.)."""
        pass


class SkillRegistry:
    def __init__(self) -> None:
        self.skills: list[Skill] = []

    def discover(self, package_name: str = "skills") -> list[type[Skill]]:
        """
        Importa los módulos del paquete (recursivo: soporta subpaquetes tipo
        `plugins/spotify/*.py`) y recolecta subclases de Skill.
        Los módulos cuyo nombre empieza por '_' son helpers y se omiten.
        """
        clases: list[type[Skill]] = []
        try:
            paquete = importlib.import_module(package_name)
        except Exception as ex:
            logger.error("No se pudo importar el paquete de skills '%s': %s",
                         package_name, ex)
            return clases

        for _, full, _ in pkgutil.walk_packages(paquete.__path__,
                                                prefix=f"{package_name}."):
            if full.rsplit(".", 1)[-1].startswith("_"):
                continue
            try:
                modulo = importlib.import_module(full)
            except Exception as ex:
                logger.error("Error importando skill '%s': %s", full, ex, exc_info=True)
                continue
            for attr in vars(modulo).values():
                if (isinstance(attr, type) and issubclass(attr, Skill)
                        and attr is not Skill and attr.__module__ == full):
                    clases.append(attr)
        return clases

    def register_all(self, router, ctx, package_name: str = "skills") -> int:
        """Descubre, instancia y registra todas las skills. Devuelve cuántos intents."""
        total_intents = 0
        for cls in self.discover(package_name):
            try:
                skill = cls()
                skill.on_load(ctx)
                specs = list(skill.intents(ctx))
                # Sellar metadata de la skill propietaria en cada spec.
                for s in specs:
                    object.__setattr__(s, "skill", skill.name)
                    if not s.category:
                        object.__setattr__(s, "category", skill.category)
                    router.register(s)
                self.skills.append(skill)
                total_intents += len(specs)
                logger.info("Skill '%s' registrada (%d intenciones).", skill.name, len(specs))
            except Exception as ex:
                logger.error("No se pudo cargar la skill %s: %s", cls, ex, exc_info=True)
        logger.info("Total: %d skills, %d intenciones.", len(self.skills), total_intents)
        return total_intents
