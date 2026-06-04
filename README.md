# Asistente Lia 🤖

Asistente personal en Python (estilo JARVIS) con voz, detección de aplausos y
una arquitectura modular basada en **skills** auto-registradas.

## Arquitectura (v5.0)

Lia usa un núcleo desacoplado: `EventBus` + `IntentRouter` + **skills**
auto-registradas, con los módulos `mod_*` como capa de implementación. Añadir
una habilidad nueva = crear un archivo en `src/skills/` (no se toca el núcleo).

Ver **[docs/ARQUITECTURA.md](docs/ARQUITECTURA.md)** para el detalle (diagrama,
plan de migración, riesgos y prioridades).

```
src/
  core/      EventBus, IntentRouter, AssistantContext, Skill registry, LiaKernel
  skills/    una skill por dominio (apps, dev, internet, tasks, vida, ...)
  services/  memory_store (memoria unificada), scheduler (recordatorios
             persistentes), ai/ (interfaz de IA), vision/ y desktop/ (scaffolds)
  mod_*.py   implementación reutilizada (sistema, voz, audio, git, ...)
```

## Funciones
- Comandos de voz (es-MX) con palabra de activación "Lia"
- Apertura de apps/sitios por aplausos y por voz
- Tareas, notas, recordatorios (persistentes), pomodoro, modo enfoque
- Git, creación de proyectos, apertura de carpetas/proyectos
- Clima, búsquedas, sistema, rutina mañanera, metas/hábitos/proyectos
- GUI (PySide6 + React) desacoplada vía EventBus

## Ejecutar
```bash
pip install -r requirements.txt
cd web && npm install && npm run build   # primera vez (compila la GUI)
python src/main.py
```

Lia arranca aunque falte el micrófono o el audio (modo solo-texto vía GUI).
Los logs van a consola y a `data/lia.log` (rotatorio).

## Pruebas (sin micrófono)
```bash
python scripts/smoke_router.py     # cada comando enruta a la skill correcta
python scripts/smoke_behavior.py   # dispatch + flujo de preguntas pendientes
python scripts/smoke_semantic.py   # recall semántico de la memoria
python scripts/smoke_kernel.py     # construye el kernel completo (audio simulado)
```

## Tecnologías
Python · SpeechRecognition · sounddevice · edge-tts · pygame · PySide6 · React
