#!/usr/bin/env python3
"""
smoke_router.py — Verifica que CADA comando histórico se enruta a la skill
correcta tras la migración (sin tocar micrófono/audio/red).

Construye el IntentRouter con todas las skills reales y comprueba una batería
de frases contra el nombre de intención esperado, incluyendo los casos de
colisión que el diseño anterior resolvía con el orden del if/elif.

Uso:  python scripts/smoke_router.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from core.context import AssistantContext
from core.event_bus import EventBus
from core.router import IntentRouter
from core.skill import SkillRegistry

# Contexto mínimo: el matching solo usa funciones de texto puras.
ctx = AssistantContext(EventBus(), config=None, persona=None, memory=None)
router = IntentRouter(ctx)
n = SkillRegistry().register_all(router, ctx, package_name="skills")

CASOS = [
    ("abre spotify", "apps.abrir"),
    ("abre el proyecto lia", "ws.abrir_proyecto"),
    ("abre documentos", "files.abrir_carpeta"),
    ("abre vscode en miapp", "dev.vscode_en"),
    ("abre maps madrid", "internet.maps"),
    ("a programar", "system.modo_codigo"),
    ("modo estudio", "system.modo_estudio"),
    ("a jugar", "system.modo_juego"),
    ("crea archivo python hola en documentos", "files.crear_archivo"),
    ("crea carpeta x en escritorio", "files.crear_carpeta"),
    ("busca gatos en internet", "files.buscar"),
    ("pendientes", "tasks.pendientes"),
    ("anota comprar pan", "tasks.anotar"),
    ("agrega meta correr 5k", "vida.agregar_meta"),          # colisión con anotar
    ("tarea comprar pan lista", "tasks.completar"),
    ("nota wifi clave1234", "tasks.nota"),
    ("recuerda nota wifi", "tasks.leer_nota"),
    ("pomodoro 30", "prod.pomodoro"),
    ("qué hora es", "prod.hora"),
    ("qué fecha es hoy", "prod.fecha"),
    ("cuánto es 12 por 8", "prod.calcular"),
    ("convierte 100 dólares a pesos", "prod.convertir"),
    ("recuerda llamar a ana en 10 minutos", "rem.minutos"),
    ("recuerda pagar la luz el 15 de julio", "rem.fecha"),
    ("mis recordatorios", "rem.listar"),
    ("recordatorio completado pagar luz", "rem.completar"),
    ("clima", "internet.clima"),
    ("wikipedia einstein", "internet.wikipedia"),
    ("youtube lofi", "internet.youtube"),
    ("mi ip", "internet.ip"),
    ("noticias", "internet.noticias"),
    ("buenos días", "internet.rutina"),
    ("git status", "dev.git_status"),
    ("git push", "dev.git_push"),
    ("nueva rama feature", "dev.nueva_rama"),
    ("clona https://github.com/x/y", "dev.clonar"),
    ("sistema", "system.info"),
    ("disco", "system.disco"),
    ("apaga la pc", "system.apagar"),
    ("cancela apagado", "system.cancelar_apagado"),
    ("modo enfoque 50", "focus.activar"),
    ("mis metas", "vida.metas"),
    ("mis hábitos", "vida.habitos"),
    ("mis proyectos", "vida.proyectos"),
    ("resumen personal", "vida.resumen"),                    # colisión con resumen.dia
    ("resumen", "resumen.dia"),
    ("qué estoy haciendo", "ws.que_hago"),
    ("ejecuta", "ws.ejecutar"),
    ("abre lo último", "ws.abrir_ultimo"),
    ("cierra lo último", "ws.cerrar_ultimo"),
    ("abortar", "ws.abortar"),
    ("cierra todo", "apps.cerrar_todo"),
    ("cierra todo lo que abriste", "ws.abortar"),            # colisión con cerrar_todo
    ("gracias", "control.gracias"),
    ("comandos", "control.ayuda"),
    ("dashboard", "control.dashboard"),
    ("silencio", "control.silencio"),
    ("pausate", "control.pausa"),
    ("ya regresé", "control.reactivar"),
    ("apagate", "control.apagate"),
    ("recalibra", "control.calibrar"),
]

fallos = 0
for frase, esperado in CASOS:
    m = router.match(frase.lower().strip())
    got = m.spec.name if m else "<sin match>"
    estado = "OK " if got == esperado else "FAIL"
    if got != esperado:
        fallos += 1
        print(f"  [{estado}] '{frase}'  ->  {got}   (esperaba {esperado})")

print(f"\nIntenciones totales registradas: {n}")
print(f"Casos probados: {len(CASOS)} | Fallos: {fallos}")
sys.exit(1 if fallos else 0)
