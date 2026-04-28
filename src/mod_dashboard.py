#!/usr/bin/env python3

import logging
import os
import re
import threading
from datetime import date, datetime

logger = logging.getLogger("lia.dashboard")

_SRC_DIR   = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR  = os.path.dirname(_SRC_DIR)
NOTAS_DIR  = os.path.join(os.path.expanduser("~"), "Documents", "Notas")
PENDIENTES_PATH = os.path.join(NOTAS_DIR, "Pendientes.md")

_DIAS   = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
_MESES  = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
           "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

_BG      = "#0d0d0d"
_BG2     = "#1a1a1a"
_BG3     = "#252525"
_ACCENT  = "#00d4ff"
_TEXT    = "#e8e8e8"
_MUTED   = "#888888"
_WARN    = "#ffaa00"
_SUCCESS = "#00cc88"
_ERROR   = "#ff4444"


def _leer_pendientes(limite: int = 6) -> list:
    items = []
    try:
        if not os.path.exists(PENDIENTES_PATH):
            return []
        with open(PENDIENTES_PATH, "r", encoding="utf-8-sig") as f:
            for linea in f:
                linea = linea.strip().lstrip("\ufeff")
                m = re.match(r"^-\s*\[\s*\]\s*(.*)", linea)
                if m and m.group(1).strip():
                    items.append(m.group(1).strip())
                    if len(items) >= limite:
                        break
    except Exception as ex:
        logger.error("Error leyendo pendientes para dashboard: %s", ex)
    return items


def _leer_recordatorios_hoy(rec_tools) -> list:
    try:
        return rec_tools.obtener_hoy()
    except Exception:
        return []


def _leer_proximos_recordatorios(rec_tools, dias: int = 7) -> list:
    try:
        return rec_tools.obtener_proximos(dias=dias)[:5]
    except Exception:
        return []


def mostrar_dashboard(lia=None, auto_close_ms: int = 15000):
    def _run():
        try:
            import tkinter as tk
            from tkinter import font as tkfont
        except ImportError:
            logger.error("tkinter no disponible.")
            return

        hoy     = date.today()
        ahora   = datetime.now()
        dia_str = f"{_DIAS[hoy.weekday()]}, {hoy.day} de {_MESES[hoy.month - 1]} de {hoy.year}"
        hora_str = ahora.strftime("%H:%M")

        pendientes   = _leer_pendientes(limite=6)
        rec_hoy      = _leer_recordatorios_hoy(lia.recordatorios) if lia and hasattr(lia, "recordatorios") else []
        rec_proximos = _leer_proximos_recordatorios(lia.recordatorios) if lia and hasattr(lia, "recordatorios") else []

        root = tk.Tk()
        root.title("Lia — Dashboard")
        root.configure(bg=_BG)
        root.resizable(False, False)
        root.attributes("-topmost", True)

        ancho, alto = 520, 600
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x  = sw - ancho - 24
        y  = 40
        root.geometry(f"{ancho}x{alto}+{x}+{y}")

        try:
            root.attributes("-alpha", 0.96)
        except Exception:
            pass

        f_titulo  = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        f_grande  = tkfont.Font(family="Segoe UI", size=22, weight="bold")
        f_normal  = tkfont.Font(family="Segoe UI", size=10)
        f_pequeño = tkfont.Font(family="Segoe UI", size=9)
        f_seccion = tkfont.Font(family="Segoe UI", size=9, weight="bold")

        def _seccion(parent, texto, color=_ACCENT):
            tk.Label(parent, text=f"  {texto.upper()}",
                     font=f_seccion, bg=_BG2, fg=color,
                     anchor="w").pack(fill="x", pady=(8, 2))

        def _item(parent, texto, color=_TEXT, prefijo="•"):
            marco = tk.Frame(parent, bg=_BG3)
            marco.pack(fill="x", padx=8, pady=1)
            tk.Label(marco, text=prefijo, font=f_pequeño,
                     bg=_BG3, fg=_ACCENT, width=2).pack(side="left")
            tk.Label(marco, text=texto, font=f_pequeño,
                     bg=_BG3, fg=color, anchor="w",
                     wraplength=440).pack(side="left", fill="x", pady=3)

        def _vacio(parent, texto="Sin elementos"):
            tk.Label(parent, text=f"    {texto}", font=f_pequeño,
                     bg=_BG, fg=_MUTED, anchor="w").pack(fill="x", pady=2)

        contenedor = tk.Frame(root, bg=_BG, padx=16, pady=12)
        contenedor.pack(fill="both", expand=True)

        cabecera = tk.Frame(contenedor, bg=_BG2, pady=12)
        cabecera.pack(fill="x", pady=(0, 10))

        tk.Label(cabecera, text="🤖  LIA", font=f_grande,
                 bg=_BG2, fg=_ACCENT).pack()
        tk.Label(cabecera, text=dia_str, font=f_normal,
                 bg=_BG2, fg=_TEXT).pack()
        tk.Label(cabecera, text=hora_str, font=tkfont.Font(family="Segoe UI", size=32, weight="bold"),
                 bg=_BG2, fg=_TEXT).pack()

        bloque = tk.Frame(contenedor, bg=_BG)
        bloque.pack(fill="both", expand=True)

        _seccion(bloque, f"🔔 Recordatorios hoy ({len(rec_hoy)})", _WARN)
        if rec_hoy:
            for r in rec_hoy:
                _item(bloque, f"[{r['hora']}] {r['mensaje']}", color=_WARN, prefijo="!")
        else:
            _vacio(bloque, "Sin recordatorios para hoy")

        _seccion(bloque, f"📋 Pendientes ({len(pendientes)})", _ACCENT)
        if pendientes:
            for p in pendientes:
                _item(bloque, p)
        else:
            _vacio(bloque, "Sin pendientes")

        prox_no_hoy = [r for r in rec_proximos if r["fecha"] != hoy.isoformat()]
        _seccion(bloque, f"📅 Próximos recordatorios", _SUCCESS)
        if prox_no_hoy:
            for r in prox_no_hoy[:4]:
                fecha_d = date.fromisoformat(r["fecha"])
                label   = f"{fecha_d.day} de {_MESES[fecha_d.month - 1]}"
                _item(bloque, f"{label}: {r['mensaje']}", color=_SUCCESS)
        else:
            _vacio(bloque, "Sin recordatorios próximos")

        pie = tk.Frame(contenedor, bg=_BG, pady=6)
        pie.pack(fill="x")

        countdown_var = tk.StringVar(value=f"Se cierra en {auto_close_ms // 1000}s")
        lbl_cd = tk.Label(pie, textvariable=countdown_var, font=f_pequeño,
                          bg=_BG, fg=_MUTED)
        lbl_cd.pack(side="left")

        tk.Button(pie, text="Cerrar", font=f_pequeño,
                  bg=_BG3, fg=_TEXT, relief="flat", cursor="hand2",
                  command=root.destroy).pack(side="right")

        segundos_restantes = [auto_close_ms // 1000]

        def _tick():
            if segundos_restantes[0] <= 0:
                try:
                    root.destroy()
                except Exception:
                    pass
                return
            countdown_var.set(f"Se cierra en {segundos_restantes[0]}s")
            segundos_restantes[0] -= 1
            root.after(1000, _tick)

        root.after(1000, _tick)
        root.mainloop()

    t = threading.Thread(target=_run, daemon=True, name="LiaDashboard")
    t.start()