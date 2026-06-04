#!/usr/bin/env python3

import logging
import os
import shutil
import subprocess
import platform
import threading
import webbrowser
import time

logger = logging.getLogger("lia.sistema")

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False
    logger.warning("psutil no instalado. Instala con: pip install psutil")


class SystemTools:

    APP_MAP: dict = {
        # VS Code: instalación de usuario (la más común)
        "vscode":                    r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
        "visual studio code":        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
        "visual studio":             r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
        # Spotify: Store / WindowsApps
        "spotify":                   r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe",
        "discord":                   r"%LOCALAPPDATA%\Discord\Update.exe",
        "whatsapp":                  r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe",
        "telegram":                  r"%APPDATA%\Telegram Desktop\Telegram.exe",
        "slack":                     r"%LOCALAPPDATA%\slack\slack.exe",
        "teams":                     r"%LOCALAPPDATA%\Microsoft\WindowsApps\ms-teams.exe",
        "zoom":                      r"%APPDATA%\Zoom\bin\Zoom.exe",
        "chrome":                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "firefox":                   r"C:\Program Files\Mozilla Firefox\firefox.exe",
        "edge":                      r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        # Office: ruta x86 (instalación estándar en este equipo)
        "word":                      r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
        "excel":                     r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
        "powerpoint":                r"C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE",
        "outlook":                   r"C:\Program Files (x86)\Microsoft Office\root\Office16\OUTLOOK.EXE",
        "obsidian":                  r"%LOCALAPPDATA%\Obsidian\Obsidian.exe",
        "notion":                    r"%LOCALAPPDATA%\Programs\Notion\Notion.exe",
        "notepad":                   "notepad.exe",
        "bloc de notas":             "notepad.exe",
        "explorador":                "explorer.exe",
        "calculadora":               "calc.exe",
        "terminal":                  r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe",
        "cmd":                       "cmd.exe",
        "paint":                     "mspaint.exe",
        "taskmgr":                   "taskmgr.exe",
        "administrador de tareas":   "taskmgr.exe",
        "configuracion":             "ms-settings:",
        "panel de control":          "control.exe",
        "steam":                     r"C:\Program Files (x86)\Steam\steam.exe",
        "vlc":                       r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        "obs":                       r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
        "photoshop":                 r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe",
        "figma":                     r"%LOCALAPPDATA%\Figma\Figma.exe",
        "postman":                   r"%LOCALAPPDATA%\Postman\Postman.exe",
    }

    # Rutas alternativas para apps con ubicaciones variables.
    # Se prueban en orden cuando la ruta principal del APP_MAP no existe.
    _FALLBACK_PATHS: dict = {
        "vscode": [
            r"C:\Program Files\Microsoft VS Code\Code.exe",
        ],
        "chrome": [
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
        "edge": [
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
        "word": [
            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
        ],
        "excel": [
            r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
        ],
        "powerpoint": [
            r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
        ],
        "outlook": [
            r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
        ],
        "spotify": [
            r"%APPDATA%\Spotify\Spotify.exe",
        ],
        "terminal": [
            r"%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe",
        ],
    }

    # URLs de servicios web. Agrega los que quieras con el mismo formato:
    # "nombre que dices": "https://url-del-sitio.com",
    WEB_MAP: dict = {
        "whatsapp web":      "https://web.whatsapp.com",
        "whatsapp":          "https://web.whatsapp.com",
        "canva":             "https://www.canva.com",
        "chatgpt":           "https://chat.openai.com",
        "claude":            "https://claude.ai",
        "gmail":             "https://mail.google.com",
        "google":            "https://www.google.com",
        "drive":             "https://drive.google.com",
        "calendar":          "https://calendar.google.com",
        "google calendar":   "https://calendar.google.com",
        "youtube":           "https://www.youtube.com",
        "github":            "https://github.com",
        "gitlab":            "https://gitlab.com",
        "notion web":        "https://www.notion.so",
        "notion":            "https://www.notion.so",
        "figma web":         "https://www.figma.com",
        "figma":             "https://www.figma.com",
        "spotify web":       "https://open.spotify.com",
        "netflix":           "https://www.netflix.com",
        "twitter":           "https://twitter.com",
        "x":                 "https://x.com",
        "instagram":         "https://www.instagram.com",
        "facebook":          "https://www.facebook.com",
        "linkedin":          "https://www.linkedin.com",
        "reddit":            "https://www.reddit.com",
        "maps":              "https://maps.google.com",
        "google maps":       "https://maps.google.com",
        "traductor":         "https://translate.google.com",
        "translate":         "https://translate.google.com",
        "noticias":          "https://news.google.com",
        "news":              "https://news.google.com",
        "stackoverflow":     "https://stackoverflow.com",
        "stack overflow":    "https://stackoverflow.com",
        "vercel":            "https://vercel.com",
        "railway":           "https://railway.app",
        "supabase":          "https://supabase.com",
        "heroku":            "https://heroku.com",
        "chatgpt 4":         "https://chat.openai.com/?model=gpt-4",
        "openai":            "https://platform.openai.com",
        "anthropic":         "https://console.anthropic.com",
        "perplexity":        "https://www.perplexity.ai",
        "gemini":            "https://gemini.google.com",
        "trello":            "https://trello.com",
        "jira":              "https://id.atlassian.com",
        "asana":             "https://app.asana.com",
        "replit":            "https://replit.com",
        "codesandbox":       "https://codesandbox.io",
        "codepen":           "https://codepen.io",
        "obsidian web":      "https://obsidian.md",
        # ── Agrega tus propias URLs aquí ──────────────────────────────────────
        # "nombre":  "https://url.com",
    }

    CARPETAS_MAP: dict = {
        # Documentos
        "documentos":       os.path.expanduser("~/Documents"),
        "mis documentos":   os.path.expanduser("~/Documents"),
        "documents":        os.path.expanduser("~/Documents"),
        # Descargas
        "descargas":        os.path.expanduser("~/Downloads"),
        "mis descargas":    os.path.expanduser("~/Downloads"),
        "downloads":        os.path.expanduser("~/Downloads"),
        # Escritorio
        "escritorio":       os.path.expanduser("~/Desktop"),
        "el escritorio":    os.path.expanduser("~/Desktop"),
        "desktop":          os.path.expanduser("~/Desktop"),
        # Imágenes
        "imágenes":         os.path.expanduser("~/Pictures"),
        "imagenes":         os.path.expanduser("~/Pictures"),
        "mis imágenes":     os.path.expanduser("~/Pictures"),
        "mis imagenes":     os.path.expanduser("~/Pictures"),
        "pictures":         os.path.expanduser("~/Pictures"),
        "fotos":            os.path.expanduser("~/Pictures"),
        # Videos
        "videos":           os.path.expanduser("~/Videos"),
        "mis videos":       os.path.expanduser("~/Videos"),
        # Música
        "música":           os.path.expanduser("~/Music"),
        "musica":           os.path.expanduser("~/Music"),
        "mi música":        os.path.expanduser("~/Music"),
        # OneDrive / Notas
        "onedrive":         os.path.expandvars("%OneDrive%"),
        "notas":            os.path.join(os.path.expanduser("~"), "Documents", "Notas"),
        # Raíz de usuario
        "usuario":          os.path.expanduser("~"),
        "mi pc":            os.path.expanduser("~"),
        "home":             os.path.expanduser("~"),
    }

    # Lugares donde buscar carpetas personalizadas que el usuario nombre
    _CARPETAS_RAIZ_BUSQUEDA = [
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~"),
    ]

    def __init__(self, parent_lia):
        self.lia     = parent_lia
        self.os_type = platform.system()

    def _es_comando_simple(self, ruta: str) -> bool:
        return "\\" not in ruta and "/" not in ruta

    def _resolver_ruta(self, clave: str):
        clave_l = clave.lower()
        raw = self.APP_MAP.get(clave_l, "")
        if not raw:
            return None

        # URI schemes como ms-settings: se manejan aparte con os.startfile
        if raw.endswith(":") and not raw.startswith("%") and "\\" not in raw:
            return raw

        ruta = os.path.expandvars(raw)

        # Comando simple (sin ruta) → buscar en PATH con shutil.which
        if self._es_comando_simple(ruta):
            found = shutil.which(ruta)
            return found  # None si no está en PATH; cae al Start Menu search

        if os.path.exists(ruta):
            return ruta

        # Probar rutas alternativas
        for fb in self._FALLBACK_PATHS.get(clave_l, []):
            fb_exp = os.path.expandvars(fb)
            if os.path.exists(fb_exp):
                return fb_exp

        return None

    def es_carpeta_conocida(self, nombre: str) -> bool:
        return nombre.lower().strip() in self.CARPETAS_MAP

    def abrir_web(self, nombre: str):
        nombre_lower = nombre.lower().strip()
        url = self.WEB_MAP.get(nombre_lower)
        if url:
            webbrowser.open(url)
            self.lia.hablar(self.lia.persona.abriendo_app(nombre))
            self.lia.registrar_actividad(f"Abrió web: {nombre}")
            if hasattr(self.lia, "contexto"):
                self.lia.contexto.registrar_apertura_url(url)
        else:
            url_google = f"https://www.google.com/search?q={nombre_lower}"
            webbrowser.open(url_google)
            self.lia.hablar(f"No tenía la URL de {nombre}, {self.lia.persona.nombre}. Lo busqué en Google.")
            self.lia.registrar_actividad(f"Buscó web: {nombre}")

    def open_application(self, nombre: str, silent: bool = False):
        """Abre una aplicación. silent=True suprime los mensajes de voz (útil en modos)."""
        nombre_limpio = nombre.lower().strip()
        if not nombre_limpio:
            if not silent:
                self.lia.hablar(self.lia.persona.no_entendi())
            return

        ruta = self._resolver_ruta(nombre_limpio)
        if ruta:
            try:
                if ruta.endswith(":") and "\\" not in ruta:
                    # URI scheme (ms-settings:, etc.)
                    os.startfile(ruta)
                elif "Update.exe" in ruta and "Discord" in ruta:
                    subprocess.Popen([ruta, "--processStart", "Discord.exe"])
                else:
                    subprocess.Popen([ruta])
                if not silent:
                    self.lia.hablar(self.lia.persona.abriendo_app(nombre))
                self.lia.registrar_actividad(f"Abrió {nombre}")
                if hasattr(self.lia, "contexto"):
                    self.lia.contexto.registrar_apertura_app(nombre_limpio)
                return
            except Exception as ex:
                logger.error("Error al lanzar '%s': %s", ruta, ex)

        try:
            # Sin shell=True: evita command injection con input del usuario.
            # Se usa lista de argumentos para que el OS no interprete metacaracteres.
            subprocess.Popen([nombre_limpio],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if not silent:
                self.lia.hablar(self.lia.persona.abriendo_app(nombre))
            self.lia.registrar_actividad(f"Abrió (shell) {nombre}")
            if hasattr(self.lia, "contexto"):
                self.lia.contexto.registrar_apertura_app(nombre_limpio)
            return
        except Exception as ex:
            logger.warning("Fallo ejecución directa para '%s': %s", nombre_limpio, ex)

        start_menus = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        ]
        for carpeta in start_menus:
            if not os.path.exists(carpeta):
                continue
            for root, _, files in os.walk(carpeta):
                for archivo in files:
                    if nombre_limpio in archivo.lower() and archivo.endswith(".lnk"):
                        os.startfile(os.path.join(root, archivo))
                        if not silent:
                            self.lia.hablar(self.lia.persona.abriendo_app(archivo.replace(".lnk", "")))
                        self.lia.registrar_actividad(f"Abrió {archivo}")
                        if hasattr(self.lia, "contexto"):
                            self.lia.contexto.registrar_apertura_app(nombre_limpio)
                        return

        url_conocida = self.WEB_MAP.get(nombre_limpio)
        if url_conocida:
            webbrowser.open(url_conocida)
            if not silent:
                self.lia.hablar(f"No lo encontré instalado, {self.lia.persona.nombre}. Lo abrí en el navegador.")
            if hasattr(self.lia, "contexto"):
                self.lia.contexto.registrar_apertura_url(url_conocida)
            return

        if not silent:
            self.lia.hablar(self.lia.persona.app_no_encontrada(nombre))
        logger.warning("App no encontrada: '%s'", nombre)

    def open_url(self, url: str, nombre: str, silent: bool = False):
        try:
            webbrowser.open(url)
            if not silent:
                self.lia.hablar(self.lia.persona.abriendo_app(nombre))
            self.lia.registrar_actividad(f"Abrió {nombre}")
            if hasattr(self.lia, "contexto"):
                self.lia.contexto.registrar_apertura_url(url)
        except Exception as ex:
            logger.error("Error al abrir URL '%s': %s", url, ex)
            if not silent:
                self.lia.hablar(self.lia.persona.error_generico(f"abrir {nombre}"))

    # Mapa nombre hablado → proceso .exe para cerrar individualmente.
    _CLOSE_MAP: dict = {
        "spotify":               "Spotify.exe",
        "vscode":                "Code.exe",
        "visual studio":         "Code.exe",
        "visual studio code":    "Code.exe",
        "código":                "Code.exe",
        "codigo":                "Code.exe",
        "chrome":                "chrome.exe",
        "firefox":               "firefox.exe",
        "edge":                  "msedge.exe",
        "discord":               "Discord.exe",
        "whatsapp":              "WhatsApp.exe",
        "telegram":              "Telegram.exe",
        "slack":                 "slack.exe",
        "zoom":                  "Zoom.exe",
        "teams":                 "Teams.exe",
        "notepad":               "notepad.exe",
        "bloc de notas":         "notepad.exe",
        "obs":                   "obs64.exe",
        "vlc":                   "vlc.exe",
        "photoshop":             "Photoshop.exe",
        "figma":                 "Figma.exe",
        "postman":               "Postman.exe",
        "steam":                 "steam.exe",
        "word":                  "WINWORD.EXE",
        "excel":                 "EXCEL.EXE",
        "powerpoint":            "POWERPNT.EXE",
        "outlook":               "OUTLOOK.EXE",
        "obsidian":              "Obsidian.exe",
        "notion":                "Notion.exe",
        "calculadora":           "CalculatorApp.exe",
        "paint":                 "mspaint.exe",
        "administrador de tareas": "Taskmgr.exe",
    }

    def cerrar_app(self, nombre: str):
        """Cierra una aplicación específica por nombre hablado."""
        nombre_l = nombre.lower().strip()
        proc = self._CLOSE_MAP.get(nombre_l)

        if not proc:
            # Búsqueda parcial en el mapa (p.ej. "el spotify" → "spotify")
            for clave, exe in self._CLOSE_MAP.items():
                if clave in nombre_l or nombre_l in clave:
                    proc = exe
                    break

        if not proc:
            # Intento directo: añade .exe si el usuario lo nombró exactamente
            proc = nombre_l if nombre_l.endswith(".exe") else nombre_l + ".exe"

        result = subprocess.run(
            ["taskkill", "/f", "/im", proc],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        nombre_display = nombre.strip().title()
        if result.returncode == 0:
            self.lia.hablar(f"Cerré {nombre_display}.")
            self.lia.registrar_actividad(f"Cerró {nombre_display}")
        else:
            self.lia.hablar(f"No encontré {nombre_display} abierto.")

    def cerrar_todo(self):
        procesos = ["chrome.exe", "msedge.exe", "firefox.exe",
                    "Code.exe", "Spotify.exe", "Discord.exe",
                    "WhatsApp.exe", "Teams.exe"]
        for p in procesos:
            subprocess.run(["taskkill", "/f", "/im", p],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.lia.hablar(self.lia.persona.cerrando_todo())
        self.lia.registrar_actividad("Cerró Todo")

    def abrir_desde_descargas(self, nombre: str, silent: bool = False):
        carpeta = os.path.join(os.path.expanduser("~"), "Downloads")
        for root, _, files in os.walk(carpeta):
            for archivo in files:
                if nombre.lower() in archivo.lower():
                    os.startfile(os.path.join(root, archivo))
                    if not silent:
                        self.lia.hablar(self.lia.persona.abriendo_app(archivo))
                    self.lia.registrar_actividad(f"Abrió desde Descargas: {archivo}")
                    return
        logger.info("'%s' no encontrado en Descargas.", nombre)

    def abrir_carpeta(self, ruta: str):
        if not os.path.exists(ruta):
            self.lia.hablar("La carpeta no existe.")
            return
        try:
            if self.os_type == "Windows":
                os.startfile(ruta)
            elif self.os_type == "Darwin":
                subprocess.Popen(["open", ruta])
            else:
                subprocess.Popen(["xdg-open", ruta])
            self.lia.hablar("Abriendo carpeta.")
            self.lia.registrar_actividad(f"Abrió carpeta: {ruta}")
        except Exception as ex:
            logger.error("Error al abrir carpeta '%s': %s", ruta, ex)
            self.lia.hablar("Error al abrir carpeta.")

    def buscar_en_carpeta(self, termino: str, nombre_carpeta: str):
        """
        Busca archivos/carpetas que contengan `termino` dentro de `nombre_carpeta`.
        La búsqueda se ejecuta en un hilo daemon para no bloquear el listener de voz
        (os.walk sobre ~/Documents puede tardar varios segundos).
        """
        clave     = nombre_carpeta.lower().strip()
        ruta_base = self.CARPETAS_MAP.get(clave)

        if not ruta_base or not os.path.exists(ruta_base):
            ruta_base = self._buscar_carpeta_por_nombre(nombre_carpeta)

        if not ruta_base:
            self.lia.hablar(
                f"No encontré ninguna carpeta llamada '{nombre_carpeta}'. "
                f"Prueba diciendo: busca {termino} en documentos, descargas o escritorio."
            )
            return

        def _buscar():
            termino_lower = termino.lower()
            encontrados   = []
            try:
                for root, dirs, files in os.walk(ruta_base):
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    for archivo in files:
                        if termino_lower in archivo.lower():
                            encontrados.append(os.path.join(root, archivo))
                    for carpeta in dirs:
                        if termino_lower in carpeta.lower():
                            encontrados.append(os.path.join(root, carpeta))
                    if len(encontrados) >= 8:
                        break
            except Exception as ex:
                logger.error("Error durante búsqueda en '%s': %s", ruta_base, ex)

            if not encontrados:
                self.lia.hablar(f"No encontré '{termino}' en {nombre_carpeta}.")
                return

            if len(encontrados) == 1:
                ruta = encontrados[0]
                self.lia.hablar(f"Encontré: {os.path.basename(ruta)}. Abriendo.")
                if hasattr(self.lia, "contexto"):
                    self.lia.contexto.registrar_apertura_archivo(ruta)
                try:
                    os.startfile(ruta)
                except Exception as ex:
                    logger.error("Error al abrir resultado de búsqueda: %s", ex)
            else:
                self.lia.hablar(f"Encontré {len(encontrados)} resultados en {nombre_carpeta}:")
                for r in encontrados[:3]:
                    self.lia.hablar(os.path.basename(r))
                if len(encontrados) > 3:
                    self.lia.hablar(f"Y {len(encontrados) - 3} más.")
                if hasattr(self.lia, "contexto"):
                    self.lia.contexto.registrar_apertura_archivo(encontrados[0])
            self.lia.registrar_actividad(f"Buscó '{termino}' en {nombre_carpeta}")

        threading.Thread(target=_buscar, daemon=True).start()

    def _buscar_carpeta_por_nombre(self, nombre: str) -> str | None:
        """
        Busca una carpeta por nombre en las ubicaciones comunes del usuario.
        Devuelve la ruta si la encuentra, None si no.
        """
        nombre_lower = nombre.lower().strip()
        for raiz in self._CARPETAS_RAIZ_BUSQUEDA:
            if not os.path.exists(raiz):
                continue
            try:
                for entry in os.scandir(raiz):
                    if entry.is_dir() and entry.name.lower() == nombre_lower:
                        return entry.path
            except PermissionError:
                continue
        return None

    def modo_estudio(self):
        if hasattr(self.lia, "contexto"):
            self.lia.contexto.limpiar_ultimo_modo()
        self.lia.hablar(self.lia.persona.modo_estudio())
        # Las apps se abren en hilo daemon para no bloquear el listener ni el detector de aplausos.
        # Los sleeps internos escalonan los lanzamientos sin afectar la UI de voz.
        def _run():
            self.open_url("https://chat.openai.com", "ChatGPT", silent=True)
            time.sleep(0.4)
            self.open_url("https://web.whatsapp.com", "WhatsApp", silent=True)
            self.lia.registrar_actividad("Modo Estudio")
        threading.Thread(target=_run, daemon=True).start()

    def modo_programacion(self):
        if hasattr(self.lia, "contexto"):
            self.lia.contexto.limpiar_ultimo_modo()
        self.lia.hablar(self.lia.persona.modo_codigo())
        def _run():
            self.open_application("vscode", silent=True)
            time.sleep(0.4)
            self.open_url("https://github.com", "GitHub", silent=True)
            time.sleep(0.4)
            self.open_application("spotify", silent=True)
            self.lia.registrar_actividad("Modo Programación")
        threading.Thread(target=_run, daemon=True).start()

    def modo_juego(self):
        if hasattr(self.lia, "contexto"):
            self.lia.contexto.limpiar_ultimo_modo()
        self.lia.hablar(self.lia.persona.modo_juego())
        def _run():
            self.open_application("discord", silent=True)
            time.sleep(0.5)
            self.abrir_desde_descargas("TimerResolution", silent=True)
            self.lia.registrar_actividad("Modo Juego")
        threading.Thread(target=_run, daemon=True).start()

    def obtener_info_sistema(self):
        if not _PSUTIL:
            self.lia.hablar("psutil no está instalado.")
            return
        # cpu_percent(interval=1) bloquea 1 segundo — se ejecuta en hilo daemon
        # para no bloquear el listener de voz.
        def _run():
            try:
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory()
                self.lia.hablar(self.lia.persona.cpu_ram(cpu, ram.percent))
                self.lia.registrar_actividad("Consultó info del sistema")
            except Exception as ex:
                logger.error("Error al leer sistema: %s", ex)
                self.lia.hablar(self.lia.persona.error_generico("leer el sistema"))
        threading.Thread(target=_run, daemon=True).start()

    def obtener_uso_disco(self):
        if not _PSUTIL:
            self.lia.hablar("psutil no está instalado.")
            return
        try:
            ruta = "C:\\" if self.os_type == "Windows" else "/"
            disco    = psutil.disk_usage(ruta)
            libre_gb = disco.free  / (1024 ** 3)
            total_gb = disco.total / (1024 ** 3)
            self.lia.hablar(
                f"Disco al {disco.percent:.0f} por ciento. "
                f"{libre_gb:.0f} de {total_gb:.0f} GB libres."
            )
            self.lia.registrar_actividad("Consultó uso de disco")
        except Exception as ex:
            logger.error("Error al leer disco: %s", ex)
            self.lia.hablar("Error al leer el disco.")

    def obtener_procesos_pesados(self, top_n: int = 5):
        if not _PSUTIL:
            self.lia.hablar("psutil no está instalado.")
            return
        try:
            procs = sorted(
                psutil.process_iter(["name", "memory_percent"]),
                key=lambda p: p.info.get("memory_percent") or 0,
                reverse=True,
            )[:top_n]
            self.lia.hablar("Procesos más pesados:")
            for p in procs:
                mem = p.info.get("memory_percent") or 0
                self.lia.hablar(f"{p.info['name']}: {mem:.1f} por ciento")
            self.lia.registrar_actividad("Consultó procesos")
        except Exception as ex:
            logger.error("Error al leer procesos: %s", ex)
            self.lia.hablar("Error al leer procesos.")

    def bloquear_pc(self):
        if self.os_type != "Windows":
            self.lia.hablar("Bloquear solo funciona en Windows.")
            return
        self.lia.hablar(self.lia.persona.bloqueando_pc())
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        self.lia.registrar_actividad("Bloqueó la PC")

    def apagar_pc(self, segundos: int = 60):
        self.lia.hablar(f"La PC se apagará en {segundos} segundos, {self.lia.persona.nombre}.")
        if self.os_type == "Windows":
            subprocess.run(["shutdown", "/s", "/t", str(segundos)],
                           stdout=subprocess.DEVNULL)
        else:
            subprocess.run(["shutdown", "-h", f"+{segundos // 60}"])
        self.lia.registrar_actividad("Programó apagado")

    def cancelar_apagado(self):
        if self.os_type != "Windows":
            self.lia.hablar("Solo funciona en Windows.")
            return
        subprocess.run(["shutdown", "/a"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.lia.hablar("Apagado cancelado.")
        self.lia.registrar_actividad("Canceló apagado")

    def notificar(self, titulo: str, mensaje: str):
        try:
            # Los datos se pasan por variables de entorno, no interpolados en el script,
            # para evitar cualquier inyección de comandos PowerShell.
            script = (
                "Add-Type -AssemblyName System.Windows.Forms;"
                "$n = New-Object System.Windows.Forms.NotifyIcon;"
                "$n.Icon = [System.Drawing.SystemIcons]::Information;"
                "$n.Visible = $true;"
                "$n.ShowBalloonTip(5000, $env:LIA_NOTIF_TITULO, $env:LIA_NOTIF_MENSAJE, "
                "[System.Windows.Forms.ToolTipIcon]::Info);"
                "Start-Sleep -Seconds 6; $n.Dispose()"
            )
            env = os.environ.copy()
            env["LIA_NOTIF_TITULO"] = str(titulo)
            env["LIA_NOTIF_MENSAJE"] = str(mensaje)
            subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command", script],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                env=env,
            )
        except Exception as ex:
            logger.warning("Error al mostrar notificación: %s", ex)