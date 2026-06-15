"""
plugins — Comandos de terceros / personales, cargados automáticamente.

Funciona igual que `skills/` pero pensado para crecer por categorías:

    plugins/
        spotify/
            __init__.py        (vacío)
            playback.py        → SpotifyPlaybackSkill(Skill)
        universidad/
            __init__.py
            horarios.py        → HorariosSkill(Skill)

El `SkillRegistry` recorre este paquete de forma RECURSIVA al arrancar:
cualquier subclase de `core.skill.Skill` en cualquier subpaquete se instancia
y sus `IntentSpec` se registran en el router. No se toca el núcleo jamás.

Reglas:
  • Un archivo = una unidad de comandos (una Skill con sus intenciones).
  • Los módulos que empiezan por '_' se ignoran (helpers/plantillas).
  • Cada subpaquete necesita su `__init__.py`.
  • Copia `_plantilla.py` para empezar un comando nuevo.
  • La guía completa está en `docs/CREAR_COMANDO.md`.
"""
