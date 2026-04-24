import os
import subprocess
import shutil


class ModuloDev:
    def __init__(self, funcion_hablar):
        self.hablar = funcion_hablar
        # Detecta tu carpeta de Proyectos automáticamente basada en tu usuario
        self.ruta_base = os.path.expandvars(r"%USERPROFILE%\Documents\Proyectos")
        os.makedirs(self.ruta_base, exist_ok=True)

    def crear_proyecto(self, lenguaje, nombre):
        ruta_proyecto = os.path.join(self.ruta_base, nombre)

        try:
            os.makedirs(ruta_proyecto, exist_ok=True)

            if "python" in lenguaje.lower():
                with open(os.path.join(ruta_proyecto, "main.py"), "w", encoding="utf-8") as f:
                    f.write('print("Hola, Lia te ha preparado este entorno de Python.")\n')
                self.hablar(f"Proyecto de Python {nombre} inicializado y listo.")

            elif "javascript" in lenguaje.lower() or "node" in lenguaje.lower():
                with open(os.path.join(ruta_proyecto, "index.js"), "w", encoding="utf-8") as f:
                    f.write('console.log("Entorno de Node JS listo.");\n')
                self.hablar(f"Proyecto de Node {nombre} inicializado.")
            else:
                self.hablar(f"Carpeta de proyecto {nombre} creada.")

            # Abre VS Code directamente en la carpeta creada
            subprocess.Popen(["code", "."], cwd=ruta_proyecto, shell=True)

        except Exception as e:
            self.hablar(f"Error al crear el proyecto. Detalles: {e}")

    def gestionar_carpeta(self, accion, nombre):
        ruta = os.path.join(self.ruta_base, nombre)
        try:
            if accion == "crea":
                os.makedirs(ruta, exist_ok=True)
                self.hablar(f"Carpeta {nombre} creada en tus proyectos.")
            elif accion == "elimina":
                if os.path.exists(ruta):
                    shutil.rmtree(ruta)  # Elimina la carpeta y su contenido
                    self.hablar(f"Carpeta {nombre} y todo su contenido han sido eliminados.")
                else:
                    self.hablar("Esa carpeta no existe.")
        except Exception:
            self.hablar("No tengo los permisos necesarios o el archivo está en uso.")