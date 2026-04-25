#!/usr/bin/env python3
"""
mod_internet.py  –  Módulo de Internet
Responsabilidades:
  · Clima actual (wttr.in)
  · Rutina de inicio del día (hora, fecha, clima, pendientes, apps)
  · Búsquedas web y herramientas online
"""

import webbrowser
import urllib.parse
import datetime
import time

try:
    import requests
    _REQUESTS = True
except ImportError:
    _REQUESTS = False
    print("⚠️  requests no instalado. Instala con: pip install requests")


class InternetTools:
    """
    Todo lo que necesita conexión a internet.
    Recibe 'parent_lia' para hablar(), registrar_actividad(),
    decir_pendientes() (via mod_memoria) y open_url() (via mod_sistema).
    """

    def __init__(self, parent_lia):
        self.lia = parent_lia

    # ════════════════════════════════════════════════════════
    #  CLIMA
    # ════════════════════════════════════════════════════════

    def decir_clima(self):
        """Consulta wttr.in y dice el clima en una frase corta."""
        if not _REQUESTS:
            self.lia.hablar("requests no está instalado.")
            return
        try:
            resp  = requests.get("https://wttr.in/?format=3&lang=es", timeout=6)
            texto = resp.text.strip()
            self.lia.hablar(f"El clima ahora: {texto}.")
        except Exception:
            self.lia.hablar("No pude consultar el clima. Revisa tu conexión.")

    def _clima_corto(self) -> str:
        """Retorna el clima como texto, para usarlo en la rutina de inicio."""
        if not _REQUESTS:
            return "sin datos de clima"
        try:
            resp = requests.get("https://wttr.in/?format=%C+%t&lang=es", timeout=5)
            return resp.text.strip()
        except Exception:
            return "sin datos de clima"

    # ════════════════════════════════════════════════════════
    #  RUTINA DE INICIO  (antes "rutina mañanera")
    # ════════════════════════════════════════════════════════

    def rutina_inicio(self):
        """
        Resumen completo al comenzar el día.
        Comando de voz: 'Lia, inicio'
        """
        self.lia.hablar("Iniciando rutina.")

        ahora = datetime.datetime.now()
        hora  = ahora.strftime("%I:%M")
        ampm  = "de la mañana" if ahora.hour < 12 else "de la tarde"
        dias  = ["lunes", "martes", "miércoles", "jueves",
                 "viernes", "sábado", "domingo"]
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

        self.lia.hablar(f"Son las {hora} {ampm}.")
        self.lia.hablar(
            f"Hoy es {dias[ahora.weekday()]} "
            f"{ahora.day} de {meses[ahora.month - 1]}."
        )

        # Clima
        clima = self._clima_corto()
        self.lia.hablar(f"Clima: {clima}.")

        # Pendientes (delegado al módulo de memoria)
        try:
            self.lia.memoria.decir_pendientes(limite=5)
        except Exception:
            pass

        # Abrir herramientas esenciales
        try:
            self.lia.sistema.open_url("https://calendar.google.com", "Google Calendar")
        except Exception:
            pass

        self.lia.registrar_actividad("Rutina Inicio")

    # ════════════════════════════════════════════════════════
    #  BÚSQUEDAS Y HERRAMIENTAS WEB
    # ════════════════════════════════════════════════════════

    def buscar_google(self, consulta: str):
        """Abre una búsqueda de Google con la consulta dada."""
        url = f"https://www.google.com/search?q={urllib.parse.quote(consulta)}"
        webbrowser.open(url)
        self.lia.hablar(f"Buscando {consulta} en Google.")
        self.lia.registrar_actividad(f"Buscó en Google: {consulta}")

    def buscar_youtube(self, consulta: str):
        """Abre una búsqueda en YouTube."""
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(consulta)}"
        webbrowser.open(url)
        self.lia.hablar(f"Buscando {consulta} en YouTube.")
        self.lia.registrar_actividad(f"Buscó en YouTube: {consulta}")

    def buscar_wikipedia(self, consulta: str):
        """Abre el artículo de Wikipedia más relevante (en español)."""
        if _REQUESTS:
            try:
                api = (
                    f"https://es.wikipedia.org/w/api.php"
                    f"?action=query&list=search"
                    f"&srsearch={urllib.parse.quote(consulta)}&format=json"
                )
                datos   = requests.get(api, timeout=5).json()
                results = datos.get("query", {}).get("search", [])
                if results:
                    titulo = results[0]["title"]
                    webbrowser.open(f"https://es.wikipedia.org/wiki/{urllib.parse.quote(titulo)}")
                    self.lia.hablar(f"Abriendo artículo: {titulo}.")
                    self.lia.registrar_actividad(f"Wikipedia: {titulo}")
                    return
            except Exception:
                pass
        # Fallback: búsqueda directa
        webbrowser.open(f"https://es.wikipedia.org/w/index.php?search={urllib.parse.quote(consulta)}")
        self.lia.hablar(f"Buscando {consulta} en Wikipedia.")

    def abrir_traductor(self):
        webbrowser.open("https://translate.google.com/")
        self.lia.hablar("Abriendo traductor.")
        self.lia.registrar_actividad("Abrió Google Translate")

    def abrir_maps(self, ubicacion: str = None):
        if ubicacion:
            webbrowser.open(f"https://www.google.com/maps/search/{urllib.parse.quote(ubicacion)}")
            self.lia.hablar(f"Buscando {ubicacion} en Maps.")
            self.lia.registrar_actividad(f"Maps: {ubicacion}")
        else:
            webbrowser.open("https://maps.google.com/")
            self.lia.hablar("Abriendo Google Maps.")
            self.lia.registrar_actividad("Abrió Google Maps")

    def abrir_gmail(self):
        webbrowser.open("https://mail.google.com/")
        self.lia.hablar("Abriendo Gmail.")
        self.lia.registrar_actividad("Abrió Gmail")

    def abrir_calendar(self):
        webbrowser.open("https://calendar.google.com/")
        self.lia.hablar("Abriendo Google Calendar.")
        self.lia.registrar_actividad("Abrió Google Calendar")

    def abrir_drive(self):
        webbrowser.open("https://drive.google.com/")
        self.lia.hablar("Abriendo Google Drive.")
        self.lia.registrar_actividad("Abrió Google Drive")

    def obtener_ip_publica(self):
        if not _REQUESTS:
            self.lia.hablar("requests no está instalado.")
            return
        try:
            ip = requests.get("https://api.ipify.org?format=json", timeout=5).json()["ip"]
            self.lia.hablar(f"Tu IP pública es {ip}.")
            self.lia.registrar_actividad(f"Consultó IP: {ip}")
        except Exception:
            self.lia.hablar("No pude obtener tu IP pública.")

    def verificar_conexion(self) -> bool:
        if not _REQUESTS:
            return False
        try:
            requests.get("https://www.google.com/", timeout=3)
            self.lia.hablar("Tienes conexión a internet.")
            return True
        except Exception:
            self.lia.hablar("No detecté conexión a internet.")
            return False

    def abrir_noticias(self):
        webbrowser.open("https://news.google.com/")
        self.lia.hablar("Abriendo Google News.")
        self.lia.registrar_actividad("Abrió Google News")