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
_registry = SkillRegistry()
n = _registry.register_all(router, ctx, package_name="skills")
n += _registry.register_all(router, ctx, package_name="plugins")

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
    # ── Plugins (v5.1) ─────────────────────────────────────────────────
    ("pausa la música", "musica.pausar"),                    # colisión con control.pausa
    ("pausa", "control.pausa"),                              # exacto sigue pausando a Lia
    ("reproduce música", "musica.reproducir"),
    ("siguiente canción", "musica.siguiente"),
    ("canción anterior", "musica.anterior"),
    ("sube el volumen", "musica.subir_volumen"),
    ("volumen al 50", "musica.volumen_a"),
    ("qué canción está sonando", "musica.cancion_actual"),
    ("quién canta esta canción", "musica.cancion_actual"),
    ("abre mi proyecto actual", "dev.proyecto_actual"),      # colisión con ws.abrir_proyecto
    ("abre la carpeta del proyecto", "dev.carpeta_proyecto"),
    ("abre el proyecto lia", "ws.abrir_proyecto"),           # no debe romperse
    ("ejecuta flutter run", "dev.ejecutar_comando"),
    ("ejecuta npm run dev", "dev.ejecutar_comando"),
    ("ejecuta npm install", "dev.ejecutar_comando"),
    ("abre powershell", "apps.abrir"),
    ("abre android studio", "apps.abrir"),
    ("pausa el pomodoro", "prod.pomodoro_pausar"),           # colisión con control.pausa y prod.pomodoro
    ("cancela el pomodoro", "prod.pomodoro_cancelar"),
    ("reanuda el pomodoro", "prod.pomodoro_reanudar"),
    ("pomodoro 30", "prod.pomodoro"),                        # no debe romperse
    ("agenda mi día", "prod.agenda_dia"),
    ("cuál es mi prioridad", "prod.prioridad"),
    ("qué debería hacer hoy", "prod.prioridad"),
    ("en qué debería enfocarme", "prod.prioridad"),
    ("recuérdame mis objetivos", "prod.objetivos"),          # colisión con rem.fecha
    ("inicia modo profundo", "prod.modo_profundo"),
    ("agrega idea app de recetas", "proy.agregar_idea"),     # colisión con tasks.anotar
    ("recuérdame mis ideas", "proy.listar_ideas"),           # colisión con rem.fecha
    ("lista ideas", "proy.listar_ideas"),
    ("lista proyectos", "proy.listar"),
    ("proyecto activo", "proy.activo"),
    ("cambia proyecto activo a lia", "proy.cambiar_activo"),
    ("agrega examen de física el 20 de junio", "uni.agregar_examen"),
    ("próximos exámenes", "uni.proximos_examenes"),
    ("cuánto falta para el examen", "uni.cuanto_falta"),     # 'para' ya no pausa a Lia
    ("recuerda pagar la luz para mañana", "rem.fecha"),      # 'para' ya no pausa a Lia
    ("agrega tarea estudiar cálculo", "tasks.anotar"),
    ("lista tareas", "tasks.pendientes"),
    ("uso de cpu", "salud.cpu"),                             # colisión con system.info
    ("uso de ram", "salud.ram"),
    ("salud del disco", "salud.disco"),                      # colisión con system.disco
    ("temperatura cpu", "salud.temp_cpu"),
    ("temperatura gpu", "salud.temp_gpu"),
    ("optimiza memoria", "salud.optimizar"),
    ("limpia temporales", "salud.temporales"),
    ("estado del sistema", "system.info"),
    ("abre mi entorno de trabajo", "auto.entorno_trabajo"),  # colisión con apps.abrir
    ("abre entorno flutter", "auto.entorno_flutter"),
    ("abre entorno web", "auto.entorno_web"),
    ("genera contraseña segura", "util.password"),
    ("genera contraseña de 20 caracteres", "util.password"),
    ("apaga la pantalla", "util.apagar_pantalla"),           # colisión con system.apagar
    ("bloquea la pc", "system.bloquear"),
    ("desbloquea sitios", "focus.desactivar"),               # bug corregido en v5.1
    ("busca comando git", "control.buscar_comando"),
    ("qué comandos tienes", "control.ayuda"),
    ("qué puedes hacer", "control.ayuda"),
    # ── Regresión: meta-comandos (alias/macro) que envuelven otros verbos.
    # Antes quedaban "secuestrados" por apps.abrir / ws.* / system.* y la
    # feature era inalcanzable. Auditoría 2026-06: precedencia + guardas.
    ("crea alias fluter para abre el proyecto de flutter", "aliases.crear"),
    ("cuando diga mi correo ejecuta abre gmail", "aliases.crear"),
    ("crea macro modo trabajo", "macros.crear"),
    ("crea una macro que abra vs code y spotify", "macros.crear_inline"),
    ("ejecuta macro modo trabajo", "macros.ejecutar"),
    ("borra macro modo trabajo", "macros.borrar"),
    ("qué hiciste hoy", "history.hoy"),          # no lo secuestra resumen.dia
    ("qué hice hoy", "resumen.dia"),             # dueño oficial del alias
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
