#!/usr/bin/env python3
"""
vida.py — Metas, hábitos y proyectos personales + resumen de vida.
Delega en `mod_vida` (VidaTools).

Nota: las intenciones de "agregar" tienen prioridad MÁS ALTA (296) que el
verbo genérico "agrega" de pendientes (300). Esto corrige un bug latente del
diseño anterior, donde "agrega meta X" era capturado por el handler de
pendientes y nunca llegaba a Metas.md, pese a estar anunciado en el menú.
"""

from __future__ import annotations

from core.intent import IntentSpec
from core.matchers import contains_any
from core.skill import Skill


def _add_after(ctx, m, kws, fn, pregunta):
    for kw in kws:
        if kw in m.text:
            texto = m.text.split(kw, 1)[-1].strip()
            if texto:
                fn(texto)
            else:
                ctx.say(pregunta)
            return


def _agregar_meta(ctx, m):
    _add_after(ctx, m, ("agrega meta ", "nueva meta ", "añade meta "),
               ctx.vida.agregar_meta, "¿Cuál es la meta que quieres agregar?")


def _leer_metas(ctx, m): ctx.vida.leer_metas()


def _completar_meta(ctx, m):
    for kw in ("meta lista ", "completé la meta ", "complete la meta ", "meta completada "):
        if kw in m.text:
            ctx.vida.completar_meta(m.text.split(kw, 1)[-1].strip())
            return


def _agregar_habito(ctx, m):
    _add_after(ctx, m, ("agrega hábito ", "agrega habito ", "nuevo hábito ", "nuevo habito "),
               ctx.vida.agregar_habito, "¿Cómo se llama el hábito?")


def _revisar_habitos(ctx, m): ctx.vida.revisar_habitos()


def _marcar_habito(ctx, m):
    for kw in ("hice el hábito ", "hice el habito ", "marqué el hábito ",
               "marque el habito ", "cumplí el hábito ", "cumpli el habito "):
        if kw in m.text:
            nombre = m.text.split(kw, 1)[-1].strip()
            if nombre:
                ctx.vida.marcar_habito(nombre)
            return


def _agregar_proyecto(ctx, m):
    _add_after(ctx, m, ("agrega proyecto ", "nuevo proyecto "),
               ctx.vida.agregar_proyecto, "¿Cómo se llama el proyecto?")


def _estado_proyectos(ctx, m): ctx.vida.estado_proyectos()


def _completar_proyecto(ctx, m):
    for kw in ("completé el proyecto ", "complete el proyecto ", "proyecto terminado "):
        if kw in m.text:
            ctx.vida.completar_proyecto(m.text.split(kw, 1)[-1].strip())
            return


def _resumen_vida(ctx, m): ctx.vida.resumen_vida()


class VidaSkill(Skill):
    name = "vida"
    category = "vida"

    def intents(self, ctx):
        return [
            # Resumen personal (antes que el "resumen" del día).
            IntentSpec(name="vida.resumen", priority=680,
                       matcher=contains_any(("resumen personal", "resumen de vida",
                                             "cómo estoy", "como estoy")),
                       handler=_resumen_vida,
                       description="Resumen de tus metas, hábitos y proyectos",
                       aliases=("resumen personal", "cómo estoy"),
                       examples=("resumen personal", "cómo estoy")),
            # Altas (prioridad alta para ganar al "agrega" genérico de pendientes).
            IntentSpec(name="vida.agregar_meta", priority=296,
                       matcher=contains_any(("agrega meta ", "nueva meta ", "añade meta ")),
                       handler=_agregar_meta,
                       description="Agrega una meta personal",
                       aliases=("agrega meta correr 5k",),
                       examples=("agrega meta correr 5k",)),
            IntentSpec(name="vida.agregar_habito", priority=296,
                       matcher=contains_any(("agrega hábito ", "agrega habito ",
                                             "nuevo hábito ", "nuevo habito ")),
                       handler=_agregar_habito,
                       description="Agrega un hábito a seguir",
                       aliases=("agrega hábito leer",),
                       examples=("agrega hábito leer",)),
            IntentSpec(name="vida.agregar_proyecto", priority=296,
                       matcher=contains_any(("agrega proyecto ", "nuevo proyecto ")),
                       handler=_agregar_proyecto,
                       description="Agrega un proyecto personal",
                       aliases=("agrega proyecto portafolio",),
                       examples=("agrega proyecto portafolio",)),
            # Lecturas y completar.
            IntentSpec(name="vida.metas", priority=760,
                       matcher=contains_any(("mis metas", "lista de metas", "qué metas tengo",
                                             "que metas tengo", "cuáles son mis metas")),
                       handler=_leer_metas,
                       description="Lee tus metas personales",
                       aliases=("mis metas",),
                       examples=("mis metas",)),
            IntentSpec(name="vida.completar_meta", priority=765,
                       matcher=contains_any(("meta lista ", "completé la meta ",
                                             "complete la meta ", "meta completada ")),
                       handler=_completar_meta,
                       description="Marca una meta como cumplida",
                       aliases=("meta lista correr 5k",),
                       examples=("meta lista correr 5k",)),
            IntentSpec(name="vida.habitos", priority=770,
                       matcher=contains_any(("mis hábitos", "mis habitos", "revisar hábitos",
                                             "revisar habitos", "cómo van mis hábitos",
                                             "como van mis habitos")),
                       handler=_revisar_habitos,
                       description="Revisa el estado de tus hábitos",
                       aliases=("mis hábitos",),
                       examples=("mis hábitos",)),
            IntentSpec(name="vida.marcar_habito", priority=775,
                       matcher=contains_any(("hice el hábito ", "hice el habito ",
                                             "marqué el hábito ", "marque el habito ",
                                             "cumplí el hábito ", "cumpli el habito ")),
                       handler=_marcar_habito,
                       description="Marca un hábito como hecho hoy",
                       aliases=("hice el hábito leer",),
                       examples=("hice el hábito leer",)),
            IntentSpec(name="vida.proyectos", priority=780,
                       matcher=contains_any(("mis proyectos", "estado de proyectos",
                                             "qué proyectos tengo", "que proyectos tengo")),
                       handler=_estado_proyectos,
                       description="Estado de tus proyectos personales",
                       aliases=("mis proyectos",),
                       examples=("mis proyectos",)),
            IntentSpec(name="vida.completar_proyecto", priority=785,
                       matcher=contains_any(("completé el proyecto ", "complete el proyecto ",
                                             "proyecto terminado ")),
                       handler=_completar_proyecto,
                       description="Marca un proyecto como terminado",
                       aliases=("proyecto terminado portafolio",),
                       examples=("proyecto terminado portafolio",)),
        ]
