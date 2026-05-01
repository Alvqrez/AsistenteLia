#!/usr/bin/env python3

import subprocess
import os
import time
from typing import Optional


class DevTools:

    def __init__(self, parent_lia):
        self.lia = parent_lia

    def _git(self, args: list, ruta: str = ".",
             timeout: int = 30) -> Optional[subprocess.CompletedProcess]:
        if not os.path.exists(os.path.join(ruta, ".git")):
            self.lia.hablar("Esta carpeta no es un repositorio Git.")
            return None
        try:
            return subprocess.run(
                ["git"] + args,
                cwd=ruta, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            self.lia.hablar("El comando Git tardó demasiado.")
            return None
        except Exception as ex:
            self.lia.hablar("Error al ejecutar Git.")
            print(f"Error git: {ex}")
            return None

    def estado_git(self, ruta: str = "."):
        res = self._git(["status"], ruta)
        if res is None:
            return
        out = res.stdout
        if "nothing to commit" in out:
            self.lia.hablar("Todo está committeado.")
        elif "Changes not staged" in out:
            self.lia.hablar("Hay cambios sin stagear.")
        elif "Untracked files" in out:
            self.lia.hablar("Hay archivos sin seguimiento.")
        else:
            self.lia.hablar("El repositorio tiene cambios pendientes.")
        self.lia.registrar_actividad("Git status")

    def hacer_commit(self, mensaje: str, ruta: str = "."):
        res = self._git(["commit", "-m", mensaje], ruta)
        if res is None:
            return
        if res.returncode == 0:
            self.lia.hablar(f"Commit realizado: {mensaje[:50]}.")
            self.lia.registrar_actividad(f"Git commit: {mensaje[:30]}")
        else:
            self.lia.hablar("Error al hacer commit.")
            print(f"Git error: {res.stderr}")

    def hacer_push(self, rama: str = "main", ruta: str = "."):
        self.lia.hablar(f"Haciendo push a {rama}.")
        res = self._git(["push", "origin", rama], ruta, timeout=60)
        if res is None:
            return
        if res.returncode == 0:
            self.lia.hablar(f"Push completado a {rama}.")
            self.lia.registrar_actividad(f"Git push a {rama}")
        else:
            self.lia.hablar("Error al hacer push.")
            print(f"Git error: {res.stderr}")

    def hacer_pull(self, rama: str = "main", ruta: str = "."):
        self.lia.hablar(f"Actualizando desde {rama}.")
        res = self._git(["pull", "origin", rama], ruta, timeout=60)
        if res is None:
            return
        if res.returncode == 0:
            self.lia.hablar(f"Repositorio actualizado desde {rama}.")
            self.lia.registrar_actividad(f"Git pull desde {rama}")
        else:
            self.lia.hablar("Error al hacer pull.")
            print(f"Git error: {res.stderr}")

    def listar_ramas(self, ruta: str = "."):
        res = self._git(["branch", "-a"], ruta)
        if res is None:
            return
        ramas = [r.strip() for r in res.stdout.split("\n") if r.strip()]
        self.lia.hablar(f"Tienes {len(ramas)} ramas.")
        for r in ramas[:5]:
            etiqueta = "rama actual:" if r.startswith("*") else ""
            self.lia.hablar(f"{etiqueta} {r.replace('*', '').strip()}")
            time.sleep(0.25)
        self.lia.registrar_actividad("Git: listó ramas")

    def crear_rama(self, nombre: str, ruta: str = "."):
        res = self._git(["checkout", "-b", nombre], ruta)
        if res is None:
            return
        if res.returncode == 0:
            self.lia.hablar(f"Rama '{nombre}' creada y activada.")
            self.lia.registrar_actividad(f"Git: creó rama {nombre}")
        else:
            self.lia.hablar("Error al crear la rama.")
            print(f"Git error: {res.stderr}")

    def cambiar_rama(self, nombre: str, ruta: str = "."):
        res = self._git(["checkout", nombre], ruta)
        if res is None:
            return
        if res.returncode == 0:
            self.lia.hablar(f"Cambiado a rama {nombre}.")
            self.lia.registrar_actividad(f"Git: cambió a rama {nombre}")
        else:
            self.lia.hablar("Error al cambiar de rama.")
            print(f"Git error: {res.stderr}")

    def clonar_repositorio(self, url: str, directorio: Optional[str] = None):
        if directorio is None:
            directorio = url.split("/")[-1].replace(".git", "")
        self.lia.hablar(f"Clonando en {directorio}.")
        try:
            res = subprocess.run(
                ["git", "clone", url, directorio],
                capture_output=True, text=True, timeout=120
            )
            if res.returncode == 0:
                self.lia.hablar("Repositorio clonado.")
                self.lia.registrar_actividad(f"Git clone: {url}")
            else:
                self.lia.hablar("Error al clonar.")
                print(f"Git error: {res.stderr}")
        except subprocess.TimeoutExpired:
            self.lia.hablar("El clone tardó demasiado.")
        except Exception as ex:
            self.lia.hablar("Error al clonar repositorio.")
            print(f"Error: {ex}")

    def log_reciente(self, n: int = 5, ruta: str = "."):
        res = self._git(["log", "--oneline", f"-{n}"], ruta)
        if res is None:
            return
        commits = [l for l in res.stdout.split("\n") if l.strip()]
        if not commits:
            self.lia.hablar("No hay commits en este repositorio.")
            return
        self.lia.hablar(f"Últimos {len(commits)} commits:")
        for c in commits:
            msg = c[8:] if len(c) > 8 else c
            self.lia.hablar(msg[:80])
            time.sleep(0.25)
        self.lia.registrar_actividad("Git: log reciente")

    def crear_proyecto_react(self, nombre_carpeta: str, ruta_base: Optional[str] = None):
        """
        Crea un proyecto React con Vite en la carpeta indicada.
        Comando: "Lia, crea proyecto React en [carpeta]"
        Requiere Node.js y npm instalados.
        """
        if not nombre_carpeta:
            self.lia.hablar("Necesito el nombre de la carpeta para el proyecto.")
            return

        nombre_limpio = nombre_carpeta.strip().replace(" ", "-").lower()

        if ruta_base is None:
            posibles = [
                os.path.expanduser("~/Documents"),
                os.path.expanduser("~/Desktop"),
                os.path.expandvars("%USERPROFILE%/projects"),
                os.path.expandvars("%USERPROFILE%/dev"),
            ]
            ruta_base = next((r for r in posibles if os.path.exists(r)),
                             os.path.expanduser("~"))

        ruta_destino = os.path.join(ruta_base, nombre_limpio)

        if os.path.exists(ruta_destino):
            self.lia.hablar(f"Ya existe una carpeta llamada {nombre_limpio}. Elige otro nombre.")
            return

        self.lia.hablar(f"Creando proyecto React en {nombre_limpio}. Esto puede tardar un momento.")
        print(f"Ejecutando: npm create vite@latest {nombre_limpio} -- --template react")
        print(f"En carpeta: {ruta_base}")

        try:
            proc = subprocess.run(
                ["npm", "create", "vite@latest", nombre_limpio,
                 "--", "--template", "react"],
                cwd=ruta_base,
                input="y\n",
                capture_output=True,
                text=True,
                timeout=120,
                shell=True
            )

            if proc.returncode != 0:
                print(f"stdout: {proc.stdout}")
                print(f"stderr: {proc.stderr}")
                self.lia.hablar("Hubo un error al crear el proyecto. Verifica que tengas Node.js instalado.")
                return

            self.lia.hablar("Proyecto creado. Instalando dependencias.")

            proc2 = subprocess.run(
                ["npm", "install"],
                cwd=ruta_destino,
                capture_output=True,
                text=True,
                timeout=180,
                shell=True
            )

            if proc2.returncode == 0:
                self.lia.hablar(f"Listo. Proyecto React '{nombre_limpio}' creado correctamente.")
                try:
                    subprocess.Popen(f'code "{ruta_destino}"', shell=True)
                    self.lia.hablar("Lo abrí en VS Code.")
                except Exception:
                    pass
                self.lia.registrar_actividad(f"Creó proyecto React: {nombre_limpio}")
            else:
                self.lia.hablar("Proyecto creado pero falló la instalación de dependencias. Ejecuta npm install manualmente.")
                print(f"npm install error: {proc2.stderr}")

        except subprocess.TimeoutExpired:
            self.lia.hablar("La creación tardó demasiado. Inténtalo manualmente.")
        except FileNotFoundError:
            self.lia.hablar("No encontré npm. Instala Node.js primero.")
        except Exception as ex:
            self.lia.hablar("Error al crear el proyecto React.")
            print(f"Error: {ex}")

    def abrir_github(self):
        self.lia.sistema.open_url("https://github.com", "GitHub")

    def abrir_stackoverflow(self):
        self.lia.sistema.open_url("https://stackoverflow.com", "Stack Overflow")

    def abrir_docs_python(self):
        self.lia.sistema.open_url("https://docs.python.org/3/", "Documentación Python")

    def abrir_mdn(self):
        self.lia.sistema.open_url("https://developer.mozilla.org/", "MDN Web Docs")

    def abrir_vscode(self, carpeta: Optional[str] = None):
        if carpeta and os.path.exists(carpeta):
            try:
                subprocess.Popen(["code", carpeta], shell=True)
                self.lia.hablar(f"Abriendo VS Code con {os.path.basename(carpeta)}.")
                self.lia.registrar_actividad(f"Abrió VS Code: {carpeta}")
                return
            except Exception as ex:
                print(f"Error VS Code: {ex}")
        self.lia.sistema.open_application("vscode")