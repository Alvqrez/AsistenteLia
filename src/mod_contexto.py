#!/usr/bin/env python3

import json
import logging
import os
import subprocess
import time
from collections import deque
from typing import Optional

logger = logging.getLogger("lia.contexto")


class ContextoConversacional:

    EXTENSIONES_EJECUTABLES = {
        ".py":   ["python", "{ruta}"],
        ".js":   ["node",   "{ruta}"],
        ".ts":   ["npx",    "ts-node", "{ruta}"],
        ".sh":   ["bash",   "{ruta}"],
        ".bat":  ["{ruta}"],
        ".exe":  ["{ruta}"],
        ".ps1":  ["powershell", "-File", "{ruta}"],
    }

    INDICADORES_PROYECTO = {
        "package.json":      ["npm", "start"],
        "requirements.txt":  ["python", "main.py"],
        "main.py":           ["python", "main.py"],
        "manage.py":         ["python", "manage.py", "runserver"],
        "Cargo.toml":        ["cargo", "run"],
        "pom.xml":           ["mvn", "spring-boot:run"],
        "go.mod":            ["go", "run", "."],
    }

    @staticmethod
    def detectar_comando_proyecto(ruta: str):
        """
        Modo JARVIS: detecta el tipo de proyecto en `ruta` y devuelve
        (comando_str, tipo) o (None, None). Para package.json inspecciona
        dependencias/scripts para distinguir Vite / React / Node genérico.
        """
        def _existe(nombre):
            return os.path.exists(os.path.join(ruta, nombre))

        if _existe("pubspec.yaml"):
            return "flutter run", "Flutter"
        if _existe("package.json"):
            try:
                with open(os.path.join(ruta, "package.json"), encoding="utf-8") as f:
                    pkg = json.load(f)
            except Exception:
                pkg = {}
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            scripts = pkg.get("scripts", {})
            if "vite" in deps or "vite" in str(scripts.get("dev", "")):
                return "npm run dev", "Vite"
            if "next" in deps:
                return "npm run dev", "Next.js"
            if "react-scripts" in deps:
                return "npm start", "React"
            if "dev" in scripts:
                return "npm run dev", "Node"
            if "start" in scripts:
                return "npm start", "Node"
            return "npm run dev", "Node"
        if _existe("manage.py"):
            return "python manage.py runserver", "Django"
        if _existe("main.py"):
            return "python main.py", "Python"
        if _existe("app.py"):
            return "python app.py", "Python"
        if _existe("Cargo.toml"):
            return "cargo run", "Rust"
        if _existe("go.mod"):
            return "go run .", "Go"
        if _existe("pom.xml"):
            return "mvn spring-boot:run", "Java"
        if _existe("requirements.txt"):
            return "python main.py", "Python"
        return None, None

    @staticmethod
    def ejecutar_en_terminal(comando: str, ruta: str):
        """Lanza `comando` en una ventana de terminal visible, con cwd=ruta."""
        subprocess.Popen(f'start "Lia" cmd /k "{comando}"', cwd=ruta, shell=True)

    def __init__(self, parent_lia):
        self.lia = parent_lia

        self.historial_comandos: deque = deque(maxlen=20)
        self.proyecto_activo: Optional[dict]  = None
        self.ultimo_archivo:   Optional[str]  = None
        self.ultima_url:       Optional[str]  = None
        self.ultimo_proceso:   Optional[str]  = None
        self.ultimos_procesos_abiertos: list  = []
        self.ultimas_urls_abiertas:     list  = []

    def registrar_comando(self, cmd: str):
        self.historial_comandos.append({"cmd": cmd, "ts": time.time()})

    def registrar_apertura_app(self, nombre_proceso: str):
        self.ultimo_proceso = nombre_proceso
        if nombre_proceso not in self.ultimos_procesos_abiertos:
            self.ultimos_procesos_abiertos.append(nombre_proceso)

    def registrar_apertura_url(self, url: str):
        self.ultima_url = url
        if url not in self.ultimas_urls_abiertas:
            self.ultimas_urls_abiertas.append(url)

    def registrar_apertura_archivo(self, ruta: str):
        self.ultimo_archivo = ruta

    def limpiar_ultimo_modo(self):
        self.ultimos_procesos_abiertos.clear()
        self.ultimas_urls_abiertas.clear()

    def establecer_proyecto(self, nombre: str, ruta: Optional[str] = None):
        if ruta is None:
            ruta = self._buscar_carpeta_proyecto(nombre)

        if ruta:
            self.proyecto_activo = {"nombre": nombre, "ruta": ruta}
            self.lia.hablar(f"Proyecto activo: {nombre}.")
            logger.info("Proyecto activo: %s en %s", nombre, ruta)
        else:
            self.proyecto_activo = {"nombre": nombre, "ruta": None}
            self.lia.hablar(f"Recordé que estás trabajando en {nombre}, aunque no encontré la carpeta.")

    def _buscar_carpeta_proyecto(self, nombre: str) -> Optional[str]:
        carpetas_raiz = [
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Downloads"),
            os.path.expandvars("%USERPROFILE%/source"),
            os.path.expandvars("%USERPROFILE%/repos"),
            os.path.expandvars("%USERPROFILE%/projects"),
            os.path.expandvars("%USERPROFILE%/dev"),
            "C:/dev",
            "C:/repos",
        ]
        nombre_lower = nombre.lower()
        for raiz in carpetas_raiz:
            if not os.path.exists(raiz):
                continue
            try:
                for entrada in os.scandir(raiz):
                    if entrada.is_dir() and nombre_lower in entrada.name.lower():
                        return entrada.path
            except PermissionError:
                continue
        return None

    def abrir_proyecto(self, nombre: str):
        self.establecer_proyecto(nombre)
        if self.proyecto_activo and self.proyecto_activo.get("ruta"):
            ruta = self.proyecto_activo["ruta"]
            try:
                subprocess.Popen(["code", ruta])
                self.lia.hablar(f"Abriendo proyecto {nombre} en VS Code.")
            except Exception:
                try:
                    os.startfile(ruta)
                    self.lia.hablar(f"Abriendo carpeta de {nombre}.")
                except Exception as ex:
                    logger.error("No se pudo abrir el proyecto: %s", ex)
                    self.lia.hablar("No pude abrir la carpeta del proyecto.")
        else:
            self.lia.hablar(f"No encontré la carpeta del proyecto {nombre}.")

    def ejecutar_ultimo(self):
        if self.proyecto_activo and self.proyecto_activo.get("ruta"):
            self._ejecutar_proyecto(self.proyecto_activo["ruta"])
            return
        if self.ultimo_archivo:
            self._ejecutar_archivo(self.ultimo_archivo)
            return
        self.lia.hablar("No sé qué ejecutar. Primero dime en qué proyecto estás trabajando.")

    def _ejecutar_proyecto(self, ruta: str):
        # Modo JARVIS: detecta Flutter/Vite/React/Node/Python/etc. y lanza el
        # comando correcto en una terminal visible (npm/flutter necesitan
        # consola; Popen sin shell fallaba con npm.cmd en Windows).
        comando, tipo = self.detectar_comando_proyecto(ruta)
        if comando is None:
            self.lia.hablar("No reconocí el tipo de proyecto para ejecutarlo.")
            return
        try:
            self.ejecutar_en_terminal(comando, ruta)
            self.lia.hablar(f"Proyecto {tipo} detectado. Ejecutando {comando}.")
            logger.info("Ejecutando proyecto %s en %s con '%s'", tipo, ruta, comando)
        except Exception as ex:
            logger.error("Error al ejecutar proyecto: %s", ex)
            self.lia.hablar("Hubo un error al ejecutar el proyecto.")

    def _ejecutar_archivo(self, ruta: str):
        _, ext = os.path.splitext(ruta.lower())
        cmd_template = self.EXTENSIONES_EJECUTABLES.get(ext)
        if not cmd_template:
            try:
                os.startfile(ruta)
                self.lia.hablar("Abriendo el archivo.")
            except Exception as ex:
                logger.error("No se pudo abrir el archivo: %s", ex)
                self.lia.hablar("No pude abrir el archivo.")
            return
        cmd = [c.replace("{ruta}", ruta) for c in cmd_template]
        try:
            subprocess.Popen(cmd, shell=False)
            self.lia.hablar("Ejecutando el archivo.")
        except Exception as ex:
            logger.error("Error al ejecutar archivo: %s", ex)
            self.lia.hablar("Hubo un error al ejecutar el archivo.")

    def abrir_ultimo(self):
        if self.ultimo_archivo and os.path.exists(self.ultimo_archivo):
            try:
                os.startfile(self.ultimo_archivo)
                self.lia.hablar("Abriendo lo último que usamos.")
                return
            except Exception:
                pass
        if self.ultima_url:
            import webbrowser
            webbrowser.open(self.ultima_url)
            self.lia.hablar("Abriendo de nuevo.")
            return
        if self.ultimo_proceso:
            self.lia.sistema.open_application(self.ultimo_proceso)
            return
        self.lia.hablar("No tengo nada reciente para abrir.")

    def cerrar_ultimo(self):
        if self.ultimo_proceso:
            nombre = self.ultimo_proceso
            proc_exe = nombre if nombre.endswith(".exe") else nombre + ".exe"
            try:
                subprocess.run(
                    ["taskkill", "/f", "/im", proc_exe],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                self.lia.hablar(f"Cerré {nombre}.")
                logger.info("Cerrado proceso: %s", proc_exe)
            except Exception as ex:
                logger.error("Error al cerrar %s: %s", proc_exe, ex)
                self.lia.hablar(f"No pude cerrar {nombre}.")
        else:
            self.lia.hablar("No sé qué cerrar.")

    def abortar(self):
        cerrados = []
        for proc in list(self.ultimos_procesos_abiertos):
            proc_exe = proc if proc.endswith(".exe") else proc + ".exe"
            result = subprocess.run(
                ["taskkill", "/f", "/im", proc_exe],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                cerrados.append(proc)

        if cerrados:
            self.lia.hablar(f"Abortado. Cerré {', '.join(cerrados)}.")
        else:
            self.lia.hablar("No hay nada que abortar.")

        self.limpiar_ultimo_modo()

    def que_estoy_haciendo(self):
        partes = []
        if self.proyecto_activo:
            partes.append(f"Estás trabajando en {self.proyecto_activo['nombre']}.")
        if self.ultimo_archivo:
            partes.append(f"Último archivo: {os.path.basename(self.ultimo_archivo)}.")
        if self.ultimo_proceso:
            partes.append(f"Última app abierta: {self.ultimo_proceso}.")
        if partes:
            for p in partes:
                self.lia.hablar(p)
        else:
            self.lia.hablar("No tengo contexto de lo que estás haciendo aún.")