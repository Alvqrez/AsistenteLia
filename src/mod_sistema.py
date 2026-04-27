#!/usr/bin/env python3

import logging
import os
import subprocess
import platform
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
        "vscode":                    "code",
        "visual studio code":        "code",
        "visual studio":             "code",
        "spotify":                   r"%APPDATA%\Spotify\Spotify.exe",
        "discord":                   r"%LOCALAPPDATA%\Discord\Update.exe",
        "whatsapp":                  r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe",
        "telegram":                  r"%APPDATA%\Telegram Desktop\Telegram.exe",
        "slack":                     r"%LOCALAPPDATA%\slack\slack.exe",
        "teams":                     r"%LOCALAPPDATA%\Microsoft\Teams\current\Teams.exe",
        "zoom":                      r"%APPDATA%\Zoom\bin\Zoom.exe",
        "chrome":                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "firefox":                   r"C:\Program Files\Mozilla Firefox\firefox.exe",
        "edge":                      r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "word":                      r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
        "excel":                     r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
        "powerpoint":                r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
        "outlook":                   r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
        "obsidian":                  r"%LOCALAPPDATA%\Obsidian\Obsidian.exe",
        "notion":                    r"%LOCALAPPDATA%\Programs\Notion\Notion.exe",
        "notepad":                   "notepad.exe",
        "bloc de notas":             "notepad.exe",
        "explorador":                "explorer.exe",
        "calculadora":               "calc.exe",
        "terminal":                  "wt.exe",
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
        "documentos":   os.path.expanduser("~/Documents"),
        "documents":    os.path.expanduser("~/Documents"),
        "descargas":    os.path.expanduser("~/Downloads"),
        "downloads":    os.path.expanduser("~/Downloads"),
        "escritorio":   os.path.expanduser("~/Desktop"),
        "desktop":      os.path.expanduser("~/Desktop"),
        "imágenes":     os.path.expanduser("~/Pictures"),
        "imagenes":     os.path.expanduser("~/Pictures"),
        "pictures":     os.path.expanduser("~/Pictures"),
        "videos":       os.path.expanduser("~/Videos"),
        "música":       os.path.expanduser("~/Music"),
        "musica":       os.path.expanduser("~/Music"),
        "onedrive":     os.path.expandvars("%OneDrive%"),
        "notas":        os.path.join(os.path.expanduser("~"), "Documents", "Notas"),
    }

    def __init__(self, parent_lia):
        self.lia     = parent_lia
        self.os_type = platform.system()

    def _es_comando_simple(self, ruta: str) -> bool:
        return "\\" not in ruta and "/" not in ruta

    def _resolver_ruta(self, clave: str):
        raw = self.APP_MAP.get(clave.lower(), "")
        if not raw:
            return None
        ruta = os.path.expandvars(raw)
        if self._es_comando_simple(ruta):
            return ruta
        return ruta if os.path.exists(ruta) else None

    def es_carpeta_conocida(self, nombre: str) -> bool:
        return nombre.lower().strip() in self.CARPETAS_MAP

    def abrir_web(self, nombre: str):
        nombre_lower = nombre.lower().strip()
        url = self.WEB_MAP.get(nombre_lower)
        if url:
            webbrowser.open(url)
            self.lia.hablar(f"Abriendo {nombre} en el navegador.")
            self.lia.registrar_actividad(f"Abrió web: {nombre}")
            if hasattr(self.lia, "contexto"):
                self.lia.contexto.registrar_apertura_url(url)
        else:
            url_google = f"https://www.google.com/search?q={nombre_lower}"
            webbrowser.open(url_google)
            self.lia.hablar(f"No tenía la URL de {nombre}. Busqué en Google.")
            self.lia.registrar_actividad(f"Buscó web: {nombre}")

    def open_application(self, nombre: str):
        nombre_limpio = nombre.lower().strip()
        if not nombre_limpio:
            self.lia.hablar("No entendí qué aplicación abrir.")
            return

        ruta = self._resolver_ruta(nombre_limpio)
        if ruta:
            try:
                if "Update.exe" in ruta and "Discord" in ruta:
                    subprocess.Popen(f'"{ruta}" --processStart Discord.exe', shell=True)
                elif self._es_comando_simple(ruta):
                    subprocess.Popen(ruta, shell=True)
                else:
                    subprocess.Popen(f'"{ruta}"', shell=True)
                self.lia.hablar(f"Abriendo {nombre}.")
                self.lia.registrar_actividad(f"Abrió {nombre}")
                if hasattr(self.lia, "contexto"):
                    self.lia.contexto.registrar_apertura_app(nombre_limpio)
                return
            except Exception as ex:
                logger.error("Error al lanzar '%s': %s", ruta, ex)

        try:
            subprocess.Popen(nombre_limpio, shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.lia.hablar(f"Intentando abrir {nombre}.")
            self.lia.registrar_actividad(f"Abrió (shell) {nombre}")
            if hasattr(self.lia, "contexto"):
                self.lia.contexto.registrar_apertura_app(nombre_limpio)
            return
        except Exception as ex:
            logger.warning("Fallo shell directo para '%s': %s", nombre_limpio, ex)

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
                        self.lia.hablar(f"Abriendo {archivo.replace('.lnk', '')}.")
                        self.lia.registrar_actividad(f"Abrió {archivo}")
                        if hasattr(self.lia, "contexto"):
                            self.lia.contexto.registrar_apertura_app(nombre_limpio)
                        return

        url_conocida = self.WEB_MAP.get(nombre_limpio)
        if url_conocida:
            webbrowser.open(url_conocida)
            self.lia.hablar(f"No lo encontré instalado, lo abrí en el navegador.")
            if hasattr(self.lia, "contexto"):
                self.lia.contexto.registrar_apertura_url(url_conocida)
            return

        self.lia.hablar(f"No encontré {nombre} en el sistema.")
        logger.warning("App no encontrada: '%s'", nombre)

    def open_url(self, url: str, nombre: str):
        try:
            webbrowser.open(url)
            self.lia.hablar(f"Abriendo {nombre}.")
            self.lia.registrar_actividad(f"Abrió {nombre}")
            if hasattr(self.lia, "contexto"):
                self.lia.contexto.registrar_apertura_url(url)
        except Exception as ex:
            logger.error("Error al abrir URL '%s': %s", url, ex)
            self.lia.hablar(f"No pude abrir {nombre}.")

    def cerrar_todo(self):
        print("\n🛑 CERRANDO TODO")
        procesos = ["chrome.exe", "msedge.exe", "firefox.exe",
                    "Code.exe", "Spotify.exe", "Discord.exe",
                    "WhatsApp.exe", "Teams.exe"]
        for p in procesos:
            subprocess.run(["taskkill", "/f", "/im", p],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.lia.hablar("Cerré todas las aplicaciones.")
        self.lia.registrar_actividad("Cerró Todo")

    def abrir_desde_descargas(self, nombre: str):
        carpeta = os.path.join(os.path.expanduser("~"), "Downloads")
        for root, _, files in os.walk(carpeta):
            for archivo in files:
                if nombre.lower() in archivo.lower():
                    os.startfile(os.path.join(root, archivo))
                    self.lia.hablar(f"Abriendo {archivo}.")
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
        ruta_base = self.CARPETAS_MAP.get(nombre_carpeta.lower().strip())
        if not ruta_base or not os.path.exists(ruta_base):
            self.lia.hablar(f"No conozco la carpeta '{nombre_carpeta}'.")
            return

        termino_lower = termino.lower()
        encontrados = []

        for root, dirs, files in os.walk(ruta_base):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for archivo in files:
                if termino_lower in archivo.lower():
                    encontrados.append(os.path.join(root, archivo))
            for carpeta in dirs:
                if termino_lower in carpeta.lower():
                    encontrados.append(os.path.join(root, carpeta))
            if len(encontrados) >= 5:
                break

        if not encontrados:
            self.lia.hablar(f"No encontré '{termino}' en {nombre_carpeta}.")
            return

        if len(encontrados) == 1:
            ruta = encontrados[0]
            self.lia.hablar(f"Encontré: {os.path.basename(ruta)}. ¿Lo abro?")
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
                time.sleep(0.2)
            if hasattr(self.lia, "contexto"):
                self.lia.contexto.registrar_apertura_archivo(encontrados[0])
        self.lia.registrar_actividad(f"Buscó '{termino}' en {nombre_carpeta}")

    def modo_estudio(self):
        if hasattr(self.lia, "contexto"):
            self.lia.contexto.limpiar_ultimo_modo()
        print("\n📚 MODO ESTUDIO")
        self.lia.hablar("Activando modo estudio.")
        self.open_url("https://chat.openai.com", "ChatGPT")
        time.sleep(0.4)
        self.open_url("https://web.whatsapp.com", "WhatsApp")
        self.lia.registrar_actividad("Modo Estudio")

    def modo_programacion(self):
        if hasattr(self.lia, "contexto"):
            self.lia.contexto.limpiar_ultimo_modo()
        print("\n💻 MODO CÓDIGO")
        self.lia.hablar("Iniciando entorno de programación.")
        self.open_application("vscode")
        time.sleep(0.4)
        self.open_url("https://github.com", "GitHub")
        time.sleep(0.4)
        self.open_application("spotify")
        self.lia.registrar_actividad("Modo Programación")

    def modo_juego(self):
        if hasattr(self.lia, "contexto"):
            self.lia.contexto.limpiar_ultimo_modo()
        print("\n🎮 MODO JUEGO")
        self.lia.hablar("Todo listo para jugar.")
        self.open_application("discord")
        time.sleep(0.5)
        self.abrir_desde_descargas("TimerResolution")
        self.lia.registrar_actividad("Modo Juego")

    def obtener_info_sistema(self):
        if not _PSUTIL:
            self.lia.hablar("psutil no está instalado.")
            return
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            self.lia.hablar(f"CPU al {cpu:.0f} por ciento.")
            self.lia.hablar(f"RAM al {ram.percent:.0f} por ciento.")
            self.lia.registrar_actividad("Consultó info del sistema")
        except Exception as ex:
            logger.error("Error al leer sistema: %s", ex)
            self.lia.hablar("Error al leer el sistema.")

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
                time.sleep(0.2)
            self.lia.registrar_actividad("Consultó procesos")
        except Exception as ex:
            logger.error("Error al leer procesos: %s", ex)
            self.lia.hablar("Error al leer procesos.")

    def bloquear_pc(self):
        if self.os_type != "Windows":
            self.lia.hablar("Bloquear solo funciona en Windows.")
            return
        self.lia.hablar("Bloqueando PC.")
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        self.lia.registrar_actividad("Bloqueó la PC")

    def apagar_pc(self, segundos: int = 60):
        self.lia.hablar(f"La PC se apagará en {segundos} segundos.")
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
            titulo  = titulo.replace("'", "''")
            mensaje = mensaje.replace("'", "''")
            script = (
                f"Add-Type -AssemblyName System.Windows.Forms;"
                f"$n = New-Object System.Windows.Forms.NotifyIcon;"
                f"$n.Icon = [System.Drawing.SystemIcons]::Information;"
                f"$n.Visible = $true;"
                f"$n.ShowBalloonTip(5000, '{titulo}', '{mensaje}', "
                f"[System.Windows.Forms.ToolTipIcon]::Info);"
                f"Start-Sleep -Seconds 6; $n.Dispose()"
            )
            subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command", script],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception as ex:
            logger.warning("Error al mostrar notificación: %s", ex)