#!/usr/bin/env python3

import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

logger = logging.getLogger("lia.recordatorios")

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_SRC_DIR)
REC_PATH  = os.path.join(_ROOT_DIR, "lia_recordatorios.json")

_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
_DIAS_SEMANA = {
    "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
    "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6,
}


def _parsear_fecha(texto: str) -> Optional[date]:
    texto = texto.lower().strip()
    hoy   = date.today()

    if "hoy" in texto:
        return hoy
    if "mañana" in texto or "manana" in texto:
        return hoy + timedelta(days=1)
    if "pasado mañana" in texto or "pasado manana" in texto:
        return hoy + timedelta(days=2)

    m = re.search(r"en (\d+) día[s]?", texto)
    if m:
        return hoy + timedelta(days=int(m.group(1)))

    for nombre, num in _DIAS_SEMANA.items():
        if nombre in texto:
            dias_hasta = (num - hoy.weekday()) % 7
            if dias_hasta == 0:
                dias_hasta = 7
            return hoy + timedelta(days=dias_hasta)

    m = re.search(r"(\d{1,2})\s+de\s+(\w+)(?:\s+de\s+(\d{4}))?", texto)
    if m:
        dia  = int(m.group(1))
        mes_nombre = m.group(2)
        anio = int(m.group(3)) if m.group(3) else hoy.year
        mes  = _MESES.get(mes_nombre)
        if mes:
            try:
                fecha = date(anio, mes, dia)
                if fecha < hoy:
                    fecha = date(anio + 1, mes, dia)
                return fecha
            except ValueError:
                pass

    m = re.search(r"(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?", texto)
    if m:
        dia  = int(m.group(1))
        mes  = int(m.group(2))
        anio = int(m.group(3)) if m.group(3) else hoy.year
        if anio < 100:
            anio += 2000
        try:
            fecha = date(anio, mes, dia)
            if fecha < hoy:
                fecha = date(anio + 1, mes, dia)
            return fecha
        except ValueError:
            pass

    return None


def _parsear_hora(texto: str) -> Optional[str]:
    texto = texto.lower()
    m = re.search(r"a las? (\d{1,2})(?::(\d{2}))?\s*(am|pm|de la mañana|de la tarde|de la noche)?", texto)
    if m:
        hora = int(m.group(1))
        mins = int(m.group(2)) if m.group(2) else 0
        sufijo = m.group(3) or ""
        if "pm" in sufijo or "tarde" in sufijo or "noche" in sufijo:
            if hora < 12:
                hora += 12
        return f"{hora:02d}:{mins:02d}"
    return "09:00"


class RecordatoriosTools:

    def __init__(self, parent_lia):
        self.lia           = parent_lia
        self._shutdown     = None
        self._datos        = self._cargar()
        self._verificar_hoy_al_inicio()
        self._iniciar_monitor()

    def _cargar(self) -> dict:
        try:
            if os.path.exists(REC_PATH):
                with open(REC_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as ex:
            logger.error("Error cargando recordatorios: %s", ex)
        return {"recordatorios": []}

    def _guardar(self):
        try:
            with open(REC_PATH, "w", encoding="utf-8") as f:
                json.dump(self._datos, f, indent=2, ensure_ascii=False)
        except Exception as ex:
            logger.error("Error guardando recordatorios: %s", ex)

    def agregar(self, mensaje: str, texto_fecha: str):
        fecha = _parsear_fecha(texto_fecha)
        if not fecha:
            self.lia.hablar("No entendí la fecha del recordatorio.")
            logger.warning("No se pudo parsear fecha: '%s'", texto_fecha)
            return

        hora = _parsear_hora(texto_fecha)

        rec = {
            "id":        str(uuid.uuid4())[:8],
            "mensaje":   mensaje,
            "fecha":     fecha.isoformat(),
            "hora":      hora,
            "creado":    datetime.now().isoformat(),
            "mostrado":  False,
        }
        self._datos["recordatorios"].append(rec)
        self._guardar()

        fecha_legible = fecha.strftime("%d de %B").lstrip("0")
        self.lia.hablar(f"Recordatorio guardado para el {fecha_legible}: {mensaje}.")
        self.lia.registrar_actividad(f"Recordatorio: {mensaje} el {fecha.isoformat()}")

    def _verificar_hoy_al_inicio(self):
        hoy     = date.today().isoformat()
        ahora   = datetime.now()
        pendientes = []

        for rec in self._datos["recordatorios"]:
            if rec.get("mostrado"):
                continue
            if rec["fecha"] == hoy or rec["fecha"] < hoy:
                pendientes.append(rec)

        if pendientes:
            print(f"\n{'='*50}")
            print(f"  🔔 RECORDATORIOS PENDIENTES ({len(pendientes)})")
            print(f"{'='*50}")
            for rec in pendientes:
                estado = "HOY" if rec["fecha"] == hoy else f"VENCIDO ({rec['fecha']})"
                print(f"  [{estado}] {rec['mensaje']} — {rec['hora']}")
            print(f"{'='*50}\n")

        return pendientes

    def obtener_hoy(self) -> list:
        hoy = date.today().isoformat()
        return [r for r in self._datos["recordatorios"]
                if r["fecha"] == hoy and not r.get("mostrado")]

    def obtener_proximos(self, dias: int = 7) -> list:
        hoy    = date.today()
        limite = (hoy + timedelta(days=dias)).isoformat()
        hoy_s  = hoy.isoformat()
        return sorted(
            [r for r in self._datos["recordatorios"]
             if not r.get("mostrado") and hoy_s <= r["fecha"] <= limite],
            key=lambda x: x["fecha"]
        )

    def listar(self):
        proximos = self.obtener_proximos(dias=30)
        if not proximos:
            self.lia.hablar("No tienes recordatorios pendientes.")
            return
        self.lia.hablar(f"Tienes {len(proximos)} recordatorio{'s' if len(proximos) != 1 else ''}.")
        for r in proximos[:5]:
            fecha  = date.fromisoformat(r["fecha"])
            label  = "hoy" if fecha == date.today() else fecha.strftime("%d de %B")
            self.lia.hablar(f"{label}: {r['mensaje']}.")
            time.sleep(0.2)

    def completar(self, texto: str):
        texto_lower = texto.lower().strip()
        for rec in self._datos["recordatorios"]:
            if texto_lower in rec["mensaje"].lower() and not rec.get("mostrado"):
                rec["mostrado"] = True
                self._guardar()
                self.lia.hablar(f"Recordatorio completado: {rec['mensaje']}.")
                return
        self.lia.hablar("No encontré ese recordatorio.")

    def _iniciar_monitor(self):
        def _loop():
            while True:
                if self._shutdown and self._shutdown.is_set():
                    break
                try:
                    self._disparar_pendientes()
                except Exception as ex:
                    logger.error("Error en monitor de recordatorios: %s", ex)
                time.sleep(60)

        t = threading.Thread(target=_loop, daemon=True, name="LiaRecMon")
        t.start()

    def _disparar_pendientes(self):
        hoy      = date.today().isoformat()
        ahora_h  = datetime.now().strftime("%H:%M")
        guardado = False

        for rec in self._datos["recordatorios"]:
            if rec.get("mostrado"):
                continue
            if rec["fecha"] != hoy:
                continue
            if rec.get("hora", "00:00") <= ahora_h:
                self.lia.hablar(f"Recordatorio: {rec['mensaje']}.")
                try:
                    self.lia.sistema.notificar("Lia – Recordatorio", rec["mensaje"])
                except Exception:
                    pass
                try:
                    from mod_sonidos import sonido_confirmacion
                    sonido_confirmacion()
                except Exception:
                    pass
                rec["mostrado"] = True
                guardado = True

        if guardado:
            self._guardar()