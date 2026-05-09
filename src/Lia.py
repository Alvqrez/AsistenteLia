#!/usr/bin/env python3

import os
import sys as _sys
import threading
import time

import speech_recognition as sr

from mod_audio         import ClapDetector
from mod_sistema       import SystemTools
from mod_sistema_extra import FileOpsTools
from mod_memoria       import MemoryTools
from mod_internet      import InternetTools
from mod_dev           import DevTools
from mod_voz           import VozEngine
from mod_personalidad  import Persona
from mod_productividad import ProductividadTools
from mod_focus         import FocusTools
from mod_resumen       import ResumenTools

_SRC_DIR          = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = _sys._MEIPASS if getattr(_sys, "frozen", False) else os.path.dirname(_SRC_DIR)
COMANDOS_TXT_PATH = os.path.join(_ROOT_DIR, "lia_comandos.txt")

# ── Sinónimos ──────────────────────────────────────────────────────────────────
_SINONIMOS_VSCODE = {
    "necesito programar", "quiero programar", "a programar",
    "vscode", "vs code", "visual studio", "código", "editor",
    "modo código", "modo programacion", "a codear", "codear",
    "abre el editor", "entorno de desarrollo", "ayúdame a programar",
    "quiero codear", "vamos a programar", "modo dev", "programemos",
}
_SINONIMOS_ESTUDIO = {
    "modo estudio", "a estudiar", "necesito estudiar",
    "quiero estudiar", "tiempo de estudiar", "hora de estudiar",
    "a trabajar", "modo trabajo", "chatgpt y whatsapp",
    "voy a estudiar", "voy a trabajar", "hora de trabajar",
    "modo concentración", "modo concentracion",
}
_SINONIMOS_JUEGO = {
    "modo juego", "a jugar", "quiero jugar", "hora de jugar",
    "gaming", "videojuegos", "necesito discord", "abre discord",
    "vamos a jugar", "quiero relajarme jugando", "hora de gaming",
}
_SINONIMOS_PENDIENTES = {
    "pendientes", "mis pendientes", "qué tengo pendiente",
    "que tengo pendiente", "mis tareas", "lista de tareas",
    "qué debo hacer", "que debo hacer", "qué tengo que hacer",
    "que tengo que hacer", "dime mis pendientes", "mis compromisos",
    "en qué andaba", "en que andaba",
}
_SINONIMOS_CLIMA = {
    "clima", "tiempo", "cómo está el clima", "como esta el clima",
    "qué temperatura hace", "que temperatura hace",
    "va a llover", "llueve hoy", "hace frío", "hace calor",
    "cómo está el tiempo", "como esta el tiempo",
    "clima de hoy", "qué clima hay", "que clima hay",
}
_SINONIMOS_INICIO = {
    "inicio", "rutina", "buenos días", "buen día", "buenas",
    "empecemos", "comencemos", "arranquemos el día",
    "empezar el día", "empezar el dia", "arrancamos",
    "buenos días lia", "hola lia", "qué hay de nuevo",
    "que hay de nuevo", "cómo va todo", "como va todo",
}
_SINONIMOS_SISTEMA = {
    "sistema", "cpu", "ram", "recursos", "cómo está la pc",
    "como esta la pc", "uso del sistema", "rendimiento",
    "cómo anda la pc", "como anda la pc", "cómo está el equipo",
    "como esta el equipo", "cómo estoy de memoria", "como estoy de memoria",
}
_SINONIMOS_PAUSA = {
    "pausate", "pausa", "detente", "para", "descansa",
    "modo descanso", "silencia los aplausos", "voy a descansar",
    "voy a dormir", "tengo sueño", "me voy un momento",
    "espérate", "esperate", "un momento",
}
_SINONIMOS_SILENCIO_VOZ = {
    "silencio", "cállate", "callate", "modo silencioso",
    "sin voz", "no hables", "mute", "ya no hables",
    "deja de hablar", "silencia tu voz",
}
_SINONIMOS_DISCO = {
    "disco", "espacio", "espacio libre", "cuánto disco", "cuanto disco",
    "cuánto espacio", "cuanto espacio", "espacio en disco",
    "cuánto me queda", "cuanto me queda",
}
_SINONIMOS_HORA = {
    "qué hora", "que hora", "la hora", "dime la hora",
    "qué horas son", "que horas son", "tienes hora",
}
_SINONIMOS_FECHA = {
    "qué fecha", "que fecha", "qué día es", "que dia es",
    "hoy es", "qué día es hoy", "que dia es hoy",
    "cuándo es hoy", "cuando es hoy",
}


def _coincide(cmd: str, sinonimos: set) -> bool:
    cmd_l = cmd.lower()
    return any(s in cmd_l for s in sinonimos)


# ── SystemTools extendido con FileOpsTools ────────────────────────────────────
class ExtendedSystemTools(FileOpsTools, SystemTools):
    """Combina SystemTools con las operaciones de archivo/carpeta."""
    pass


class LiaAssistant:

    MENU_TEXTO = """\
+==============================================================+
|                   ASISTENTE LIA  v4.6.0                      |
+==============================================================+
|  APLAUSOS                                                     |
|    1 aplauso   ->  Modo Estudio  (ChatGPT + WhatsApp)        |
|    2 aplausos  ->  Modo Codigo   (VS Code + GitHub + Spotify)|
|    3 aplausos  ->  Modo Juego    (Discord + TimerResolution) |
|                                                               |
|  COMANDOS DE VOZ  (di "Lia, ...")                             |
|  -- Modos --------------------------------------------------- |
|    "a estudiar" / "modo estudio" / "voy a trabajar"          |
|    "a programar" / "modo código" / "quiero codear"           |
|    "a jugar" / "gaming" / "modo juego"                       |
|  -- Rutina -------------------------------------------------- |
|    "inicio" / "buenos días" / "empecemos"                    |
|  -- Voz y control ------------------------------------------ |
|    "silencio" / "cállate" / "mute"                           |
|    "habla" / "activa voz"                                     |
|    "pausate" / "voy a descansar"                              |
|    "ya regresé" / "ya volví"  (reactivar desde pausa)        |
|    "apagate"                                                  |
|    "cancela"  (cancela la pregunta pendiente)                |
|  -- Aplicaciones ------------------------------------------- |
|    "abre [app]"                                              |
|    "cierra todo"                                             |
|  -- Archivos y carpetas ------------------------------------ |
|    "crea archivo python [nombre] en [carpeta]"               |
|    "crea archivo js/html/txt/json [nombre] en [carpeta]"     |
|    "crea carpeta [nombre] en [carpeta]"                      |
|    "abre carpeta [nombre]" / "abre documentos/descargas"     |
|    "busca [término] en [carpeta]"                            |
|  -- Pendientes --------------------------------------------- |
|    "pendientes" / "mis tareas" / "qué debo hacer"            |
|    "anota [tarea]" / "apunta [tarea]"                        |
|    "tarea X lista"                                           |
|  -- Notas -------------------------------------------------- |
|    "nota [clave] [texto]"                                    |
|    "recuerda nota [clave]"                                   |
|  -- Dev ---------------------------------------------------- |
|    "crea proyecto React en [carpeta]"                        |
|    "git status / push / pull / log"                          |
|    "nueva rama [nombre]" / "cambia rama [nombre]"            |
|    "clona [url]"                                             |
|    "abre vscode en [carpeta]"                                |
|    "docs python" / "mdn" / "stackoverflow"                   |
|  -- Productividad ------------------------------------------ |
|    "pomodoro [N]" / "temporizador [N] minutos"               |
|    "recuerda [X] en [N] minutos"                             |
|    "qué hora" / "qué fecha"                                  |
|    "calcula [operación]" / "cuánto es X por Y"               |
|    "convierte [N] [unidad] a [unidad]"                       |
|  -- Clima e internet --------------------------------------- |
|    "clima" / "va a llover"                                   |
|    "busca [X]" / "youtube [X]" / "wikipedia [X]"             |
|    "maps [lugar]" / "abre maps [lugar]"                      |
|    "mi ip" / "hay internet"                                  |
|    "noticias"                                                |
|    "traduce [texto]"                                         |
|  -- Sistema ------------------------------------------------ |
|    "sistema" / "cpu" / "rendimiento"                         |
|    "disco" / "cuánto espacio libre"                          |
|    "procesos pesados"                                        |
|    "bloquea" / "apaga la pc" / "cancela apagado"             |
|  -- Modo Enfoque ------------------------------------------- |
|    "modo enfoque [N]" / "desbloquea sitios"                  |
|  -- Misc --------------------------------------------------- |
|    "resumen" / "qué hice hoy"                                |
|    "comandos" / "ayuda"                                      |
|    "gracias"                                                 |
|    "recalibra" (recalibra el micrófono)                      |
+==============================================================+
"""

    def __init__(self):
        self.is_active       = True
        self._shutdown_flag  = threading.Event()
        self._gui_window     = None

        # Acción pendiente: Lia espera un dato extra del usuario
        # {"tipo": str, "params": dict, "pregunta": str}
        self._pending_action = None

        self.persona = Persona(nombre="Leonardo")

        self.voz = VozEngine(
            on_speak_start=lambda: self.detector.set_lia_hablando(True)
                           if hasattr(self, 'detector') else None,
            on_speak_end=lambda: self.detector.set_lia_hablando(False)
                         if hasattr(self, 'detector') else None,
        )

        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        # Umbral de energía más alto para no reaccionar a teclas o ruido leve
        self.recognizer.energy_threshold          = 400
        self.recognizer.dynamic_energy_threshold  = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.pause_threshold           = 1.1
        self.recognizer.non_speaking_duration     = 0.6

        self.sistema       = ExtendedSystemTools(self)
        self.memoria       = MemoryTools(self)
        self.internet      = InternetTools(self)
        self.dev           = DevTools(self)
        self.productividad = ProductividadTools(self)
        self.focus         = FocusTools(self)
        self.resumen       = ResumenTools(self)

        self.memoria._shutdown_flag = self._shutdown_flag

        self.detector = ClapDetector(on_sequence=self._handle_clap_sequence)

        self.detector.calibrar()
        self._generar_txt_comandos()
        self.hablar(self.persona.saludo_inicio())

    # ── Interfaz base ─────────────────────────────────────────────────────────

    def hablar(self, texto: str):
        print(f"Lia: {texto}")
        if self._gui_window:
            try:
                self._gui_window.signal_log.emit(f"🗣 {texto}")
            except Exception:
                pass
        self.voz.decir(texto)

    def registrar_actividad(self, actividad: str):
        self.memoria.registrar_actividad(actividad)
        if self._gui_window:
            try:
                self._gui_window.signal_log.emit(f"✓ {actividad}")
            except Exception:
                pass

    def mostrar_menu(self):
        pass

    def _generar_txt_comandos(self):
        try:
            with open(COMANDOS_TXT_PATH, "w", encoding="utf-8") as f:
                f.write(self.MENU_TEXTO)
        except Exception as ex:
            print(f"No se pudo crear lia_comandos.txt: {ex}")

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
            print(f"Error al abrir comandos: {ex}")

    def cerrar_comandos_txt(self):
        import subprocess, platform
        try:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/f", "/im", "notepad.exe"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    # ── Aplausos ──────────────────────────────────────────────────────────────

    def _handle_clap_sequence(self, count: int):
        import json
        # CORRECCIÓN: ruta era "../lia_modos.json" — incorrecto si se renombró la carpeta
        modos_path = os.path.join(_ROOT_DIR, "lia_modos.json")
        modos = []
        try:
            if os.path.exists(modos_path):
                with open(modos_path, "r", encoding="utf-8") as f:
                    modos = json.load(f).get("modos", [])
        except Exception:
            pass

        if not self.is_active and count >= 3:
            self.is_active = True
            self.detector.set_active(True)
            self.hablar(self.persona.reactivacion())
            if self._gui_window:
                self._gui_window.signal_status.emit("activa")
            return

        if not self.is_active:
            return

        modo = next((m for m in modos if m.get("aplausos") == count), None)
        accion = modo.get("accion", "") if modo else ""

        if accion == "modo_estudio" or count == 1:
            self.sistema.modo_estudio()
        elif accion == "modo_programacion" or count == 2:
            self.sistema.modo_programacion()
        elif count >= 3:
            self.sistema.modo_juego()

    # ── Sistema de preguntas pendientes ───────────────────────────────────────

    def _pedir(self, tipo: str, params: dict, pregunta: str):
        """Guarda una acción incompleta y hace la pregunta al usuario."""
        self._pending_action = {"tipo": tipo, "params": params}
        self.hablar(pregunta)

    def _resolver_pendiente(self, respuesta: str):
        """Completa la acción pendiente con la respuesta del usuario."""
        accion = self._pending_action
        self._pending_action = None

        resp_l = respuesta.lower().strip()

        # Cancelar
        if any(w in resp_l for w in ("cancela", "olvida", "nada", "no importa",
                                      "déjalo", "dejalo", "cancel")):
            self.hablar("Entendido, cancelado.")
            return

        tipo   = accion["tipo"]
        params = accion["params"]

        if tipo == "crear_archivo":
            params["carpeta"] = respuesta.strip()
            self.sistema.crear_archivo(**params)

        elif tipo == "crear_carpeta":
            params["ruta_padre"] = respuesta.strip()
            self.sistema.crear_carpeta(**params)

        elif tipo == "proyecto_react":
            self.dev.crear_proyecto_react(respuesta.strip())

        elif tipo == "crear_archivo_nombre":
            # Ya tenemos carpeta, falta nombre
            params["nombre"] = respuesta.strip()
            self.sistema.crear_archivo(**params)

        elif tipo == "abrir_carpeta":
            self.sistema.abrir_carpeta_conocida(respuesta.strip())

        elif tipo == "buscar_carpeta":
            params["nombre_carpeta"] = respuesta.strip()
            self.sistema.buscar_en_carpeta(**params)

        elif tipo == "git_push_rama":
            self.dev.hacer_push(rama=respuesta.strip())

        elif tipo == "nueva_rama":
            self.dev.crear_rama(respuesta.strip())

        elif tipo == "cambiar_rama":
            self.dev.cambiar_rama(respuesta.strip())

        elif tipo == "clonar_repo":
            self.dev.clonar_repositorio(respuesta.strip())

        elif tipo == "pomodoro_minutos":
            try:
                minutos = int("".join(c for c in respuesta if c.isdigit()) or "25")
            except Exception:
                minutos = 25
            self.memoria.iniciar_pomodoro(minutos)

        elif tipo == "abrir_app":
            self.sistema.open_application(respuesta.strip())

        else:
            self.hablar(f"No supe qué hacer con '{respuesta}'.")

    # ── Parser principal ──────────────────────────────────────────────────────

    def _parse_command(self, cmd: str):
        if not cmd.strip():
            return

        # Si hay una acción pendiente, la respuesta del usuario la completa
        if self._pending_action:
            self._resolver_pendiente(cmd)
            return

        cmd_l = cmd.lower().strip()

        # ── Cancelar explícito ────────────────────────────────────────────────
        if cmd_l in ("cancela", "cancel", "olvídalo", "olvidalo", "no importa"):
            self.hablar("No hay ninguna acción pendiente.")
            return

        # ── Saludos / agradecimientos ─────────────────────────────────────────
        if "gracias" in cmd_l:
            self.cerrar_comandos_txt()
            self.hablar(self.persona.gracias())
            return

        # ── Comandos / ayuda ──────────────────────────────────────────────────
        if any(w in cmd_l for w in ("comandos", "ayuda", "menú", "menu", "qué puedes hacer",
                                     "que puedes hacer", "qué sabes hacer", "que sabes hacer")):
            self.abrir_comandos_txt()
            return

        # ── Rutina de inicio ──────────────────────────────────────────────────
        if _coincide(cmd_l, _SINONIMOS_INICIO):
            self.internet.rutina_inicio()
            return

        # ── Voz ───────────────────────────────────────────────────────────────
        if _coincide(cmd_l, _SINONIMOS_SILENCIO_VOZ):
            self.voz.set_silencioso(True)
            print("Modo silencioso activado.")
            return

        if any(w in cmd_l for w in ("habla", "activa voz", "voz normal", "ya puedes hablar")):
            self.voz.set_silencioso(False)
            self.hablar(self.persona.voz_reactivada())
            return

        # ── Pausa / reactivación ──────────────────────────────────────────────
        if _coincide(cmd_l, _SINONIMOS_PAUSA):
            self.is_active = False
            self.detector.set_active(False)
            self.hablar(self.persona.pausa())
            if self._gui_window:
                self._gui_window.signal_status.emit("pausada")
            return

        if any(w in cmd_l for w in ("ya regresé", "ya regrese", "ya volví", "ya volvi",
                                     "estoy de vuelta", "aquí estoy", "aqui estoy")):
            if not self.is_active:
                self.is_active = True
                self.detector.set_active(True)
                self.hablar(self.persona.reactivacion())
                if self._gui_window:
                    self._gui_window.signal_status.emit("activa")
            else:
                self.hablar(self.persona.saludo_corto())
            return

        if any(w in cmd_l for w in ("apagate", "apagar lia", "ciérrate", "cierrate",
                                     "hasta luego", "hasta mañana", "hasta manana",
                                     "chao lia", "adiós lia", "adios lia")):
            self.hablar(self.persona.apagado())
            self._shutdown_flag.set()
            if self._gui_window:
                self._gui_window.signal_status.emit("apagada")
            return

        # ── Modos ─────────────────────────────────────────────────────────────
        if _coincide(cmd_l, _SINONIMOS_VSCODE) and "abre" not in cmd_l:
            self.sistema.modo_programacion()
            return

        if _coincide(cmd_l, _SINONIMOS_ESTUDIO) and "abre" not in cmd_l:
            self.sistema.modo_estudio()
            return

        if _coincide(cmd_l, _SINONIMOS_JUEGO) and "abre" not in cmd_l:
            self.sistema.modo_juego()
            return

        # ── Archivos ──────────────────────────────────────────────────────────
        # "crea archivo python hola en documentos"
        # "crea un archivo js en escritorio"
        # "nuevo archivo html"
        if any(kw in cmd_l for kw in ("crea archivo", "crea un archivo",
                                        "nuevo archivo", "crear archivo")):
            self._cmd_crear_archivo(cmd_l)
            return

        # ── Carpetas ──────────────────────────────────────────────────────────
        if any(kw in cmd_l for kw in ("crea carpeta", "crea una carpeta",
                                        "nueva carpeta", "crear carpeta")):
            self._cmd_crear_carpeta(cmd_l)
            return

        if any(kw in cmd_l for kw in ("abre carpeta", "abrir carpeta",
                                        "abre la carpeta", "abre mis documentos",
                                        "abre documentos", "abre descargas",
                                        "abre el escritorio", "abre escritorio",
                                        "abre imágenes", "abre imagenes")):
            self._cmd_abrir_carpeta(cmd_l)
            return

        # ── Buscar en carpeta ─────────────────────────────────────────────────
        # "busca proyecto en documentos" / "encuentra factura en descargas"
        if ("busca " in cmd_l or "encuentra " in cmd_l or "buscar " in cmd_l) and " en " in cmd_l:
            self._cmd_buscar_carpeta(cmd_l)
            return

        # ── Proyecto React ────────────────────────────────────────────────────
        if "proyecto react" in cmd_l or "proyecto de react" in cmd_l:
            for kw in ("crea proyecto react en ", "crear proyecto react en ",
                       "crea proyecto de react en ", "crea proyecto react ",
                       "crear proyecto react ", "nuevo proyecto react en ",
                       "nuevo proyecto react "):
                if kw in cmd_l:
                    nombre = cmd_l.split(kw, 1)[-1].strip()
                    if nombre:
                        self.dev.crear_proyecto_react(nombre)
                    else:
                        self._pedir("proyecto_react", {},
                                    "¿Cómo se va a llamar el proyecto React?")
                    return
            self._pedir("proyecto_react", {}, "¿Cómo se va a llamar el proyecto React?")
            return

        # ── Abrir aplicación ──────────────────────────────────────────────────
        if "abre " in cmd_l or "abrir " in cmd_l:
            for trigger in ("abre ", "abrir "):
                if trigger in cmd_l:
                    app = cmd_l.split(trigger, 1)[-1].strip()
                    if app:
                        self.sistema.open_application(app)
                    else:
                        self._pedir("abrir_app", {}, "¿Qué aplicación quieres que abra?")
                    return

        if "cierra todo" in cmd_l or "cerrar todo" in cmd_l or "ciérralo todo" in cmd_l:
            self.sistema.cerrar_todo()
            return

        # ── Pendientes ────────────────────────────────────────────────────────
        if _coincide(cmd_l, _SINONIMOS_PENDIENTES):
            self.memoria.decir_pendientes()
            return

        for verbo in ("anota", "apunta", "agrega pendiente", "agrega tarea",
                       "agrega", "añade pendiente", "añade"):
            if verbo in cmd_l:
                texto = cmd_l.split(verbo, 1)[-1].strip().strip(",.-: ")
                if texto:
                    self.memoria.agregar_pendiente(texto)
                else:
                    self.hablar("¿Qué quieres que anote?")
                return

        for kw in ("lista", "completada", "hecha", "terminada", "completa", "done"):
            if kw in cmd_l and ("tarea" in cmd_l or "pendiente" in cmd_l):
                tarea = (cmd_l.replace("tarea", "").replace("pendiente", "")
                              .replace(kw, "").strip().strip(",.-: "))
                self.memoria.completar_tarea(tarea)
                return

        # ── Notas ─────────────────────────────────────────────────────────────
        if cmd_l.startswith("nota "):
            partes = cmd_l[5:].strip().split(" ", 1)
            if len(partes) == 2:
                self.memoria.guardar_nota(partes[0], partes[1])
            else:
                self.hablar("Di: nota [clave] [contenido].")
            return

        if "recuerda nota " in cmd_l or "lee nota " in cmd_l:
            clave = (cmd_l.replace("recuerda nota", "").replace("lee nota", "").strip())
            self.memoria.obtener_nota(clave)
            return

        if "lista notas" in cmd_l or "mis notas" in cmd_l:
            self.memoria.listar_notas()
            return

        # ── Pomodoro / temporizador ───────────────────────────────────────────
        if any(w in cmd_l for w in ("pomodoro", "temporizador", "cronómetro",
                                     "cronometro", "enciende el pomodoro",
                                     "inicia el pomodoro", "empieza el pomodoro")):
            minutos = 25
            for p in cmd_l.split():
                if p.isdigit():
                    minutos = int(p)
                    break
            self.memoria.iniciar_pomodoro(minutos)
            return

        # ── Recordatorio ─────────────────────────────────────────────────────
        # "recuerda [X] en [N] minutos" / "en [N] minutos recuérdame [X]"
        if ("recuerda" in cmd_l or "recuérdame" in cmd_l or "recuerdame" in cmd_l) \
                and (" en " in cmd_l or " minutos" in cmd_l):
            self._cmd_recordatorio(cmd_l)
            return

        # ── Clima ─────────────────────────────────────────────────────────────
        if _coincide(cmd_l, _SINONIMOS_CLIMA):
            self.internet.decir_clima()
            return

        # ── Búsquedas ─────────────────────────────────────────────────────────
        if "wikipedia" in cmd_l or "busca en wikipedia" in cmd_l:
            consulta = (cmd_l.replace("busca en wikipedia", "")
                             .replace("wikipedia", "").strip())
            if consulta:
                self.internet.buscar_wikipedia(consulta)
            else:
                self.hablar("¿Qué quieres buscar en Wikipedia?")
            return

        if "youtube " in cmd_l or "busca en youtube " in cmd_l:
            consulta = (cmd_l.replace("busca en youtube", "")
                             .replace("youtube", "").strip())
            if consulta:
                self.internet.buscar_youtube(consulta)
            return

        if "traduce " in cmd_l or "traducir " in cmd_l or "cómo se dice" in cmd_l:
            consulta = (cmd_l.replace("traduce", "").replace("traducir", "")
                             .replace("cómo se dice", "").strip())
            if consulta:
                import webbrowser, urllib.parse
                webbrowser.open(f"https://translate.google.com/?text={urllib.parse.quote(consulta)}")
                self.hablar(f"Buscando traducción de '{consulta}'.")
            else:
                self.internet.abrir_traductor()
            return

        if "maps " in cmd_l or "abre maps" in cmd_l or "google maps" in cmd_l:
            lugar = (cmd_l.replace("abre maps", "").replace("google maps", "")
                          .replace("maps", "").strip())
            self.internet.abrir_maps(lugar if lugar else None)
            return

        if "mi ip" in cmd_l or "ip pública" in cmd_l or "ip publica" in cmd_l:
            self.internet.obtener_ip_publica()
            return

        if any(w in cmd_l for w in ("hay internet", "tengo conexión", "tengo conexion",
                                     "hay conexión", "hay conexion", "checa internet")):
            self.internet.verificar_conexion()
            return

        if "noticias" in cmd_l:
            self.internet.abrir_noticias()
            return

        if "busca " in cmd_l or "buscar " in cmd_l:
            consulta = cmd_l.replace("busca", "").replace("buscar", "").strip()
            if consulta:
                self.internet.buscar_google(consulta)
            return

        # ── Recalibrar micrófono ──────────────────────────────────────────────
        if "recalibra" in cmd_l or ("calibra" in cmd_l and "micro" in cmd_l):
            self.detector.calibrar()
            self.hablar("Micrófono recalibrado.")
            return

        # ── Sistema ───────────────────────────────────────────────────────────
        if _coincide(cmd_l, _SINONIMOS_SISTEMA):
            self.sistema.obtener_info_sistema()
            return

        if _coincide(cmd_l, _SINONIMOS_DISCO):
            self.sistema.obtener_uso_disco()
            return

        if any(w in cmd_l for w in ("procesos pesados", "qué proceso usa más",
                                     "que proceso usa mas", "procesos que más consumen",
                                     "qué está consumiendo", "que esta consumiendo")):
            self.sistema.obtener_procesos_pesados()
            return

        if "bloquea" in cmd_l or "bloquear" in cmd_l or "bloquea la pc" in cmd_l:
            self.sistema.bloquear_pc()
            return

        if any(w in cmd_l for w in ("apaga la pc", "apaga el pc", "apaga la computadora")):
            self.sistema.apagar_pc(segundos=60)
            return

        if "cancela apagado" in cmd_l:
            self.sistema.cancelar_apagado()
            return

        # ── Git ───────────────────────────────────────────────────────────────
        if "git status" in cmd_l or "estado del repo" in cmd_l or "estado del git" in cmd_l:
            self.dev.estado_git()
            return

        if "git push" in cmd_l or "sube los cambios" in cmd_l or "hacer push" in cmd_l:
            self.dev.hacer_push()
            return

        if "git pull" in cmd_l or "baja los cambios" in cmd_l or "jala los cambios" in cmd_l:
            self.dev.hacer_pull()
            return

        if "git log" in cmd_l or "últimos commits" in cmd_l or "ultimos commits" in cmd_l or "historial de commits" in cmd_l:
            self.dev.log_reciente()
            return

        if "git commit" in cmd_l or "haz commit" in cmd_l or "hacer commit" in cmd_l:
            mensaje = (cmd_l.replace("git commit", "").replace("haz commit", "")
                            .replace("hacer commit", "").replace("-m", "").strip().strip('"\''))
            if mensaje:
                self.dev.hacer_commit(mensaje)
            else:
                self.hablar("¿Cuál es el mensaje del commit?")
            return

        if "ramas" in cmd_l or "listar ramas" in cmd_l or "mis ramas" in cmd_l:
            self.dev.listar_ramas()
            return

        if any(w in cmd_l for w in ("nueva rama", "crea rama", "crear rama")):
            nombre = (cmd_l.replace("nueva rama", "").replace("crea rama", "")
                          .replace("crear rama", "").strip())
            if nombre:
                self.dev.crear_rama(nombre)
            else:
                self._pedir("nueva_rama", {}, "¿Cómo se llamará la nueva rama?")
            return

        if any(w in cmd_l for w in ("cambia rama", "cambiar rama", "cambia a rama",
                                     "ve a rama", "checkout")):
            nombre = (cmd_l.replace("cambia rama", "").replace("cambiar rama", "")
                          .replace("cambia a rama", "").replace("ve a rama", "")
                          .replace("checkout", "").strip())
            if nombre:
                self.dev.cambiar_rama(nombre)
            else:
                self._pedir("cambiar_rama", {}, "¿A qué rama quieres cambiar?")
            return

        if "clona " in cmd_l or "clonar " in cmd_l or "git clone" in cmd_l:
            url = (cmd_l.replace("clona", "").replace("clonar", "")
                        .replace("git clone", "").strip())
            if url:
                self.dev.clonar_repositorio(url)
            else:
                self._pedir("clonar_repo", {}, "¿Cuál es la URL del repositorio a clonar?")
            return

        if any(w in cmd_l for w in ("abre vscode en", "abrir vscode en",
                                     "vscode en", "code en")):
            for kw in ("abre vscode en ", "abrir vscode en ", "vscode en ", "code en "):
                if kw in cmd_l:
                    carpeta = cmd_l.split(kw, 1)[-1].strip()
                    ruta    = self.sistema._resolver_carpeta_destino(carpeta)
                    self.dev.abrir_vscode(ruta)
                    return
            self.dev.abrir_vscode()
            return

        if "docs python" in cmd_l or "documenta python" in cmd_l or "documentación python" in cmd_l:
            self.dev.abrir_docs_python()
            return

        if "mdn " in cmd_l or cmd_l == "mdn":
            self.dev.abrir_mdn()
            return

        if "stackoverflow" in cmd_l or "stack overflow" in cmd_l:
            self.dev.abrir_stackoverflow()
            return

        # ── Productividad ─────────────────────────────────────────────────────
        if any(w in cmd_l for w in ("resumen", "qué hice hoy", "que hice hoy",
                                     "mi resumen", "resumen del día", "resumen del dia")):
            self.resumen.resumen_del_dia()
            return

        if _coincide(cmd_l, _SINONIMOS_HORA):
            self.productividad.decir_hora()
            return

        if _coincide(cmd_l, _SINONIMOS_FECHA):
            self.productividad.decir_fecha()
            return

        if any(kw in cmd_l for kw in ("cuánto es", "cuanto es", "calcula",
                                        "resultado de", "cuánto son", "cuanto son")):
            if self.productividad.calcular(cmd_l):
                return

        if "convierte " in cmd_l or "convertir " in cmd_l:
            self.productividad.convertir(cmd_l)
            return

        # ── Modo Enfoque ──────────────────────────────────────────────────────
        if any(w in cmd_l for w in ("modo enfoque", "modo focus", "activa el enfoque",
                                     "activa focus")):
            minutos = 25
            for p in cmd_l.split():
                if p.isdigit():
                    minutos = int(p)
                    break
            self.focus.activar(minutos)
            return

        if any(w in cmd_l for w in ("termina enfoque", "fin enfoque",
                                     "desbloquea sitios", "desactiva enfoque")):
            self.focus.desactivar()
            return

        # ── Fallback: informar ────────────────────────────────────────────────
        self.hablar(self.persona.no_entendi())

    # ── Helpers de comandos complejos ─────────────────────────────────────────

    def _cmd_crear_archivo(self, cmd_l: str):
        """Parsea 'crea archivo [tipo] [nombre] en [carpeta]'."""
        # Quitar trigger
        for trigger in ("crea un archivo ", "crea archivo ", "nuevo archivo ", "crear archivo "):
            if trigger in cmd_l:
                resto = cmd_l.split(trigger, 1)[-1].strip()
                break
        else:
            resto = cmd_l

        # ¿Hay "en [carpeta]"?
        carpeta = None
        if " en " in resto:
            partes  = resto.rsplit(" en ", 1)
            resto   = partes[0].strip()
            carpeta = partes[1].strip()

        tokens = resto.split()
        tipo   = tokens[0] if tokens else "txt"
        nombre = " ".join(tokens[1:]) if len(tokens) > 1 else "nuevo_archivo"

        if carpeta:
            self.sistema.crear_archivo(tipo=tipo, nombre=nombre, carpeta=carpeta)
        else:
            self._pedir("crear_archivo", {"tipo": tipo, "nombre": nombre},
                        f"¿En qué carpeta quieres crear el archivo {nombre}.{tipo}?")

    def _cmd_crear_carpeta(self, cmd_l: str):
        """Parsea 'crea carpeta [nombre] en [carpeta]'."""
        for trigger in ("crea una carpeta ", "crea carpeta ", "nueva carpeta ", "crear carpeta "):
            if trigger in cmd_l:
                resto = cmd_l.split(trigger, 1)[-1].strip()
                break
        else:
            resto = cmd_l

        ruta_padre = None
        if " en " in resto:
            partes     = resto.rsplit(" en ", 1)
            resto      = partes[0].strip()
            ruta_padre = partes[1].strip()

        nombre = resto

        if ruta_padre:
            self.sistema.crear_carpeta(nombre=nombre, ruta_padre=ruta_padre)
        else:
            self._pedir("crear_carpeta", {"nombre": nombre},
                        f"¿En qué carpeta quieres crear '{nombre}'?")

    def _cmd_abrir_carpeta(self, cmd_l: str):
        """Parsea 'abre carpeta [nombre]' o accesos directos tipo 'abre documentos'."""
        atajos = {
            "documentos": "documentos",
            "descargas":  "descargas",
            "escritorio": "escritorio",
            "imágenes":   "imágenes",
            "imagenes":   "imágenes",
            "música":     "música",
            "musica":     "música",
            "videos":     "videos",
        }
        for atajo, clave in atajos.items():
            if atajo in cmd_l:
                self.sistema.abrir_carpeta_conocida(clave)
                return

        for trigger in ("abre carpeta ", "abrir carpeta ", "abre la carpeta "):
            if trigger in cmd_l:
                nombre = cmd_l.split(trigger, 1)[-1].strip()
                self.sistema.abrir_carpeta_conocida(nombre)
                return

        self.hablar("¿Qué carpeta quieres que abra?")

    def _cmd_buscar_carpeta(self, cmd_l: str):
        """Parsea 'busca [término] en [carpeta]'."""
        for trigger in ("busca ", "encuentra ", "buscar "):
            if trigger in cmd_l:
                resto = cmd_l.split(trigger, 1)[-1].strip()
                break
        else:
            return

        if " en " in resto:
            partes        = resto.rsplit(" en ", 1)
            termino       = partes[0].strip()
            nombre_carpeta = partes[1].strip()
            self.sistema.buscar_en_carpeta(termino, nombre_carpeta)
        else:
            self._pedir("buscar_carpeta", {"termino": resto},
                        f"¿En qué carpeta quieres buscar '{resto}'?")

    def _cmd_recordatorio(self, cmd_l: str):
        """Parsea 'recuerda [X] en [N] minutos' y variaciones."""
        try:
            if " en " in cmd_l:
                partes  = cmd_l.split(" en ", 1)
                mensaje = (partes[0].replace("recuerda", "")
                                    .replace("recuérdame", "")
                                    .replace("recuerdame", "").strip())
                resto   = partes[1]
                mins    = float("".join(c for c in resto if c.isdigit() or c == ".") or "5")
                self.memoria.recordar_en(mensaje, mins)
            else:
                self.hablar("No entendí el recordatorio. Di: recuerda [cosa] en [N] minutos.")
        except Exception:
            self.hablar("No entendí el recordatorio.")

    # ── Bucle de escucha ──────────────────────────────────────────────────────

    def _listen_loop(self):
        with self.microphone as src:
            self.recognizer.adjust_for_ambient_noise(src, duration=1.5)

            while not self._shutdown_flag.is_set():
                if not self.is_active:
                    time.sleep(0.4)
                    continue
                try:
                    audio = self.recognizer.listen(src, timeout=None, phrase_time_limit=10)
                    cmd   = self.recognizer.recognize_google(audio, language="es-MX").lower()

                    if "gracias" in cmd:
                        self.cerrar_comandos_txt()
                        self.hablar(self.persona.gracias())
                        continue

                    print(f"Escuché: '{cmd}'")

                    if cmd.strip() in ("lia", "lía"):
                        self.hablar(self.persona.saludo_corto())
                        continue

                    # Si hay acción pendiente, cualquier respuesta la completa
                    if self._pending_action:
                        limpio = (cmd.replace("lía,", "").replace("lia,", "")
                                     .replace("lía", "").replace("lia", "")
                                     .strip().strip(",. "))
                        if limpio:
                            self._parse_command(limpio)
                        continue

                    if "lia" in cmd or "lía" in cmd:
                        limpio = (cmd.replace("lía,", "").replace("lia,", "")
                                     .replace("lía", "").replace("lia", "")
                                     .strip().strip(",. "))
                        if limpio:
                            self._parse_command(limpio)

                except sr.UnknownValueError:
                    pass
                except sr.RequestError as ex:
                    print(f"Error reconocimiento: {ex}")
                except Exception:
                    time.sleep(0.5)

    def run(self):
        voz = threading.Thread(target=self._listen_loop, daemon=True)
        voz.start()
        try:
            self.detector.start_loop(shutdown_flag=self._shutdown_flag)
        except KeyboardInterrupt:
            print("\nLia detenida.")
        finally:
            self._shutdown_flag.set()


if __name__ == "__main__":
    LiaAssistant().run()
