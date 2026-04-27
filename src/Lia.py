#!/usr/bin/env python3

import logging
import logging.handlers
import os
import random
import threading
import time

import speech_recognition as sr

from mod_voz      import VozEngine
from mod_audio    import ClapDetector
from mod_sistema  import SystemTools
from mod_memoria  import MemoryTools
from mod_internet import InternetTools
from mod_dev      import DevTools
from mod_contexto import ContextoConversacional
from mod_vida     import VidaTools

_SRC_DIR          = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR         = os.path.dirname(_SRC_DIR)
COMANDOS_TXT_PATH = os.path.join(_ROOT_DIR, "lia_comandos.txt")
LOG_PATH          = os.path.join(_ROOT_DIR, "lia_errores.log")

_GRACIAS = [
    "Para eso estoy, con gusto.",
    "De nada, cuando quieras.",
    "Es un placer ayudarte.",
    "Sin problema, aquí estaré.",
    "Claro que sí, para eso soy.",
]


def _configurar_logging():
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.WARNING)
    fh.setFormatter(fmt)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(fmt)
    root = logging.getLogger("lia")
    root.setLevel(logging.DEBUG)
    root.addHandler(fh)
    root.addHandler(ch)


logger = logging.getLogger("lia.core")


class LiaAssistant:

    MENU_TEXTO = """
+================================================================+
|                    ASISTENTE LIA  v6.0                         |
+================================================================+
|  APLAUSOS                                                      |
|    1 aplauso   ->  Modo Estudio  (ChatGPT + WhatsApp)          |
|    2 aplausos  ->  Modo Codigo   (VS Code + GitHub + Spotify)  |
|    3 aplausos  ->  Modo Juego    (Discord + TimerResolution)   |
|                                                                |
|  COMANDOS DE VOZ  (di "Lia, ...")                              |
|  -- Control -------------------------------------------------- |
|    "inicio"                    -> Rutina del dia               |
|    "silencio" / "habla"        -> Activa/desactiva voz         |
|    "pausate"                   -> Pausa (3 aplausos p/volver)  |
|    "apagate"                   -> Apaga el asistente           |
|    "abortar"                   -> Cierra lo que abrió el modo  |
|  -- Aplicaciones y Web --------------------------------------- |
|    "abre [app]"                -> Abre app instalada           |
|    "abre [X] en internet"      -> Abre en el navegador         |
|    "cierra todo"               -> Cierra apps de trabajo       |
|  -- Contexto y Proyectos ------------------------------------- |
|    "proyecto [nombre]"         -> Establece proyecto activo    |
|    "abre mi proyecto [nombre]" -> Abre proyecto en VS Code     |
|    "ejecutalo"                 -> Ejecuta el proyecto activo   |
|    "abrir de nuevo"            -> Re-abre lo último            |
|    "cerrar lo último"          -> Cierra el último proceso     |
|    "qué estoy haciendo"        -> Resumen del contexto actual  |
|  -- Búsqueda en carpetas ------------------------------------- |
|    "busca [X] en Documentos"   -> Busca archivo en carpeta     |
|    "busca [X] en Descargas"    -> Busca en Descargas           |
|    "busca [X] en Escritorio"   -> Busca en Escritorio          |
|  -- Pendientes ----------------------------------------------- |
|    "pendientes"                -> Lee tus pendientes           |
|    "anota [tarea]"             -> Agrega pendiente             |
|    "tarea X lista"             -> Marca tarea X como hecha     |
|  -- Metas y Vida --------------------------------------------- |
|    "mis metas"                 -> Lee tus metas de Obsidian    |
|    "agregar meta [X]"          -> Agrega una nueva meta        |
|    "meta [X] completada"       -> Marca meta como completada   |
|    "mis hábitos"               -> Estado de hábitos de hoy     |
|    "hice [hábito]"             -> Marca hábito como hecho      |
|    "agregar hábito [X]"        -> Registra nuevo hábito        |
|    "mis proyectos"             -> Lista proyectos activos      |
|    "agregar proyecto [X]"      -> Registra nuevo proyecto      |
|    "proyecto [X] listo"        -> Marca proyecto como hecho    |
|    "resumen de vida"           -> Resumen de metas y hábitos   |
|  -- Productividad -------------------------------------------- |
|    "pomodoro"                  -> Timer 25 min                 |
|    "pomodoro de [N]"           -> Timer N minutos              |
|    "recuerda [X] en [N] minutos" -> Recordatorio personal      |
|    "clima"                     -> Dice el clima actual         |
|  -- Búsquedas web -------------------------------------------- |
|    "busca [X]"                 -> Busca en Google              |
|    "youtube [X]"               -> Busca en YouTube             |
|  -- Notas rápidas -------------------------------------------- |
|    "nota [clave] [texto]"      -> Guarda nota rapida           |
|    "recuerda nota [clave]"     -> Lee nota guardada            |
|  -- Sistema -------------------------------------------------- |
|    "comandos"                  -> Abre este archivo            |
|    "recalibra"                 -> Recalibra el microfono       |
|    "sistema"                   -> Info de CPU y RAM            |
|    "disco"                     -> Uso del disco                |
|    "bloquea"                   -> Bloquea la PC                |
|    "git status/push/pull"      -> Comandos Git                 |
|  "gracias"                     -> Responde y cierra comandos   |
+================================================================+
"""

    def __init__(self):
        _configurar_logging()
        logger.info("Iniciando Lia v6.0")

        self.is_active       = True
        self._shutdown_flag  = threading.Event()
        self.modo_silencioso = False

        self._voz = VozEngine(rate=175)

        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.recognizer.pause_threshold          = 1.1
        self.recognizer.non_speaking_duration    = 0.6
        self.recognizer.dynamic_energy_threshold = True

        self.sistema  = SystemTools(self)
        self.memoria  = MemoryTools(self)
        self.internet = InternetTools(self)
        self.dev      = DevTools(self)
        self.contexto = ContextoConversacional(self)
        self.vida     = VidaTools(self)

        self.memoria._shutdown_flag = self._shutdown_flag

        self.detector = ClapDetector(on_sequence=self._handle_clap_sequence)

        self._construir_tabla_comandos()

        self.detector.calibrar()
        self._generar_txt_comandos()
        self.hablar("Hola, aquí estoy.")
        self.mostrar_menu()

    def hablar(self, texto: str):
        print(f"🗣️  Lia: {texto}")
        if self.modo_silencioso:
            return
        self._voz.decir(texto)

    def registrar_actividad(self, actividad: str):
        self.memoria.registrar_actividad(actividad)

    def mostrar_menu(self):
        print(self.MENU_TEXTO)

    def _generar_txt_comandos(self):
        try:
            with open(COMANDOS_TXT_PATH, "w", encoding="utf-8") as f:
                f.write(self.MENU_TEXTO)
        except Exception as ex:
            logger.error("No se pudo crear lia_comandos.txt: %s", ex)

    def abrir_comandos_txt(self):
        import subprocess, platform
        try:
            if not os.path.exists(COMANDOS_TXT_PATH):
                self._generar_txt_comandos()
            if platform.system() == "Windows":
                subprocess.Popen(["notepad.exe", COMANDOS_TXT_PATH])
            else:
                subprocess.Popen(["xdg-open", COMANDOS_TXT_PATH])
            self.hablar("Aquí tienes todos mis comandos.")
            self.registrar_actividad("Abrió Comandos.txt")
        except Exception as ex:
            logger.error("Error al abrir comandos.txt: %s", ex)

    def cerrar_comandos_txt(self):
        import subprocess, platform
        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/f", "/im", "notepad.exe"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        except Exception as ex:
            logger.warning("No se pudo cerrar notepad: %s", ex)

    def _handle_clap_sequence(self, count: int):
        logger.debug("Secuencia de aplausos: %d", count)
        if not self.is_active and count >= 3:
            self.is_active = True
            self.detector.set_active(True)
            self.hablar("Sistemas reactivados.")
            return
        if not self.is_active:
            return
        if count == 1:
            self.sistema.modo_estudio()
        elif count == 2:
            self.sistema.modo_programacion()
        elif count >= 3:
            self.sistema.modo_juego()

    def _construir_tabla_comandos(self):
        s = self.sistema
        m = self.memoria
        i = self.internet
        d = self.dev
        c = self.contexto
        v = self.vida

        self._CMD_EXACTOS: dict = {
            "pendientes":           m.decir_pendientes,
            "mis pendientes":       m.decir_pendientes,
            "clima":                i.decir_clima,
            "tiempo":               i.decir_clima,
            "sistema":              s.obtener_info_sistema,
            "cpu":                  s.obtener_info_sistema,
            "ram":                  s.obtener_info_sistema,
            "disco":                s.obtener_uso_disco,
            "bloquea":              s.bloquear_pc,
            "bloquear":             s.bloquear_pc,
            "cierra todo":          s.cerrar_todo,
            "cerrar todo":          s.cerrar_todo,
            "git status":           d.estado_git,
            "estado del repo":      d.estado_git,
            "git push":             d.hacer_push,
            "git pull":             d.hacer_pull,
            "ramas":                d.listar_ramas,
            "comandos":             self.abrir_comandos_txt,
            "ayuda":                self.mostrar_menu,
            "menu":                 self.mostrar_menu,
            "menú":                 self.mostrar_menu,
            "notas":                m.listar_notas,
            "abortar":              c.abortar,
            "abrir de nuevo":       c.abrir_ultimo,
            "cerrar lo último":     c.cerrar_ultimo,
            "qué estoy haciendo":   c.que_estoy_haciendo,
            "que estoy haciendo":   c.que_estoy_haciendo,
            "ejecutalo":            c.ejecutar_ultimo,
            "ejecútalo":            c.ejecutar_ultimo,
            "mis metas":            v.leer_metas,
            "metas":                v.leer_metas,
            "mis hábitos":          v.revisar_habitos,
            "hábitos":              v.revisar_habitos,
            "habitos":              v.revisar_habitos,
            "mis proyectos":        v.estado_proyectos,
            "proyectos":            v.estado_proyectos,
            "resumen de vida":      v.resumen_vida,
            "resumen":              v.resumen_vida,
        }

    def _parse_command(self, cmd: str):
        if not cmd.strip():
            return

        logger.debug("Comando: '%s'", cmd)
        self.contexto.registrar_comando(cmd)

        if "gracias" in cmd:
            self.cerrar_comandos_txt()
            self.hablar(random.choice(_GRACIAS))
            return

        if any(k in cmd for k in ("inicio", "rutina", "buenos días", "buen día")):
            self.internet.rutina_inicio()
            return

        if "silencio" in cmd:
            self.modo_silencioso = True
            print("🔇 Modo silencioso activado.")
            return

        if "habla" in cmd or "activa voz" in cmd:
            self.modo_silencioso = False
            self.hablar("Voz reactivada.")
            return

        if "pausate" in cmd or cmd == "pausa":
            self.is_active = False
            self.detector.set_active(False)
            self.hablar("Pausada. Da 3 aplausos para volver.")
            return

        if "apagate" in cmd or "apagar" in cmd:
            self.hablar("Apagando. Hasta luego.")
            self._shutdown_flag.set()
            return

        if "apaga la pc" in cmd or "apaga el pc" in cmd:
            self.sistema.apagar_pc(segundos=60)
            return

        if "cancela apagado" in cmd:
            self.sistema.cancelar_apagado()
            return

        # ── "abre X en internet" → fuerza apertura web ──────────────────────
        if " en internet" in cmd or " en el navegador" in cmd or " en web" in cmd:
            nombre = (cmd
                      .replace(" en internet", "")
                      .replace(" en el navegador", "")
                      .replace(" en web", ""))
            for trigger in ("abre ", "abrir "):
                if trigger in nombre:
                    nombre = nombre.split(trigger, 1)[-1].strip()
                    break
            self.sistema.abrir_web(nombre.strip())
            return

        # ── "abre X" → app primero, si no encuentra → web ───────────────────
        for trigger in ("abre ", "abrir "):
            if trigger in cmd:
                objetivo = cmd.split(trigger, 1)[-1].strip()
                if objetivo:
                    self.sistema.open_application(objetivo)
                else:
                    self.hablar("¿Qué quieres que abra?")
                return

        # ── Búsqueda en carpeta: "busca X en Documentos" ────────────────────
        carpetas_conocidas = list(self.sistema.CARPETAS_MAP.keys())
        if any(k in cmd for k in ("busca ", "buscar ")):
            for carpeta in carpetas_conocidas:
                if f" en {carpeta}" in cmd:
                    termino = (cmd
                               .replace("busca ", "")
                               .replace("buscar ", "")
                               .replace(f" en {carpeta}", "")
                               .strip())
                    self.sistema.buscar_en_carpeta(termino, carpeta)
                    return

        # ── Contexto: proyecto ───────────────────────────────────────────────
        if "abre mi proyecto" in cmd or "abrir mi proyecto" in cmd:
            nombre = (cmd.replace("abre mi proyecto", "")
                        .replace("abrir mi proyecto", "")
                        .strip())
            if nombre:
                self.contexto.abrir_proyecto(nombre)
            else:
                self.hablar("¿Qué proyecto quieres abrir?")
            return

        if cmd.startswith("proyecto ") and "listo" not in cmd and "completado" not in cmd:
            nombre = cmd.replace("proyecto", "", 1).strip()
            if nombre:
                self.contexto.establecer_proyecto(nombre)
            return

        # ── Vida: metas ──────────────────────────────────────────────────────
        if "agregar meta" in cmd or "nueva meta" in cmd:
            texto = (cmd.replace("agregar meta", "")
                       .replace("nueva meta", "")
                       .strip().strip(",.-: "))
            self.vida.agregar_meta(texto) if texto else self.hablar("¿Cuál es la meta?")
            return

        for kw in ("meta", "objetivo"):
            if kw in cmd and any(k in cmd for k in ("completada", "lograda", "lista", "hecha")):
                texto = cmd
                for k in ("meta", "objetivo", "completada", "lograda", "lista", "hecha"):
                    texto = texto.replace(k, "")
                self.vida.completar_meta(texto.strip().strip(",.-: "))
                return

        # ── Vida: hábitos ────────────────────────────────────────────────────
        if "agregar hábito" in cmd or "agregar habito" in cmd or "nuevo hábito" in cmd:
            texto = (cmd.replace("agregar hábito", "")
                       .replace("agregar habito", "")
                       .replace("nuevo hábito", "")
                       .strip().strip(",.-: "))
            self.vida.agregar_habito(texto) if texto else self.hablar("¿Cuál es el hábito?")
            return

        if cmd.startswith("hice ") or "completé el hábito" in cmd:
            habito = (cmd.replace("hice", "")
                        .replace("completé el hábito", "")
                        .strip().strip(",.-: "))
            self.vida.marcar_habito(habito) if habito else self.hablar("¿Qué hábito completaste?")
            return

        # ── Vida: proyectos ──────────────────────────────────────────────────
        if "agregar proyecto" in cmd or "nuevo proyecto" in cmd:
            texto = (cmd.replace("agregar proyecto", "")
                       .replace("nuevo proyecto", "")
                       .strip().strip(",.-: "))
            self.vida.agregar_proyecto(texto) if texto else self.hablar("¿Cuál es el proyecto?")
            return

        if "proyecto" in cmd and any(k in cmd for k in ("listo", "completado", "terminado", "hecho")):
            texto = cmd
            for k in ("proyecto", "listo", "completado", "terminado", "hecho"):
                texto = texto.replace(k, "")
            self.vida.completar_proyecto(texto.strip().strip(",.-: "))
            return

        # ── Pendientes ───────────────────────────────────────────────────────
        if cmd.strip() == "pendientes" or "mis pendientes" in cmd or (
            "pendientes" in cmd and not any(k in cmd for k in ("anota", "tarea", "agreg"))
        ):
            self.memoria.decir_pendientes()
            return

        for verbo in ("anota", "apunta", "agrega pendiente", "agrega"):
            if verbo in cmd:
                texto = cmd.split(verbo, 1)[-1].strip().strip(",.-: ")
                self.memoria.agregar_pendiente(texto) if texto else self.hablar("¿Qué quieres que anote?")
                return

        for kw in ("lista", "completada", "hecha", "terminada", "completa"):
            if kw in cmd and "tarea" in cmd:
                tarea = cmd.replace("tarea", "").replace(kw, "").strip().strip(",.-: ")
                self.memoria.completar_tarea(tarea)
                return

        # ── Notas rápidas ────────────────────────────────────────────────────
        if cmd.startswith("nota "):
            partes = cmd[5:].strip().split(" ", 1)
            if len(partes) == 2:
                self.memoria.guardar_nota(partes[0], partes[1])
            else:
                self.hablar("Di: nota [clave] [contenido].")
            return

        if "recuerda nota " in cmd:
            self.memoria.obtener_nota(cmd.split("recuerda nota ", 1)[-1].strip())
            return

        # ── Pomodoro ─────────────────────────────────────────────────────────
        if "pomodoro" in cmd:
            minutos = 25
            for p in cmd.split():
                if p.isdigit():
                    minutos = int(p)
                    break
            self.memoria.iniciar_pomodoro(minutos)
            return

        # ── Recordatorio ─────────────────────────────────────────────────────
        if "recuerda" in cmd and " en " in cmd and "nota" not in cmd:
            try:
                partes  = cmd.split(" en ", 1)
                mensaje = partes[0].replace("recuerda", "").strip()
                mins    = float("".join(c for c in partes[1] if c.isdigit() or c == ".") or "5")
                self.memoria.recordar_en(mensaje, mins)
            except Exception as ex:
                logger.warning("Error al parsear recordatorio: %s", ex)
                self.hablar("No entendí el recordatorio.")
            return

        # ── Búsquedas web ────────────────────────────────────────────────────
        for trigger in ("busca ", "buscar "):
            if trigger in cmd:
                q = cmd.split(trigger, 1)[-1].strip()
                self.internet.buscar_google(q) if q else self.hablar("¿Qué quieres buscar?")
                return

        if "youtube " in cmd:
            q = cmd.split("youtube ", 1)[-1].strip()
            self.internet.buscar_youtube(q) if q else self.hablar("¿Qué quieres buscar en YouTube?")
            return

        # ── Recalibración ────────────────────────────────────────────────────
        if "recalibra" in cmd or "calibra" in cmd:
            self.detector.calibrar()
            return

        # ── Tabla de comandos exactos ────────────────────────────────────────
        fn = self._CMD_EXACTOS.get(cmd.strip())
        if fn:
            try:
                fn()
            except Exception as ex:
                logger.error("Error ejecutando '%s': %s", cmd, ex)
                self.hablar("Hubo un error al ejecutar ese comando.")
            return

        logger.debug("Comando no reconocido: '%s'", cmd)

    def _listen_loop(self):
        with self.microphone as src:
            self.recognizer.adjust_for_ambient_noise(src, duration=1.0)
            logger.info("Reconocimiento de voz listo.")
            print("✅ Listo para comandos de voz.\n")

            while not self._shutdown_flag.is_set():
                if self._voz.hablando:
                    time.sleep(0.1)
                    continue
                if not self.is_active:
                    time.sleep(0.4)
                    continue
                try:
                    audio = self.recognizer.listen(src, timeout=None, phrase_time_limit=8)
                    if self._voz.hablando:
                        continue
                    cmd = self.recognizer.recognize_google(audio, language="es-MX").lower()
                    print(f"🎤 Escuché: '{cmd}'")
                    logger.debug("Reconocido: '%s'", cmd)

                    if "gracias" in cmd:
                        self.cerrar_comandos_txt()
                        self.hablar(random.choice(_GRACIAS))
                        continue

                    if cmd.strip() in ("lia", "lía"):
                        continue

                    if "lia" in cmd or "lía" in cmd:
                        limpio = (cmd
                                  .replace("lía,", "").replace("lia,", "")
                                  .replace("lía", "").replace("lia", "")
                                  .strip().strip(",. "))
                        if limpio:
                            self._parse_command(limpio)

                except sr.UnknownValueError:
                    pass
                except sr.RequestError as ex:
                    logger.error("Error de reconocimiento de voz: %s", ex)
                except Exception as ex:
                    logger.exception("Error inesperado en _listen_loop: %s", ex)
                    time.sleep(0.5)

    def run(self):
        voz = threading.Thread(target=self._listen_loop, daemon=True, name="LiaVoz")
        voz.start()
        try:
            self.detector.start_loop(shutdown_flag=self._shutdown_flag)
        except KeyboardInterrupt:
            print("\n👋 Lia detenida.")
        finally:
            self._shutdown_flag.set()
            self._voz.detener()
            logger.info("Lia apagada.")


if __name__ == "__main__":
    print("""
+=======================================+
|       ASISTENTE  LIA  v4.3.0          |
+=======================================+
""")
    LiaAssistant().run()