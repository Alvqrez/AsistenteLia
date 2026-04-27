#!/usr/bin/env python3

import logging
import os
import json
import re
import datetime
import time

logger = logging.getLogger("lia.vida")

_SRC_DIR   = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR  = os.path.dirname(_SRC_DIR)
NOTAS_DIR  = os.path.join(os.path.expanduser("~"), "Documents", "Notas")

METAS_PATH      = os.path.join(NOTAS_DIR, "Metas.md")
HABITOS_PATH    = os.path.join(NOTAS_DIR, "Habitos.md")
PROYECTOS_PATH  = os.path.join(NOTAS_DIR, "Proyectos.md")
VIDA_JSON_PATH  = os.path.join(_ROOT_DIR, "lia_vida.json")


class VidaTools:

    def __init__(self, parent_lia):
        self.lia  = parent_lia
        self.data = self._cargar_json()

    def _cargar_json(self) -> dict:
        default = {
            "habitos_hoy": {},
            "proyectos":   [],
            "racha":       {},
        }
        try:
            if os.path.exists(VIDA_JSON_PATH):
                with open(VIDA_JSON_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as ex:
            logger.error("No se pudo cargar lia_vida.json: %s", ex)
        return default

    def _guardar_json(self):
        try:
            with open(VIDA_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as ex:
            logger.error("No se pudo guardar lia_vida.json: %s", ex)

    def _asegurar_archivo(self, ruta: str, contenido_inicial: str):
        os.makedirs(NOTAS_DIR, exist_ok=True)
        if not os.path.exists(ruta):
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido_inicial)
            logger.info("Creado archivo: %s", ruta)

    def _leer_items_md(self, ruta: str, solo_pendientes: bool = True) -> list:
        items = []
        try:
            with open(ruta, "r", encoding="utf-8-sig") as f:
                for linea in f:
                    linea = linea.strip().lstrip("\ufeff")
                    if solo_pendientes:
                        m = re.match(r"^-\s*\[\s*\]\s*(.*)", linea)
                    else:
                        m = re.match(r"^-\s*\[.\]\s*(.*)", linea)
                    if m and m.group(1).strip():
                        items.append(m.group(1).strip())
        except Exception as ex:
            logger.error("Error leyendo '%s': %s", ruta, ex)
        return items

    def _marcar_completado_md(self, ruta: str, texto_buscar: str) -> bool:
        try:
            with open(ruta, "r", encoding="utf-8-sig") as f:
                lineas = f.readlines()
            encontrado = False
            nuevas = []
            for linea in lineas:
                if not encontrado:
                    m = re.match(r"^-\s*\[\s*\]\s*(.*)", linea.strip())
                    if m and texto_buscar.lower() in m.group(1).lower():
                        nuevas.append(re.sub(r"\[\s*\]", "[x]", linea, count=1))
                        encontrado = True
                        continue
                nuevas.append(linea)
            if encontrado:
                with open(ruta, "w", encoding="utf-8") as f:
                    f.writelines(nuevas)
            return encontrado
        except Exception as ex:
            logger.error("Error al marcar en '%s': %s", ruta, ex)
            return False

    def _agregar_item_md(self, ruta: str, texto: str):
        try:
            with open(ruta, "a", encoding="utf-8") as f:
                f.write(f"\n- [ ] {texto}\n")
        except Exception as ex:
            logger.error("Error al agregar en '%s': %s", ruta, ex)

    def leer_metas(self):
        self._asegurar_archivo(METAS_PATH, "# Metas\n\n")
        metas = self._leer_items_md(METAS_PATH)
        if not metas:
            self.lia.hablar("No tienes metas pendientes. ¡Agrega algunas!")
            return
        self.lia.hablar(f"Tienes {len(metas)} meta{'s' if len(metas) != 1 else ''} pendiente{'s' if len(metas) != 1 else ''}.")
        for meta in metas[:5]:
            self.lia.hablar(meta)
            time.sleep(0.3)
        if len(metas) > 5:
            self.lia.hablar(f"Y {len(metas) - 5} más.")
        self.lia.registrar_actividad("Leyó metas")

    def agregar_meta(self, texto: str):
        self._asegurar_archivo(METAS_PATH, "# Metas\n\n")
        self._agregar_item_md(METAS_PATH, texto)
        self.lia.hablar(f"Meta agregada: {texto}.")
        self.lia.registrar_actividad("Agregó meta")

    def completar_meta(self, texto: str):
        self._asegurar_archivo(METAS_PATH, "# Metas\n\n")
        if self._marcar_completado_md(METAS_PATH, texto):
            self.lia.hablar(f"Meta completada: {texto}. ¡Bien hecho!")
        else:
            self.lia.hablar(f"No encontré esa meta.")
        self.lia.registrar_actividad("Completó meta")

    def revisar_habitos(self):
        self._asegurar_archivo(HABITOS_PATH, "# Hábitos\n\n")
        habitos = self._leer_items_md(HABITOS_PATH)
        hoy = datetime.date.today().isoformat()
        marcados_hoy = self.data.get("habitos_hoy", {}).get(hoy, [])

        if not habitos:
            self.lia.hablar("No tienes hábitos registrados. Agrega algunos a Habitos.md.")
            return

        pendientes = [h for h in habitos if h not in marcados_hoy]
        completados = len(habitos) - len(pendientes)

        self.lia.hablar(f"Hábitos hoy: {completados} de {len(habitos)} completados.")
        if pendientes:
            self.lia.hablar("Pendientes:")
            for h in pendientes[:5]:
                self.lia.hablar(h)
                time.sleep(0.25)
        else:
            self.lia.hablar("¡Completaste todos tus hábitos de hoy!")
        self.lia.registrar_actividad("Revisó hábitos")

    def marcar_habito(self, nombre: str):
        self._asegurar_archivo(HABITOS_PATH, "# Hábitos\n\n")
        habitos = self._leer_items_md(HABITOS_PATH)
        nombre_lower = nombre.lower()
        coincidencia = next((h for h in habitos if nombre_lower in h.lower()), None)

        if not coincidencia:
            self.lia.hablar(f"No encontré el hábito '{nombre}'.")
            return

        hoy = datetime.date.today().isoformat()
        if "habitos_hoy" not in self.data:
            self.data["habitos_hoy"] = {}
        if hoy not in self.data["habitos_hoy"]:
            self.data["habitos_hoy"][hoy] = []

        if coincidencia not in self.data["habitos_hoy"][hoy]:
            self.data["habitos_hoy"][hoy].append(coincidencia)
            self._actualizar_racha(coincidencia, hoy)
            self._guardar_json()
            racha = self.data["racha"].get(coincidencia, {}).get("dias", 1)
            self.lia.hablar(f"Hábito marcado: {coincidencia}. Racha de {racha} día{'s' if racha != 1 else ''}.")
        else:
            self.lia.hablar(f"Ya marcaste '{coincidencia}' hoy.")
        self.lia.registrar_actividad(f"Marcó hábito: {coincidencia}")

    def _actualizar_racha(self, habito: str, hoy: str):
        if "racha" not in self.data:
            self.data["racha"] = {}
        racha_info = self.data["racha"].get(habito, {"dias": 0, "ultimo": ""})
        ayer = (datetime.date.fromisoformat(hoy) - datetime.timedelta(days=1)).isoformat()
        if racha_info.get("ultimo") == ayer:
            racha_info["dias"] += 1
        elif racha_info.get("ultimo") != hoy:
            racha_info["dias"] = 1
        racha_info["ultimo"] = hoy
        self.data["racha"][habito] = racha_info

    def agregar_habito(self, nombre: str):
        self._asegurar_archivo(HABITOS_PATH, "# Hábitos\n\n")
        self._agregar_item_md(HABITOS_PATH, nombre)
        self.lia.hablar(f"Hábito agregado: {nombre}.")
        self.lia.registrar_actividad("Agregó hábito")

    def estado_proyectos(self):
        self._asegurar_archivo(PROYECTOS_PATH, "# Proyectos\n\n")
        proyectos = self._leer_items_md(PROYECTOS_PATH)
        if not proyectos:
            self.lia.hablar("No tienes proyectos registrados.")
            return
        self.lia.hablar(f"Tienes {len(proyectos)} proyecto{'s' if len(proyectos) != 1 else ''} activo{'s' if len(proyectos) != 1 else ''}.")
        for p in proyectos[:5]:
            self.lia.hablar(p)
            time.sleep(0.3)
        self.lia.registrar_actividad("Revisó proyectos")

    def agregar_proyecto(self, nombre: str):
        self._asegurar_archivo(PROYECTOS_PATH, "# Proyectos\n\n")
        self._agregar_item_md(PROYECTOS_PATH, nombre)
        self.lia.hablar(f"Proyecto agregado: {nombre}.")
        self.lia.registrar_actividad("Agregó proyecto")

    def completar_proyecto(self, texto: str):
        self._asegurar_archivo(PROYECTOS_PATH, "# Proyectos\n\n")
        if self._marcar_completado_md(PROYECTOS_PATH, texto):
            self.lia.hablar(f"Proyecto completado: {texto}.")
        else:
            self.lia.hablar("No encontré ese proyecto.")
        self.lia.registrar_actividad("Completó proyecto")

    def resumen_vida(self):
        self.lia.hablar("Resumen personal.")

        metas = self._leer_items_md(METAS_PATH) if os.path.exists(METAS_PATH) else []
        habitos = self._leer_items_md(HABITOS_PATH) if os.path.exists(HABITOS_PATH) else []
        proyectos = self._leer_items_md(PROYECTOS_PATH) if os.path.exists(PROYECTOS_PATH) else []
        hoy = datetime.date.today().isoformat()
        marcados_hoy = self.data.get("habitos_hoy", {}).get(hoy, [])
        habitos_ok = len(marcados_hoy)

        self.lia.hablar(f"Metas: {len(metas)} pendientes.")
        self.lia.hablar(f"Hábitos hoy: {habitos_ok} de {len(habitos)} completados.")
        self.lia.hablar(f"Proyectos activos: {len(proyectos)}.")

        if self.lia.contexto.proyecto_activo:
            self.lia.hablar(f"Trabajando en: {self.lia.contexto.proyecto_activo['nombre']}.")

        self.lia.registrar_actividad("Resumen de vida")