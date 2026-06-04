# Arquitectura de Lia

> Documento de la Fase 14. Describe la arquitectura **anterior**, la **nueva**
> (ya implementada), el diagrama de módulos, el plan de migración, los riesgos
> y las prioridades para los próximos años.

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

## 2. Arquitectura nueva (v5.0) — implementada

```
                         ┌──────────────┐
            main.py ────►│  LiaKernel   │  orquestador delgado
                         └──────┬───────┘
        ┌───────────────┬───────┼────────────┬──────────────┐
        ▼               ▼       ▼            ▼              ▼
   ┌─────────┐   ┌────────────┐ │      ┌──────────┐  ┌─────────────┐
   │ EventBus│   │AssistantCtx│ │      │IntentRouter│  │SkillRegistry│
   │ (pub/sub│◄──┤ (fachada + │ │      │ (prioridad │  │(auto-descubre│
   │ logs/UI)│   │  DI + ask) │ │      │  → handler)│  │  skills/)   │
   └─────────┘   └──────┬─────┘ │      └─────┬──────┘  └──────┬──────┘
                        │       │            │ registra        │
                        │       │            ▼                 ▼
                        │       │     ┌──────────────────────────────┐
                        │       │     │  skills/  (auto-registradas)  │
                        │       │     │  apps, files, system_info,    │
                        │       │     │  dev, internet, tasks,        │
                        │       │     │  productivity, reminders,     │
                        │       │     │  focus, vida, workspace,      │
                        │       │     │  resumen, voice_control       │
                        │       │     └───────────────┬──────────────┘
                        │       │ inyecta servicios    │ delega en
                        ▼       ▼                      ▼
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
| 8+ | Visión/OCR, control de escritorio | 🟡 Scaffold listo |

`Lia.py` (god-object) se **conserva como fallback** hasta validar v5.0 en uso
real; `main.py` ya arranca el `LiaKernel`.

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
   en el entorno de desarrollo). *Mitigación:* `Lia.py` se conserva como fallback;
   tests de ruteo (`scripts/smoke_router.py`, 61 casos) y de comportamiento
   (`scripts/smoke_behavior.py`) cubren la lógica sin audio. **Validar en uso real.**
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

1. **Validar v5.0 con micrófono real**; si todo bien, eliminar `Lia.py` y
   `mod_dashboard.py` (ya deprecado).
2. **Fase 6 (IA):** implementar `ClaudeProvider`/`OpenAIProvider` y un
   `IntentResolver` de fallback → conversación natural real. Con IA disponible,
   activar también `sentence-transformers` para `recall` semántico de alta precisión.
3. **Fase 8/9:** implementar `DesktopService` (ventanas/multimedia) y
   `VisionService` (OCR de pantalla) sobre los scaffolds ya creados.
4. **Tests:** ampliar la batería de `smoke_router` a medida que se añaden skills.

Ya completado: dashboard consolidado (React único con datos reales) y memoria
semántica (`recall` por embeddings offline).
