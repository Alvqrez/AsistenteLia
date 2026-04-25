#!/usr/bin/env python3
"""
mod_sistema.py  –  Módulo de Sistema
Responsabilidades:
  · Abrir / cerrar aplicaciones de escritorio
  · Modos de trabajo (Estudio, Código, Juego)
  · Control del sistema: disco, procesos, energía, bloqueo
  · Notificaciones toast de Windows
"""

import os
import subprocess
import platform
import webbrowser
import time

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False
    print("⚠️  psutil no instalado. Instala con: pip install psutil")


class SystemTools:
    """
    Todas las operaciones que tocan el sistema operativo o lanzan procesos.
    Recibe 'parent_lia' para poder llamar hablar() y registrar_actividad().
    """

    # ── Mapa de aplicaciones ─────────────────────────────────
    APP_MAP: dict = {
        # Desarrollo
        "vscode":                    "code.cmd",
        "visual studio code":        "code.cmd",
        "visual studio":             "code.cmd",
        # Música
        "spotify":                   r"%APPDATA%\Spotify\Spotify.exe",
        # Comunicación
        "discord":                   r"%LOCALAPPDATA%\Discord\Update.exe",
        "whatsapp":                  r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe",
        "telegram":                  r"%APPDATA%\Telegram Desktop\Telegram.exe",
        "slack":                     r"%LOCALAPPDATA%\slack\slack.exe",
        "teams":                     r"%LOCALAPPDATA%\Microsoft\Teams\current\Teams.exe",
        "zoom":                      r"%APPDATA%\Zoom\bin\Zoom.exe",
        # Navegadores
        "chrome":                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "firefox":                   r"C:\Program Files\Mozilla Firefox\firefox.exe",
        "edge":                      r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        # Microsoft Office
        "word":                      r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
        "excel":                     r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
        "powerpoint":                r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
        "outlook":                   r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE",
        # Notas / productividad
        "obsidian":                  r"%LOCALAPPDATA%\Obsidian\Obsidian.exe",
        "notion":                    r"%LOCALAPPDATA%\Programs\Notion\Notion.exe",
        "notepad":                   "notepad.exe",
        "bloc de notas":             "notepad.exe",
        # Sistema
        "explorador":                "explorer.exe",
        "calculadora":               "calc.exe",
        "terminal":                  "wt.exe",
        "cmd":                       "cmd.exe",
        "paint":                     "mspaint.exe",
        "taskmgr":                   "taskmgr.exe",
        "administrador de tareas":   "taskmgr.exe",
        "configuracion":             "ms-settings:",
        "panel de control":          "control.exe",
        # Multimedia / gaming
        "steam":                     r"C:\Program Files (x86)\Steam\steam.exe",
        "vlc":                       r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        "obs":                       r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
        "photoshop":                 r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe",
        "figma":                     r"%LOCALAPPDATA%\Figma\Figma.exe",
        "postman":                   r"%LOCALAPPDATA%\Postman\Postman.exe",
    }

    def __init__(self, parent_lia):
        self.lia     = parent_lia
        self.os_type = platform.system()

    # ════════════════════════════════════════════════════════
    #  APERTURA DE APLICACIONES
    # ════════════════════════════════════════════════════════

    def _resolver_ruta(self, clave: str):
        raw = self.APP_MAP.get(clave.lower(), "")
        if not raw:
            return None

        ruta = os.path.expandvars(raw)

        # Si no tiene barras (\) ni puntos (.), es un comando del sistema (como 'code')
        # No verificamos si existe, dejamos que subprocess lo intente.
        if "\\" not in ruta and "/" not in ruta:
            return ruta

            # Si es una ruta completa, ahí sí verificamos
        return ruta if os.path.exists(ruta) else None

    def open_application(self, nombre: str):
        """
        Abre una app por nombre hablado.
        3 capas: APP_MAP → shell directo → búsqueda en Menú de Inicio.
        """
        nombre_limpio = nombre.lower().strip()

        # 1. APP_MAP
        ruta = self._resolver_ruta(nombre_limpio)
        if ruta:
            try:
                if "Update.exe" in ruta and "Discord" in ruta:
                    subprocess.Popen(f'"{ruta}" --processStart Discord.exe', shell=True)
                else:
                    subprocess.Popen(f'"{ruta}"', shell=True)
                self.lia.hablar(f"Abriendo {nombre}.")
                self.lia.registrar_actividad(f"Abrió {nombre}")
                return
            except Exception as e:
                print(f"❌ Error al lanzar {ruta}: {e}")

        # 2. Shell directo
        try:
            subprocess.Popen(nombre_limpio, shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.lia.hablar(f"Intentando abrir {nombre}.")
            self.lia.registrar_actividad(f"Abrió (shell) {nombre}")
            return
        except Exception:
            pass

        # 3. Menú de Inicio
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
                        return

        self.lia.hablar(f"No encontré {nombre} en el sistema.")
        print(f"❌ App no encontrada: {nombre}")

    def open_url(self, url: str, nombre: str):
        """Abre una URL en el navegador predeterminado."""
        try:
            webbrowser.open(url)
            self.lia.hablar(f"Abriendo {nombre}.")
            self.lia.registrar_actividad(f"Abrió {nombre}")
        except Exception as e:
            print(f"❌ Error al abrir {nombre}: {e}")

    def cerrar_todo(self):
        """Termina procesos de las aplicaciones de trabajo."""
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
        """Busca y abre un archivo por nombre parcial en Descargas."""
        carpeta = os.path.join(os.path.expanduser("~"), "Downloads")
        for root, _, files in os.walk(carpeta):
            for archivo in files:
                if nombre.lower() in archivo.lower():
                    os.startfile(os.path.join(root, archivo))
                    self.lia.hablar(f"Abriendo {archivo}.")
                    self.lia.registrar_actividad(f"Abrió desde Descargas: {archivo}")
                    return
        self.lia.hablar(f"No encontré {nombre} en Descargas.")

    def abrir_carpeta(self, ruta: str):
        """Abre una carpeta en el explorador de archivos."""
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
        except Exception as e:
            self.lia.hablar("Error al abrir carpeta.")
            print(f"❌ {e}")

    # ════════════════════════════════════════════════════════
    #  MODOS DE TRABAJO
    # ════════════════════════════════════════════════════════

    def modo_estudio(self):
        print("\n📚 MODO ESTUDIO")
        self.lia.hablar("Activando modo estudio.")
        self.open_url("https://chat.openai.com", "ChatGPT")
        time.sleep(0.4)
        self.open_url("https://web.whatsapp.com", "WhatsApp")
        self.lia.registrar_actividad("Modo Estudio")

    def modo_programacion(self):
        print("\n💻 MODO CÓDIGO")
        self.lia.hablar("Iniciando entorno de programación.")
        self.open_application("vscode")
        time.sleep(0.4)
        self.open_url("https://github.com", "GitHub")
        time.sleep(0.4)
        self.open_application("spotify")
        self.lia.registrar_actividad("Modo Programación")

    def modo_juego(self):
        print("\n🎮 MODO JUEGO")
        self.lia.hablar("Todo listo para jugar.")
        self.open_application("discord")
        time.sleep(0.5)
        self.abrir_desde_descargas("TimerResolution")
        self.lia.registrar_actividad("Modo Juego")

    # ════════════════════════════════════════════════════════
    #  INFORMACIÓN DEL SISTEMA
    # ════════════════════════════════════════════════════════

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
        except Exception as e:
            self.lia.hablar("Error al leer el sistema.")
            print(f"❌ {e}")

    def obtener_uso_disco(self):
        if not _PSUTIL:
            self.lia.hablar("psutil no está instalado.")
            return
        try:
            disco    = psutil.disk_usage("/")
            libre_gb = disco.free  / (1024 ** 3)
            total_gb = disco.total / (1024 ** 3)
            self.lia.hablar(
                f"Disco al {disco.percent:.0f} por ciento. "
                f"{libre_gb:.0f} de {total_gb:.0f} GB libres."
            )
            self.lia.registrar_actividad("Consultó uso de disco")
        except Exception as e:
            self.lia.hablar("Error al leer el disco.")
            print(f"❌ {e}")

    def obtener_procesos_pesados(self, top_n: int = 5):
        if not _PSUTIL:
            self.lia.hablar("psutil no está instalado.")
            return
        try:
            procs = sorted(
                psutil.process_iter(['name', 'memory_percent']),
                key=lambda p: p.info.get('memory_percent') or 0,
                reverse=True
            )[:top_n]
            self.lia.hablar("Procesos más pesados:")
            for p in procs:
                mem = p.info.get('memory_percent') or 0
                self.lia.hablar(f"{p.info['name']}: {mem:.1f} por ciento")
                time.sleep(0.2)
            self.lia.registrar_actividad("Consultó procesos")
        except Exception as e:
            self.lia.hablar("Error al leer procesos.")
            print(f"❌ {e}")

    # ════════════════════════════════════════════════════════
    #  CONTROL DE ENERGÍA Y BLOQUEO
    # ════════════════════════════════════════════════════════

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

    # ════════════════════════════════════════════════════════
    #  NOTIFICACIONES TOAST  (usadas por Lia y mod_memoria)
    # ════════════════════════════════════════════════════════

    def notificar(self, titulo: str, mensaje: str):
        """Notificación toast en Windows via PowerShell. Sin dependencias extra."""
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
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass