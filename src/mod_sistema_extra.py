#!/usr/bin/env python3
# mod_sistema_extra.py — Operaciones de archivos y carpetas por voz.
# Métodos añadidos al SystemTools original en mod_sistema.py.
# Se importa y usa desde Lia.py via mixin o composición directa.

import logging
import os
import subprocess
import platform

logger = logging.getLogger("lia.sistema_extra")


class FileOpsTools:
    """Mixin de operaciones de archivo/carpeta. Requiere self.lia."""

    # Extensiones soportadas para creación de archivos
    _EXT_MAP = {
        "python":      "py",
        "py":          "py",
        "javascript":  "js",
        "js":          "js",
        "typescript":  "ts",
        "ts":          "ts",
        "html":        "html",
        "css":         "css",
        "json":        "json",
        "texto":       "txt",
        "txt":         "txt",
        "markdown":    "md",
        "md":          "md",
        "bash":        "sh",
        "sh":          "sh",
        "java":        "java",
        "c":           "c",
        "cpp":         "cpp",
        "csharp":      "cs",
        "cs":          "cs",
        "ruby":        "rb",
        "php":         "php",
        "yaml":        "yaml",
        "xml":         "xml",
    }

    # Contenido inicial por extensión
    _TEMPLATES = {
        "py":   "#!/usr/bin/env python3\n\n",
        "js":   "// archivo JavaScript\n\n",
        "ts":   "// archivo TypeScript\n\n",
        "html": "<!DOCTYPE html>\n<html lang=\"es\">\n<head>\n  <meta charset=\"UTF-8\">\n  <title>Nuevo</title>\n</head>\n<body>\n\n</body>\n</html>\n",
        "css":  "/* estilos */\n\n",
        "json": "{}\n",
        "md":   "# Título\n\n",
        "sh":   "#!/bin/bash\n\n",
        "txt":  "",
    }

    def _resolver_carpeta_destino(self, nombre_carpeta: str) -> str | None:
        """Resuelve un nombre de carpeta a una ruta absoluta."""
        nombre_l = nombre_carpeta.lower().strip()
        # Mapa conocido del sistema
        conocidas = getattr(self, "CARPETAS_MAP", {})
        if nombre_l in conocidas:
            return conocidas[nombre_l]
        # Ruta absoluta o relativa explícita
        if os.path.isabs(nombre_carpeta) or os.path.exists(nombre_carpeta):
            return os.path.abspath(nombre_carpeta)
        # Buscar en escritorio, documentos, raíz de usuario
        candidatos = [
            os.path.join(os.path.expanduser("~"), "Desktop",    nombre_carpeta),
            os.path.join(os.path.expanduser("~"), "Documents",  nombre_carpeta),
            os.path.join(os.path.expanduser("~"), "Projects",   nombre_carpeta),
            os.path.join(os.path.expanduser("~"), "dev",        nombre_carpeta),
            os.path.join(os.path.expanduser("~"),               nombre_carpeta),
        ]
        for c in candidatos:
            if os.path.exists(c):
                return c
        return None

    def crear_archivo(self, tipo: str, nombre: str, carpeta: str):
        """Crea un archivo vacío (con plantilla) del tipo indicado."""
        ext = self._EXT_MAP.get(tipo.lower().strip(), tipo.lower().strip())
        nombre_limpio = nombre.strip().replace(" ", "_") if nombre else f"nuevo_archivo"
        if not nombre_limpio.endswith(f".{ext}"):
            nombre_limpio = f"{nombre_limpio}.{ext}"

        ruta_carpeta = self._resolver_carpeta_destino(carpeta)
        if not ruta_carpeta:
            # Usa escritorio como fallback
            ruta_carpeta = os.path.expanduser("~/Desktop")
            self.lia.hablar(f"No encontré la carpeta '{carpeta}'. Crearé el archivo en el Escritorio.")

        os.makedirs(ruta_carpeta, exist_ok=True)
        ruta_archivo = os.path.join(ruta_carpeta, nombre_limpio)

        if os.path.exists(ruta_archivo):
            self.lia.hablar(f"Ya existe '{nombre_limpio}' en esa carpeta.")
            return

        contenido = self._TEMPLATES.get(ext, "")
        try:
            with open(ruta_archivo, "w", encoding="utf-8") as f:
                f.write(contenido)
            self.lia.hablar(f"Archivo '{nombre_limpio}' creado en {os.path.basename(ruta_carpeta)}.")
            self.lia.registrar_actividad(f"Creó archivo: {nombre_limpio}")
            # Abrir en VS Code si está disponible
            try:
                subprocess.Popen(f'code "{ruta_archivo}"', shell=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        except Exception as ex:
            logger.error("Error al crear archivo '%s': %s", ruta_archivo, ex)
            self.lia.hablar("No pude crear el archivo.")

    def crear_carpeta(self, nombre: str, ruta_padre: str):
        """Crea una nueva carpeta."""
        nombre_limpio = nombre.strip().replace(" ", "_") if nombre else "nueva_carpeta"
        ruta_padre_resuelta = self._resolver_carpeta_destino(ruta_padre)
        if not ruta_padre_resuelta:
            ruta_padre_resuelta = os.path.expanduser("~/Desktop")
            self.lia.hablar(f"No encontré '{ruta_padre}'. Crearé la carpeta en el Escritorio.")

        ruta_nueva = os.path.join(ruta_padre_resuelta, nombre_limpio)
        if os.path.exists(ruta_nueva):
            self.lia.hablar(f"Ya existe una carpeta llamada '{nombre_limpio}' ahí.")
            return
        try:
            os.makedirs(ruta_nueva)
            self.lia.hablar(f"Carpeta '{nombre_limpio}' creada.")
            self.lia.registrar_actividad(f"Creó carpeta: {ruta_nueva}")
            # Abrir en explorador
            try:
                if platform.system() == "Windows":
                    os.startfile(ruta_nueva)
                elif platform.system() == "Darwin":
                    subprocess.Popen(["open", ruta_nueva])
                else:
                    subprocess.Popen(["xdg-open", ruta_nueva])
            except Exception:
                pass
        except Exception as ex:
            logger.error("Error al crear carpeta '%s': %s", ruta_nueva, ex)
            self.lia.hablar("No pude crear la carpeta.")

    def abrir_carpeta_conocida(self, nombre: str):
        """Abre una carpeta del sistema (documentos, descargas, etc.)."""
        conocidas = getattr(self, "CARPETAS_MAP", {})
        ruta = conocidas.get(nombre.lower().strip())
        if not ruta:
            ruta = self._resolver_carpeta_destino(nombre)
        if not ruta or not os.path.exists(ruta):
            self.lia.hablar(f"No encontré la carpeta '{nombre}'.")
            return
        try:
            if platform.system() == "Windows":
                os.startfile(ruta)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", ruta])
            else:
                subprocess.Popen(["xdg-open", ruta])
            self.lia.hablar(f"Abriendo {nombre}.")
            self.lia.registrar_actividad(f"Abrió carpeta: {nombre}")
        except Exception as ex:
            logger.error("Error al abrir carpeta '%s': %s", ruta, ex)
            self.lia.hablar("No pude abrir la carpeta.")
