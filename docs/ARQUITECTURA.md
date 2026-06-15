# Arquitectura de Lia

> Documento de la Fase 14, actualizado en v5.1 (Command Registry). Describe la
> arquitectura **anterior**, la **nueva** (ya implementada), el diagrama de
> módulos, el plan de migración, los riesgos y las prioridades.

---

## 1. Arquitectura anterior (v4.x)

```
main.py ─► LiaAssistant (Lia.py, 1382 líneas)
              │  god-object: estado + threading + parsing + orquestación
              │
              ├─ _parse_command()  ── ~620 líneas de if/elif (orden-dependiente)
              │
              └─ instancia y posee a TODOS los módulos:
                 mod_sistema, mod_memoria, mod_internet, mod_dev, mod_voz,
                 mod_personalidad, mod_productividad, mod_focus, mod_resumen,
                 mod_contexto, mod_config, mod_vida, mod_recordatorios,
                 mod_audio, mod_dashboard, mod_sonidos

cada mod_*  ──► recibe el god-object completo como `parent_lia`
                y llama self.lia.hablar(), self.lia.persona, self.lia.sistema...
                (acoplamiento bidireccional fuerte)
GUI (mod_gui + web/) ──► web_bridge llama lia._parse_command() directamente
```

**Problemas centrales:** god-object (viola SRP), parser `if/elif` (viola OCP),
acoplamiento por `parent_lia` concreto (viola DIP), parsing duplicado (viola
DRY), memoria fragmentada, recordatorios efímeros, GUI acoplada a internals.

---

## 2. Arquitectura nueva (v5.1) — implementada

```
                         ┌──────────────┐
            main.py ────►│  LiaKernel   │  orquestador delgado
                         └──────┬───────┘
        ┌───────────────┬───────┼────────────┬──────────────┐
        ▼               ▼       ▼            ▼              ▼
   ┌─────────┐   ┌────────────┐ │      ┌──────────┐  ┌─────────────┐
   │ EventBus│   │AssistantCtx│ │      │IntentRouter│  │SkillRegistry│
   │ (pub/sub│◄──┤ (fachada + │ │      │ (prioridad │  │(auto-descubre│
   │ logs/UI)│   │  DI + ask) │ │      │  → handler)│  │ RECURSIVO)  │
   └─────────┘   └──────┬─────┘ │      └─────┬──────┘  └──────┬──────┘
        ▲               │       │            │                 │
        │ command_      │       │      ┌─────┴───────┐         │
        │ executed/     │       │      │CommandRegistry│        │
        │ failed/intent │       │      │ list/search/ │◄── help dinámico,
        │               │       │      │ validate     │    "busca comando X"
        │               │       │      └──────────────┘
        │               │       │            ▲ registra
        │               │       │   ┌────────┴──────────────────────┐
        │               │       │   │ skills/   (built-in, 13 mods) │
        │               │       │   │ plugins/<categoria>/*.py      │
        │               │       │   │   (terceros/personales,       │
        │               │       │   │    descubrimiento recursivo)  │
        │               │       │   └───────────────┬───────────────┘
        │               │ inyecta servicios          │ delega en
        │               ▼                            ▼
   ┌────────────────────────────────────────────────────────────────┐
   │ services/                       │  mod_* (capa de implementación │
   │  memory_store  (corto/largo)    │  REUTILIZADA, sin reescribir): │
   │  scheduler     (persistente)    │  mod_sistema, mod_dev, ...     │
   │  ai/  (AIProvider, Null+stubs)  │  mod_voz, mod_audio, ...       │
   │  vision/ (OCR scaffold)         │                                │
   │  desktop/ (ventanas scaffold)   │                                │
   └────────────────────────────────────────────────────────────────┘

   GUI (mod_gui + web/) ──► se suscribe al EventBus (SPEAK/ACTIVITY/STATUS)
                            y envía comandos vía kernel.handle_text()
```

### Novedades v5.1 (Command Registry)
- **`core/registry.py` — CommandRegistry**: catálogo consultable de comandos
  (listar, buscar, describir, ejecutar) + **validación al arranque**: nombres
  duplicados, aliases duplicados, aliases "secuestrados" por otra intención y
  comandos sin descripción.
- **Metadata en `IntentSpec`**: `description`, `category` (heredable de la
  skill) y `aliases` (frases canónicas, validadas contra el router real).
- **Plugins**: `plugins/<categoria>/*.py` se cargan automáticamente
  (descubrimiento recursivo). Plantilla en `plugins/_plantilla.py`; guía en
  `docs/CREAR_COMANDO.md`. Plugins reales incluidos (123 comandos en total):
  `musica/` (control de Spotify/volumen/canción actual), `desarrollo/`
  (proyecto activo, runner de comandos flutter/npm con whitelist),
  `productividad/` (agenda del día, prioridad, modo profundo, control de
  pomodoro), `proyectos/` (ideas, proyecto activo), `universidad/` (exámenes
  con cuenta regresiva), `sistema/` (salud: CPU/RAM/disco/temperaturas,
  optimizar memoria, limpiar temporales), `automatizacion/` (entornos de
  trabajo/Flutter/web) y `utilidades/` (contraseñas seguras, apagar pantalla).
- **Modo JARVIS**: `mod_contexto.detectar_comando_proyecto()` detecta
  Flutter/Vite/Next/React/Node/Django/Python/Rust/Go y "ejecuta el proyecto"
  lanza el comando correcto en una terminal visible, sin preguntar.
- **Help 100% dinámico**: `lia_comandos.txt` y el resumen hablado se generan
  desde el registry; nada hardcodeado. Nuevo comando "busca comando X".
- **Eventos de comando**: el router publica `intent`, `command_executed` y
  `command_failed` en el EventBus (módulos/plugins reaccionan sin acoplarse).
- **`Lia.py` y `mod_dashboard.py` eliminados**: el if/elif de 620 líneas ya no
  existe ni como fallback.

### Principios aplicados
- **DIP:** las skills dependen de `AssistantContext` (abstracción), no del kernel.
- **OCP:** añadir habilidad = crear `skills/x.py`; no se toca el núcleo.
- **SRP:** kernel solo ensambla; router solo enruta; skills solo deciden acción.
- **DRY:** `core/matchers.py` elimina el `split(trigger)` repetido ~30 veces.
- **Compatibilidad:** `AssistantContext` expone la interfaz legacy (`hablar`,
  `persona`, `registrar_actividad`, `sistema`...) para que los `mod_*` funcionen
  sin cambios al recibir el contexto como `parent_lia`.

### El IntentRouter reproduce y mejora el if/elif
Cada `IntentSpec` tiene una `priority`. El router evalúa en orden ascendente y
despacha el primero que coincide → **misma semántica** que el if/elif, pero
modular. Las colisiones que antes se resolvían por orden de líneas ahora son
prioridades explícitas y documentadas (p. ej. `vida.resumen`=680 gana a
`resumen.dia`=690).

---

## 3. Migración: estado

| Etapa | Descripción | Estado |
|------|-------------|--------|
| 0 | Andamiaje `core/` (EventBus, Context, Router, Skill) | ✅ Hecho |
| 1 | Logs/estado vía EventBus; GUI desacoplada | ✅ Hecho |
| 2 | Skills piloto + router junto al if/elif | ✅ Superado |
| 3 | **Todas** las skills migradas; if/elif retirado | ✅ Hecho |
| 4 | `MemoryStore` unificado + recordatorios persistentes | ✅ Hecho |
| 5 | `AIProvider` abstracto (sin proveedor real, por decisión) | ✅ Interfaz lista |
| 6 | Endurecimiento de seguridad (confirmación destructivos) | ✅ Hecho |
| 7 | **Dashboard consolidado** (una sola GUI React con datos reales) | ✅ Hecho |
| 7 | **Memoria semántica** (`recall` por embeddings) | ✅ Hecho |
| 9 | **CommandRegistry** (metadata, validación, búsqueda, help dinámico) | ✅ Hecho (v5.1) |
| 9 | **Plugin system** (`plugins/<categoria>/`, carga recursiva) | ✅ Hecho (v5.1) |
| 9 | **`Lia.py` + `mod_dashboard.py` eliminados** (fin del if/elif) | ✅ Hecho (v5.1) |
| 8+ | Visión/OCR, control de escritorio | 🟡 Scaffold listo |

---

## 4. Capacidades JARVIS: dónde se enchufa cada una

| Fase | Capacidad | Punto de extensión |
|------|-----------|--------------------|
| 5 | Motor de intenciones | `core/intent.py` + `core/matchers.py`; `IntentSpec.examples` ya alimenta NLU futura |
| 6 | IA (ChatGPT/Claude/Gemini/local) | `services/ai/` — implementar un proveedor + inyectarlo; opcional `IntentResolver` en el router |
| 4 | Memoria avanzada | `services/memory_store.py` + `services/embeddings.py` — `recall()` ya es **semántico** (cosine sobre embeddings; offline por defecto) |
| 8 | Control de sistema/multimedia | `services/desktop/` — implementar `DesktopService` |
| 9 | Visión / OCR | `services/vision/` — implementar `VisionService` |
| 10 | Productividad dev | `skills/dev.py` — añadir intenciones (PRs, auditorías, Claude Code) |
| 11 | Dashboard | **Único** (React), datos reales vía `getDashboardData`; GUI escucha EventBus para logs/estado |

---

## 4b. Robustez operativa (v5.0)

- **Arranque resiliente:** si falla TTS, micrófono o detector de aplausos, el
  kernel arranca igualmente en modo degradado; la GUI y los comandos por texto
  siguen funcionando. Validado por `scripts/smoke_kernel.py` (modo sin micrófono).
- **Logging:** `main.py` configura consola + archivo rotatorio `data/lia.log`
  (se había perdido al dejar de usar `Lia.py` como entry point).
- **UTF-8 forzado** en stdout/stderr para evitar `UnicodeEncodeError` en consolas
  cp1252 (Windows).

## 5. Riesgos y mitigaciones

1. **No se pudo probar el flujo de voz/audio real en migración** (sin micrófono
   en el entorno de desarrollo). *Mitigación:* tests de ruteo
   (`scripts/smoke_router.py`, 61 casos), de comportamiento
   (`scripts/smoke_behavior.py`) y de catálogo (`scripts/smoke_registry.py`)
   cubren la lógica sin audio. `Lia.py` fue eliminado en v5.1 (recuperable en
   git si hiciera falta). **Validar en uso real.**
2. **Bugs latentes corregidos** podrían cambiar comportamiento que alguien
   esperaba roto: `nueva rama`/`mis ramas` ya no caen en "info del sistema"
   (la subcadena `ram`); `agrega meta/hábito/proyecto` ya no se anotan como
   pendiente; `abre vscode en`/`abre maps` ya funcionan.
3. **Acciones destructivas por voz** (apagar, cerrar todo) ahora piden
   confirmación: cambia ligeramente la UX, pero evita apagados por falso positivo.
4. **Dashboard duplicado:** resuelto. La GUI React es ahora el único dashboard,
   alimentado con datos reales (`services/dashboard_data.py` + bridge
   `getDashboardData`). El popup tkinter (`mod_dashboard.py`) queda **deprecado**
   y solo existe para el fallback de `Lia.py`; eliminar tras validar v5.0.
   El comando "dashboard"/"panel" trae al frente la ventana React (señal Qt).
5. **Memoria semántica:** `MemoryStore.recall()` usa embeddings (cosine). Por
   defecto un `HashingEmbedder` offline (numpy, sin descargas) que capta
   similitud léxica/morfológica; opcionalmente `sentence-transformers` real si
   se instala y se configura `embedder: sentence-transformer`. Tras esto,
   `recall` ya no es búsqueda por subcadena.

---

## 6. Prioridades recomendadas (próximos pasos)

1. **Validar v5.1 con micrófono real** (la lógica está cubierta por smokes,
   pero el flujo de audio solo se valida en uso).
2. **Fase 6 (IA):** implementar `ClaudeProvider`/`OpenAIProvider` y un
   `IntentResolver` de fallback → conversación natural real. Los
   `IntentSpec.examples`/`aliases` ya son el dataset para ese resolutor. Con IA
   disponible, activar `sentence-transformers` para `recall` de alta precisión.
3. **Primer plugin real** (p.ej. `plugins/musica/` con control de Spotify) para
   ejercitar el pipeline de plugins de punta a punta.
4. **Fase 8/9:** implementar `DesktopService` (ventanas/multimedia) y
   `VisionService` (OCR de pantalla) sobre los scaffolds ya creados.
5. **Tests:** `smoke_registry.py` en cada arranque de CI; ampliar `smoke_router`
   al añadir comandos.

Ya completado: dashboard consolidado, memoria semántica, CommandRegistry con
validación, plugins auto-descubiertos, help dinámico y retiro definitivo del
god-object.
