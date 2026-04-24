import webbrowser
import urllib.parse

class ModuloInternet:
    def __init__(self, funcion_hablar):
        # Recibe la función de hablar del núcleo principal
        self.hablar = funcion_hablar

    def abrir_url(self, url, nombre, silent=False):
        try:
            webbrowser.open(url)
            if not silent:
                self.hablar(f"Abriendo {nombre}")
        except Exception as e:
            print(f"❌ Error al abrir {nombre}: {e}")

    def buscar_en_google(self, consulta):
        self.hablar(f"Buscando {consulta} en internet.")
        # Prepara el texto para que sea una URL válida (ej. cambia espacios por %20)
        url = f"https://www.google.com/search?q={urllib.parse.quote(consulta)}"
        webbrowser.open(url)