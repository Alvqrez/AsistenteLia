# Cómo crear un comando nuevo en Lia

> v5.1 — Command Registry + auto-discovery. **Nunca se toca el núcleo.**

## TL;DR

1. Crea un archivo en `src/skills/` (built-in) o `src/plugins/<categoria>/` (plugin).
2. Define una subclase de `Skill` con sus `IntentSpec`.
3. Reinicia Lia. Listo: el comando se registra, aparece en "Lia, ayuda" y es
   buscable con "Lia, busca comando X".

No hay paso 4. No se edita el kernel, ni el router, ni ningún menú.

## Plantilla mínima

Copia `src/plugins/_plantilla.py` o parte de aquí:

```python
# src/plugins/musica/spotify_pause.py
from core.intent import IntentSpec
from core.matchers import contains_any
from core.skill import Skill


def _pausar(ctx, match):
    ctx.sistema.open_application("spotify")  # ejemplo: usa los servicios que necesites
    ctx.say("Música pausada.")
    ctx.registrar_actividad("Pausó Spotify")


class SpotifyPauseSkill(Skill):
    name = "spotify_pause"
    category = "musica"          # agrupa el comando en el help

    def intents(self, ctx):
        return [
            IntentSpec(
                name="spotify.pause",                      # único en todo el sistema
                priority=255,                              # menor = se evalúa antes
                matcher=contains_any(("pausa spotify", "pausa la música",
                                      "detén la canción", "deten la cancion")),
                handler=_pausar,
                description="Pausa la reproducción de Spotify",
                aliases=("pausa spotify", "pausa la música"),
                examples=("pausa la música",),
            ),
        ]
```

Si es un plugin, asegúrate de que `src/plugins/musica/__init__.py` exista (puede
estar vacío).

## Anatomía de un `IntentSpec`

| Campo | Obligatorio | Qué hace |
|---|---|---|
| `name` | ✔ | Identificador único (`categoria.accion`). La validación detecta duplicados. |
| `matcher` | ✔ | Decide si una frase activa el comando y extrae slots. Usa las fábricas de `core/matchers.py`. |
| `handler` | ✔ | `def handler(ctx, match)` — la acción. |
| `priority` | recomendado | Orden de evaluación (menor gana). Rango típico: 15–900. |
| `description` | ✔ (validado) | Una línea para el help dinámico y la búsqueda. |
| `category` | opcional | Si se omite, hereda `Skill.category`. |
| `aliases` | recomendado | Frases canónicas completas. El registry **valida** que cada alias rutee a su dueño (detecta secuestros por otra intención de mayor prioridad). |
| `examples` | recomendado | Frases con slots; documentación viva y semilla para NLU/IA futura. |

## Matchers disponibles (`core/matchers.py`)

| Fábrica | Coincide cuando... |
|---|---|
| `contains_any(frases)` | el texto contiene cualquiera de las subcadenas |
| `contains_word_any(frases)` | ídem pero con límites de palabra (evita "ram" en "rama") |
| `equals_any(frases)` | el texto ES exactamente una de las frases |
| `starts_with(prefijos)` | empieza con un prefijo; extrae el resto en un slot |
| `after_trigger(triggers)` | contiene un trigger; extrae lo que sigue en un slot |
| `regex(patron)` | regex con grupos nombrados como slots |
| `all_of(m1, m2)` | composición AND (fusiona slots) |
| `without(m, prohibidas)` | envuelve un matcher con palabras de exclusión |

## El contexto (`ctx`) — inyección de dependencias

El handler nunca usa globales; todo llega por `ctx` (`AssistantContext`):

```python
ctx.say("texto")                      # hablar (TTS + GUI + log)
ctx.ask("¿pregunta?", callback)       # pregunta de seguimiento (pendiente)
ctx.sistema / ctx.dev / ctx.internet / ctx.memoria / ctx.vida / ...   # servicios
ctx.service("scheduler")              # acceso por nombre
ctx.memory                            # MemoryStore (recall semántico)
ctx.config                            # configuración del usuario
ctx.emit("mi_evento", payload)        # publicar en el EventBus
ctx.bus.subscribe("command_executed", fn)   # reaccionar a eventos
ctx.registrar_actividad("...")        # historial del dashboard
ctx.kernel                            # ciclo de vida (pause/resume/shutdown)
```

## Eventos del bus que puedes escuchar (en `Skill.on_load`)

| Evento | Cuándo | Payload |
|---|---|---|
| `intent` | se resolvió una intención (antes de ejecutar) | `{name, text}` |
| `command_executed` | el handler terminó bien | `{name, text, skill, category}` |
| `command_failed` | el handler lanzó excepción | `{name, text, error}` |
| `speak` / `activity` / `status` / `listening` | voz, actividad, estado, STT | str |

## Cómo elegir `priority`

El router evalúa de menor a mayor y despacha el **primero** que coincide.
Regla práctica:

- **15–120** — comandos de control (cancela, ayuda, pausa...).
- **130–300** — frases con verbo específico ("abre X", "crea Y", "anota Z").
- **300–700** — comandos temáticos (git, clima, recordatorios...).
- **700–900** — frases genéricas que podrían chocar ("resumen", "hora").

Si tu alias lo captura otra intención, el arranque lo avisa:
`Alias secuestrado: 'pausa la música' de 'spotify.pause' lo captura 'control.pausa'`
→ baja tu `priority` o afina el matcher del otro.

## Validación automática

Al arrancar, `CommandRegistry.validate()` revisa y loguea advertencias:

- nombres de intención duplicados,
- aliases declarados por dos comandos,
- aliases que rutean a otra intención (colisión real de prioridad/matcher),
- aliases que no matchean nada (alias muerto),
- comandos sin descripción.

También puedes correrlo a mano: `python scripts/smoke_registry.py`
(sale con código 1 si hay cualquier advertencia).

## Checklist antes de dar por terminado un comando

- [ ] `python scripts/smoke_registry.py` → 0 advertencias.
- [ ] `python scripts/smoke_router.py` → 0 fallos (agrega tu frase a `CASOS`).
- [ ] "Lia, ayuda" muestra tu comando en la categoría correcta.
- [ ] "Lia, busca comando <tema>" lo encuentra.
