#!/usr/bin/env python3
"""
benchmark.py — Perfilado reproducible de Lia (sin micrófono, audio ni red).

Mide las partes deterministas del pipeline:
  • Arranque de la capa de intenciones (importar + descubrir + registrar skills).
  • Latencia de interpretación (normalización + matching) por comando: avg/p95/max.
  • RAM del proceso tras cargar todo.

NO mide STT/TTS (dependen de red/audio y se observan en vivo con
"rendimiento de Lia"). Pensado para comparar antes/después de un cambio.

Uso:  python scripts/benchmark.py
Escribe también un resumen en data/performance.log.
"""

import datetime
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

# Corpus representativo (mezcla de áreas y de frases naturales con cortesía).
CORPUS = [
    "abre spotify", "pon música", "reproduce spotify", "lanza discord",
    "abre el proyecto lia", "ejecuta", "ejecuta macro modo trabajo",
    "crea alias fluter para abre el proyecto de flutter",
    "qué hora es", "qué fecha es hoy", "cuánto es 12 por 8",
    "a programar", "modo estudio", "git status", "git push", "mis ramas",
    "clima", "wikipedia einstein", "youtube lofi", "noticias", "buenos días",
    "sistema", "disco", "apaga la pc", "sube el volumen", "volumen al 50",
    "pausa la música", "siguiente canción", "qué canción está sonando",
    "recuérdame llamar a ana en 10 minutos", "mis recordatorios",
    "pendientes", "anota comprar pan", "pomodoro 30", "modo enfoque 50",
    "podrías abrir chrome por favor", "necesito que abras vs code",
    "oye lia pon algo de música", "quiero escuchar música",
    "rendimiento de lia", "qué no entendiste", "resumen", "qué hice hoy",
    "abre amazon en internet", "genera contraseña de 20 caracteres",
]


def main():
    # ── 1) Arranque de la capa de intenciones ────────────────────────────────
    t0 = time.perf_counter()
    from core.context import AssistantContext
    from core.event_bus import EventBus
    from core.router import IntentRouter
    from core.skill import SkillRegistry
    from services import perf

    ctx = AssistantContext(EventBus(), config=None, persona=None, memory=None)
    router = IntentRouter(ctx)
    reg = SkillRegistry()
    n = reg.register_all(router, ctx, "skills")
    n += reg.register_all(router, ctx, "plugins")
    arranque_ms = (time.perf_counter() - t0) * 1000.0

    # ── 2) Latencia de interpretación ────────────────────────────────────────
    # Warm-up para no contar el coste de compilación de regex en la 1ª pasada.
    perf.time_routing(router, CORPUS)
    lat = perf.time_routing(router, CORPUS * 20)

    # ── 3) Memoria del proceso ───────────────────────────────────────────────
    snap = perf.snapshot()

    lineas = [
        "================ BENCHMARK LIA ================",
        f"Fecha:                {datetime.datetime.now().isoformat(timespec='seconds')}",
        f"Intenciones:          {n}",
        f"Arranque skills:      {arranque_ms:.1f} ms",
        f"Latencia ruteo (avg): {lat['avg_ms']:.3f} ms",
        f"Latencia ruteo (p95): {lat['p95_ms']:.3f} ms",
        f"Latencia ruteo (max): {lat['max_ms']:.3f} ms",
        f"Comandos medidos:     {lat['n']}",
        f"RAM proceso:          {snap['ram_mb']} MB" if snap["ram_mb"] is not None
        else "RAM proceso:          (psutil no disponible)",
        f"Hilos activos:        {snap['threads']}",
        "===============================================",
    ]
    salida = "\n".join(lineas)
    print(salida)

    try:
        data_dir = os.path.join(_ROOT, "data")
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "performance.log"), "a", encoding="utf-8") as f:
            f.write(salida + "\n")
    except Exception as ex:
        print(f"(No se pudo escribir performance.log: {ex})")


if __name__ == "__main__":
    main()
