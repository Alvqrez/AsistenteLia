#!/usr/bin/env python3
"""
mod_dev.py  –  Módulo de Desarrollo
Responsabilidades:
  · Operaciones Git (status, commit, push, ramas)
  · Apertura de herramientas y recursos de desarrollo
  · Utilidades para programadores
"""

import subprocess
import os
import time


class DevTools:
    """
    Herramientas para desarrolladores.
    Recibe 'parent_lia' para hablar() y registrar_actividad().
    """

    def __init__(self, parent_lia):
        self.lia = parent_lia

    # ════════════════════════════════════════════════════════
    #  GIT
    # ════════════════════════════════════════════════════════

    def _git(self, args: list, ruta: str = ".", timeout: int = 30) -> subprocess.CompletedProcess | None:
        """Ejecuta un comando git y retorna el resultado."""
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
        except Exception as e:
            self.lia.hablar("Error al ejecutar Git.")
            print(f"❌ {e}")
            return None

    def estado_git(self, ruta: str = "."):
        """Dice el estado del repositorio (git status)."""
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
        """
        Hace commit de los cambios staged.
        Nota: debes ejecutar 'git add' antes de llamar a esto.
        """
        res = self._git(["commit", "-m", mensaje], ruta)
        if res is None:
            return
        if res.returncode == 0:
            self.lia.hablar(f"Commit realizado: {mensaje[:50]}.")
            self.lia.registrar_actividad(f"Git commit: {mensaje[:30]}")
        else:
            self.lia.hablar("Error al hacer commit.")
            print(f"❌ {res.stderr}")

    def hacer_push(self, rama: str = "main", ruta: str = "."):
        """Hace push a origin/rama."""
        self.lia.hablar(f"Haciendo push a {rama}.")
        res = self._git(["push", "origin", rama], ruta, timeout=60)
        if res is None:
            return
        if res.returncode == 0:
            self.lia.hablar(f"Push completado a {rama}.")
            self.lia.registrar_actividad(f"Git push a {rama}")
        else:
            self.lia.hablar("Error al hacer push. Revisa tu conexión o credenciales.")
            print(f"❌ {res.stderr}")

    def hacer_pull(self, rama: str = "main", ruta: str = "."):
        """Hace pull desde origin/rama."""
        self.lia.hablar(f"Actualizando desde {rama}.")
        res = self._git(["pull", "origin", rama], ruta, timeout=60)
        if res is None:
            return
        if res.returncode == 0:
            self.lia.hablar(f"Repositorio actualizado desde {rama}.")
            self.lia.registrar_actividad(f"Git pull desde {rama}")
        else:
            self.lia.hablar("Error al hacer pull.")
            print(f"❌ {res.stderr}")

    def listar_ramas(self, ruta: str = "."):
        """Lista y dice las ramas del repositorio."""
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
        """Crea y activa una nueva rama."""
        res = self._git(["checkout", "-b", nombre], ruta)
        if res is None:
            return
        if res.returncode == 0:
            self.lia.hablar(f"Rama '{nombre}' creada y activada.")
            self.lia.registrar_actividad(f"Git: creó rama {nombre}")
        else:
            self.lia.hablar(f"Error al crear rama: {res.stderr[:80]}")

    def cambiar_rama(self, nombre: str, ruta: str = "."):
        """Cambia a una rama existente."""
        res = self._git(["checkout", nombre], ruta)
        if res is None:
            return
        if res.returncode == 0:
            self.lia.hablar(f"Cambiado a rama {nombre}.")
            self.lia.registrar_actividad(f"Git: cambió a rama {nombre}")
        else:
            self.lia.hablar(f"Error: {res.stderr[:80]}")

    def clonar_repositorio(self, url: str, directorio: str = None):
        """Clona un repositorio remoto."""
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
                print(f"❌ {res.stderr}")
        except subprocess.TimeoutExpired:
            self.lia.hablar("El clone tardó demasiado.")
        except Exception as e:
            self.lia.hablar("Error al clonar repositorio.")
            print(f"❌ {e}")

    def log_reciente(self, n: int = 5, ruta: str = "."):
        """Dice los últimos N commits."""
        res = self._git(
            ["log", f"--oneline", f"-{n}"],
            ruta
        )
        if res is None:
            return
        commits = [l for l in res.stdout.split("\n") if l.strip()]
        if not commits:
            self.lia.hablar("No hay commits en este repositorio.")
            return
        self.lia.hablar(f"Últimos {len(commits)} commits:")
        for c in commits:
            # El hash ocupa los primeros 7 caracteres
            msg = c[8:] if len(c) > 8 else c
            self.lia.hablar(msg[:80])
            time.sleep(0.25)
        self.lia.registrar_actividad("Git: log reciente")

    # ════════════════════════════════════════════════════════
    #  HERRAMIENTAS Y RECURSOS WEB DE DESARROLLO
    # ════════════════════════════════════════════════════════

    def abrir_github(self):
        self.lia.sistema.open_url("https://github.com", "GitHub")

    def abrir_gitlab(self):
        self.lia.sistema.open_url("https://gitlab.com", "GitLab")

    def abrir_stackoverflow(self):
        self.lia.sistema.open_url("https://stackoverflow.com", "Stack Overflow")

    def abrir_docs_python(self):
        self.lia.sistema.open_url("https://docs.python.org/3/", "Documentación Python")

    def abrir_mdn(self):
        self.lia.sistema.open_url("https://developer.mozilla.org/", "MDN Web Docs")

    def abrir_pypi(self):
        self.lia.sistema.open_url("https://pypi.org/", "PyPI")

    def abrir_npm(self):
        self.lia.sistema.open_url("https://www.npmjs.com/", "NPM")

    def abrir_vscode(self, carpeta: str = None):
        """Abre VS Code, opcionalmente con una carpeta específica."""
        if carpeta and os.path.exists(carpeta):
            try:
                subprocess.Popen(["code", carpeta], shell=True)
                self.lia.hablar(f"Abriendo VS Code con {os.path.basename(carpeta)}.")
                self.lia.registrar_actividad(f"Abrió VS Code: {carpeta}")
                return
            except Exception:
                pass
        self.lia.sistema.open_application("vscode")