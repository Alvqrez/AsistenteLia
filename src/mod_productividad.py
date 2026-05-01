#!/usr/bin/env python3
# Funciones de productividad: hora, fecha, calculadora por voz,
# conversiones (monedas, longitud, peso, temperatura).

import datetime
import logging
import re

logger = logging.getLogger("lia.productividad")

try:
    import requests
    _REQUESTS = True
except ImportError:
    _REQUESTS = False


_NUMEROS_PALABRA = {
    "cero": 0, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50,
    "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
    "cien": 100, "ciento": 100, "doscientos": 200, "trescientos": 300,
    "cuatrocientos": 400, "quinientos": 500, "seiscientos": 600,
    "setecientos": 700, "ochocientos": 800, "novecientos": 900,
    "mil": 1000,
}

_OPERADORES = {
    "mas":      "+", "y":         "+",
    "menos":    "-",
    "por":      "*", "veces":     "*", "multiplicado": "*",
    "entre":    "/", "dividido":  "/", "sobre":     "/",
}

_DIAS = ["lunes", "martes", "miercoles", "jueves",
         "viernes", "sabado", "domingo"]
_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
          "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


_TASAS_FALLBACK = {
    "usd": 1.00, "dolar": 1.00, "dolares": 1.00,
    "eur": 0.92, "euro": 0.92, "euros": 0.92,
    "mxn": 17.0, "peso": 17.0, "pesos": 17.0,
    "gbp": 0.79, "libra": 0.79, "libras": 0.79,
    "jpy": 150.0, "yen": 150.0, "yenes": 150.0,
    "ars": 920.0,
    "cop": 4000.0,
    "clp": 950.0,
    "brl": 5.0, "real": 5.0, "reales": 5.0,
    "cny": 7.2, "yuan": 7.2,
    "cad": 1.36,
}

_UNIDADES_LONGITUD = {
    "km": 1000.0, "kilometro": 1000.0, "kilometros": 1000.0,
    "m": 1.0, "metro": 1.0, "metros": 1.0,
    "cm": 0.01, "centimetro": 0.01, "centimetros": 0.01,
    "mm": 0.001, "milimetro": 0.001, "milimetros": 0.001,
    "milla": 1609.34, "millas": 1609.34,
    "pie": 0.3048, "pies": 0.3048,
    "pulgada": 0.0254, "pulgadas": 0.0254,
}

_UNIDADES_PESO = {
    "kg": 1000.0, "kilo": 1000.0, "kilos": 1000.0, "kilogramo": 1000.0,
    "kilogramos": 1000.0,
    "g": 1.0, "gramo": 1.0, "gramos": 1.0,
    "mg": 0.001, "miligramo": 0.001, "miligramos": 0.001,
    "libra": 453.592, "libras": 453.592,
    "onza": 28.3495, "onzas": 28.3495,
    "tonelada": 1000000.0, "toneladas": 1000000.0,
}


def _quitar_acentos(s):
    repl = (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
            ("ñ", "n"))
    for a, b in repl:
        s = s.replace(a, b).replace(a.upper(), b.upper())
    return s


class ProductividadTools:

    def __init__(self, parent_lia):
        self.lia = parent_lia
        self.persona = parent_lia.persona

    # ----- Hora y fecha -----
    def decir_hora(self):
        ahora = datetime.datetime.now()
        h12 = ahora.strftime("%I:%M").lstrip("0") or "12:00"
        if ahora.hour < 12:
            ampm = "de la maniana"
        elif ahora.hour < 19:
            ampm = "de la tarde"
        else:
            ampm = "de la noche"
        self.lia.hablar(f"Son las {h12} {ampm}, {self.persona.nombre}.")

    def decir_fecha(self):
        ahora = datetime.datetime.now()
        dia_sem = _DIAS[ahora.weekday()]
        mes = _MESES[ahora.month - 1]
        self.lia.hablar(
            f"Hoy es {dia_sem} {ahora.day} de {mes} de {ahora.year}, "
            f"{self.persona.nombre}."
        )

    # ----- Calculadora -----
    def _palabra_a_numero(self, texto):
        partes = texto.split()
        out = []
        for p in partes:
            n = _NUMEROS_PALABRA.get(p.lower())
            out.append(str(n) if n is not None else p)
        return " ".join(out)

    def _normalizar_expresion(self, texto):
        texto = _quitar_acentos(texto.lower())
        for prefacio in ("cuanto es", "calcula",
                         "resultado de", "el resultado de"):
            texto = texto.replace(prefacio, "")
        texto = self._palabra_a_numero(texto)
        for palabra, simbolo in _OPERADORES.items():
            texto = re.sub(rf"\b{palabra}\b", simbolo, texto)
        texto = re.sub(r"[^0-9\.\+\-\*/\(\)\s]", "", texto)
        texto = texto.replace(",", ".").strip()
        return texto

    def calcular(self, cmd):
        try:
            expr = self._normalizar_expresion(cmd)
            if not expr or not re.match(r"^[\d\s\.\+\-\*/\(\)]+$", expr):
                return False
            if not any(op in expr for op in "+-*/"):
                return False
            resultado = eval(expr, {"__builtins__": {}}, {})
            if isinstance(resultado, float):
                if resultado.is_integer():
                    resultado_str = str(int(resultado))
                else:
                    resultado_str = f"{resultado:.4f}".rstrip("0").rstrip(".")
            else:
                resultado_str = str(resultado)
            self.lia.hablar(f"El resultado es {resultado_str}.")
            self.lia.registrar_actividad(f"Calculo {expr} = {resultado_str}")
            return True
        except ZeroDivisionError:
            self.lia.hablar("Division entre cero. Mala idea.")
            return True
        except Exception as ex:
            logger.debug("calcular() fallo: %s", ex)
            return False

    # ----- Conversiones -----
    def _detectar_numero(self, texto):
        m = re.search(r"-?\d+(?:[.,]\d+)?", texto)
        if m:
            return float(m.group(0).replace(",", "."))
        for p in texto.split():
            n = _NUMEROS_PALABRA.get(p.lower())
            if n is not None:
                return float(n)
        return None

    def _resolver_unidad(self, texto, mapa):
        texto_l = _quitar_acentos(texto.lower())
        keys = sorted(mapa.keys(), key=len, reverse=True)
        for k in keys:
            if re.search(rf"\b{re.escape(k)}\b", texto_l):
                return (k, mapa[k])
        return None

    def convertir(self, cmd):
        cmd_l = _quitar_acentos(cmd.lower())
        m = re.search(r"convierte\s+(.*?)\s+a\s+(.+)$", cmd_l)
        if not m:
            self.lia.hablar(
                f"Diga: convierte 100 dolares a pesos, {self.persona.nombre}."
            )
            return
        origen_txt, destino_txt = m.group(1).strip(), m.group(2).strip()
        cantidad = self._detectar_numero(origen_txt)
        if cantidad is None:
            self.lia.hablar("No detecte la cantidad a convertir.")
            return

        if any(t in cmd_l for t in ("celsius", "fahrenheit", "centigrados")):
            self._convertir_temperatura(cantidad, origen_txt, destino_txt)
            return

        if any(u in origen_txt for u in _UNIDADES_LONGITUD) and \
           any(u in destino_txt for u in _UNIDADES_LONGITUD):
            self._convertir_genericas(cantidad, origen_txt, destino_txt,
                                       _UNIDADES_LONGITUD)
            return

        if any(u in origen_txt for u in _UNIDADES_PESO) and \
           any(u in destino_txt for u in _UNIDADES_PESO):
            self._convertir_genericas(cantidad, origen_txt, destino_txt,
                                       _UNIDADES_PESO)
            return

        self._convertir_moneda(cantidad, origen_txt, destino_txt)

    def _convertir_genericas(self, cant, origen_txt, destino_txt, mapa):
        u_o = self._resolver_unidad(origen_txt, mapa)
        u_d = self._resolver_unidad(destino_txt, mapa)
        if not u_o or not u_d:
            self.lia.hablar("No reconoci las unidades.")
            return
        en_base = cant * u_o[1]
        resultado = en_base / u_d[1]
        self.lia.hablar(
            f"{cant:g} {u_o[0]} equivalen a {resultado:.3g} {u_d[0]}."
        )

    def _convertir_temperatura(self, cant, origen_txt, destino_txt):
        o_cels = "celsius" in origen_txt or "centigrados" in origen_txt
        d_cels = "celsius" in destino_txt or "centigrados" in destino_txt
        o_fahr = "fahrenheit" in origen_txt
        d_fahr = "fahrenheit" in destino_txt
        if o_cels and d_fahr:
            r = cant * 9 / 5 + 32
            self.lia.hablar(f"{cant:g} grados Celsius son {r:.1f} Fahrenheit.")
        elif o_fahr and d_cels:
            r = (cant - 32) * 5 / 9
            self.lia.hablar(f"{cant:g} Fahrenheit son {r:.1f} Celsius.")
        else:
            self.lia.hablar("No entendi la conversion de temperatura.")

    def _convertir_moneda(self, cant, origen_txt, destino_txt):
        def detectar(t):
            for k in sorted(_TASAS_FALLBACK.keys(), key=len, reverse=True):
                if re.search(rf"\b{re.escape(k)}\b", t):
                    return k
            return None

        m_o = detectar(origen_txt)
        m_d = detectar(destino_txt)
        if not m_o or not m_d:
            self.lia.hablar(f"No reconoci las monedas, {self.persona.nombre}.")
            return

        tasa = self._tasa_online(m_o, m_d)
        if tasa is None:
            tasa_o = _TASAS_FALLBACK[m_o]
            tasa_d = _TASAS_FALLBACK[m_d]
            en_usd = cant / tasa_o
            tasa = (en_usd * tasa_d) / cant if cant else 0

        resultado = cant * tasa if tasa else 0
        self.lia.hablar(
            f"{cant:g} {m_o} son aproximadamente {resultado:,.2f} {m_d}."
        )
        self.lia.registrar_actividad(
            f"Conversion {cant} {m_o} -> {resultado:.2f} {m_d}"
        )

    def _tasa_online(self, m_o, m_d):
        if not _REQUESTS:
            return None
        codigos = {
            "dolar": "USD", "dolares": "USD", "usd": "USD",
            "euro": "EUR", "euros": "EUR", "eur": "EUR",
            "peso": "MXN", "pesos": "MXN", "mxn": "MXN",
            "libra": "GBP", "libras": "GBP", "gbp": "GBP",
            "yen": "JPY", "yenes": "JPY", "jpy": "JPY",
            "real": "BRL", "reales": "BRL", "brl": "BRL",
            "yuan": "CNY", "cny": "CNY",
            "ars": "ARS", "cop": "COP", "clp": "CLP", "cad": "CAD",
        }
        c_o = codigos.get(m_o)
        c_d = codigos.get(m_d)
        if not c_o or not c_d:
            return None
        try:
            url = f"https://open.er-api.com/v6/latest/{c_o}"
            data = requests.get(url, timeout=5).json()
            return data.get("rates", {}).get(c_d)
        except Exception:
            return None
