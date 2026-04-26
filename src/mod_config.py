#!/usr/bin/env python3
"""
mod_config.py  –  Módulo de Configuración  (NUEVO en v4.0)
Responsabilidades:
  · Leer / escribir lia_config.json en la raíz del proyecto
  · Exponer get() / set() a todos los módulos
  · Proveer un asistente de configuración por voz

Por qué existe:
  En v3 muchas rutas (PENDIENTES_PATH, etc.) estaban hardcodeadas.
  Si el usuario tiene Obsidian en otra carpeta, o un nombre de usuario
  diferente a 'dell', todo falla silenciosamente.
  Este módulo resuelve ese problema centralizando la configuración.

Uso desde cualquier módulo:
    ruta = self.lia.config.get("pendientes_path")
"""

import os
import json


# Valores por defecto razonables
_DEFAULTS: dict = {
    # Rutas de archivos de usuario
    "pendientes_path": os.path.join(
        os.path.expanduser("~"), "Documents", "Notas", "Pendientes.md"
    ),
    "notas_dir": os.path.join(
        os.path.expanduser("~"), "Documents", "Notas"
    ),

    # TTS
    "tts_rate": 175,          # palabras por minuto

    # Detección de aplausos
    "clap_threshold_multiplier": 3.0,   # noise_floor * este valor
    "clap_window": 2.5,                 # segundos de ventana
    "sequence_gap": 0.90,               # silencio para cerrar secuencia

    # Comportamiento
    "idioma_reconocimiento": "es-MX",
    "pendientes_limite": 5,             # máximo de pendientes que lee Lia
    "pomodoro_minutos": 25,             # duración por defecto del pomodoro
}


class ConfigManager:
    """
    Gestor de configuración para Lia.
    Lee/escribe lia_config.json. Si no existe, lo crea con valores por defecto.
    """

    def __init__(self, root_dir: str):
        self._config_path = os.path.join(root_dir, "lia_config.json")
        self._config      = dict(_DEFAULTS)
        self._cargar()

    # ════════════════════════════════════════════════════════
    #  LECTURA Y ESCRITURA
    # ════════════════════════════════════════════════════════

    def _cargar(self):
        """Carga la configuración del archivo. Crea el archivo si no existe."""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    guardado = json.load(f)
                # Fusionar: los valores guardados sobreescriben los defaults,
                # pero se conservan keys nuevas que el usuario no tenga todavía.
                self._config.update(guardado)
            except Exception as e:
                print(f"⚠️  No se pudo leer config: {e}. Usando valores por defecto.")
        else:
            # Primera vez: guardar config con defaults
            self._guardar()
            print(f"✅ Archivo de configuración creado en:\n   {self._config_path}")

    def _guardar(self):
        """Persiste la configuración actual en el archivo JSON."""
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ No se pudo guardar config: {e}")

    def get(self, clave: str, default=None):
        """Retorna el valor de una clave de configuración."""
        return self._config.get(clave, default if default is not None
                                else _DEFAULTS.get(clave))

    def set(self, clave: str, valor):
        """Actualiza una clave y persiste el cambio."""
        self._config[clave] = valor
        self._guardar()
        print(f"⚙️  Config: {clave} = {valor}")

    def mostrar_todas(self):
        """Imprime toda la configuración en consola."""
        print("\n⚙️  CONFIGURACIÓN ACTUAL DE LIA")
        print("=" * 50)
        for k, v in self._config.items():
            print(f"  {k:<35} : {v}")
        print("=" * 50)

    # ════════════════════════════════════════════════════════
    #  ASISTENTE DE CONFIGURACIÓN POR VOZ
    # ════════════════════════════════════════════════════════

    def asistente_configuracion(self, lia):
        """
        Lia guía al usuario a través de la configuración básica.
        Se activa con: 'Lia, configurar'
        """
        self.mostrar_todas()
        lia.hablar(
            "Te mostraré la configuración en pantalla. "
            "Puedes editar el archivo lia_config.json directamente "
            "para cambiar rutas, velocidad de voz y otras opciones."
        )

        # Verificar si el archivo de pendientes existe y avisar
        pendientes = self.get("pendientes_path")
        if not os.path.exists(pendientes):
            lia.hablar(
                f"No encontré tu archivo de pendientes. "
                f"Crearé uno vacío en la ruta configurada."
            )
            print(f"\n⚠️  Pendientes no encontrado en:\n   {pendientes}")
            print("   Edita 'pendientes_path' en lia_config.json si tu ruta es diferente.\n")
            # Crear carpeta y archivo si no existen
            try:
                os.makedirs(os.path.dirname(pendientes), exist_ok=True)
                if not os.path.exists(pendientes):
                    with open(pendientes, "w", encoding="utf-8") as f:
                        f.write("# Pendientes\n\n- [ ] Ejemplo de tarea\n")
                    lia.hablar("Creé un archivo de ejemplo. Puedes agregar tus tareas ahí.")
            except Exception as e:
                print(f"❌ No pude crear el archivo: {e}")
        else:
            lia.hablar("Tu archivo de pendientes está disponible.")

        lia.hablar(
            "Para cambiar cualquier ajuste, edita lia_config.json "
            "en la carpeta raíz del proyecto."
        )
        lia.registrar_actividad("Abrió configuración")