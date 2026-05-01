#!/usr/bin/env python3
# Resumen del dia: lee lia_historial.json, agrupa por categorias
# y genera un informe hablado con personalidad Jarvis.

import datetime
import json
import logging
import os
from collections import Counter

logger = logging.getLogger("lia.resumen")

_SRC_DIR       = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR      = os.path.dirname(_SRC_DIR)
HISTORIAL_PATH = os.path.join(_ROOT_DIR, "lia_historial.json")


class ResumenTools:

    def __init__(self, parent_lia):
        self.lia     = parent_lia
        self.persona = parent_lia.persona

    def _cargar_historial(self):
        try:
            if os.path.exists(HISTORIAL_PATH):
                with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
                    return json.load(f).get("actividades", [])
        except Exception as ex:
            logger.error("No se pudo leer historial: %s", ex)
        return []

    def _filtrar_fecha(self, actividades, fecha):
        out = []
        for act in actividades:
            try:
                ts = datetime.datetime.fromisoformat(act["timestamp"])
                if ts.date() == fecha:
                    out.append(act)
            except Exception:
                continue
        return out

    def _categorizar(self, texto):
        t = texto.lower()
        if "modo estudio"     in t: return "estudio"
        if "modo programac"   in t: return "codigo"
        if "modo codigo"      in t: return "codigo"
        if "modo juego"       in t: return "juego"
        if "pomodoro"         in t: return "pomodoros"
        if "tarea" in t or "pendiente" in t: return "tareas"
        if "nota"             in t: return "notas"
        if "git"              in t: return "git"
        if "abrio" in t or "abrió" in t: return "aplicaciones"
        if "busco" in t or "buscó" in t: return "busquedas"
        if "enfoque"          in t: return "enfoque"
        return "otros"

    def resumen_del_dia(self):
        hoy      = datetime.date.today()
        historial = self._cargar_historial()
        del_dia   = self._filtrar_fecha(historial, hoy)

        if not del_dia:
            self.lia.hablar(
                f"Hoy no he registrado actividad suya, {self.persona.nombre}. "
                f"Espero que al menos haya descansado."
            )
            return

        cats  = Counter(self._categorizar(a["actividad"]) for a in del_dia)
        total = len(del_dia)

        if total < 5:
            apertura = f"Dia tranquilo, {self.persona.nombre}."
        elif total < 20:
            apertura = f"Dia razonablemente productivo, {self.persona.nombre}."
        else:
            apertura = f"Dia ocupado. {total} acciones registradas, {self.persona.nombre}."

        self.lia.hablar(apertura)

        prioridades = ["estudio", "codigo", "juego", "pomodoros",
                       "tareas", "enfoque", "git", "notas",
                       "aplicaciones", "busquedas"]
        count = 0
        for cat in prioridades:
            n = cats.get(cat, 0)
            if n > 0 and count < 6:
                self.lia.hablar(self._frase_categoria(cat, n))
                count += 1

        ayer     = hoy - datetime.timedelta(days=1)
        del_ayer = self._filtrar_fecha(historial, ayer)
        if del_ayer:
            diff = total - len(del_ayer)
            if diff > 5:
                self.lia.hablar("Bastante mas que ayer. Bien.")
            elif diff < -5:
                self.lia.hablar("Menos actividad que ayer, por cierto.")

        self.lia.registrar_actividad("Pidio resumen del dia")

    def _frase_categoria(self, cat, n):
        plural = "s" if n != 1 else ""
        ses    = "es" if n != 1 else ""
        op     = "es" if n != 1 else ""
        ap     = "es" if n != 1 else ""
        if cat == "estudio":
            return f"Modo Estudio: {n} sesion{ses}."
        if cat == "codigo":
            return f"Modo Codigo: {n} sesion{ses}."
        if cat == "juego":
            return f"Modo Juego: {n} sesion{ses}."
        if cat == "pomodoros":
            return f"{n} pomodoro{plural} completado{plural}."
        if cat == "tareas":
            return f"{n} accion{op} sobre tareas."
        if cat == "enfoque":
            return f"{n} sesion{ses} de enfoque."
        if cat == "git":
            return f"{n} operacion{op} de Git."
        if cat == "notas":
            return f"{n} nota{plural}."
        if cat == "aplicaciones":
            return f"{n} aplicacion{ap} abierta{plural}."
        if cat == "busquedas":
            return f"{n} busqueda{plural} en internet."
        return f"{cat}: {n}."

    def estadisticas_dict(self):
        hoy       = datetime.date.today()
        historial = self._cargar_historial()
        del_hoy   = self._filtrar_fecha(historial, hoy)
        cats      = Counter(self._categorizar(a["actividad"]) for a in del_hoy)

        semana = {}
        for i in range(7):
            d = hoy - datetime.timedelta(days=i)
            semana[d.isoformat()] = len(self._filtrar_fecha(historial, d))

        return {
            "total_hoy":     len(del_hoy),
            "categorias":    dict(cats),
            "ultima_semana": semana,
            "total_global":  len(historial),
        }
