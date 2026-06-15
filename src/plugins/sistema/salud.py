#!/usr/bin/env python3
"""
salud.py — Salud del sistema: CPU, RAM, disco, temperaturas, optimización de
memoria y limpieza de temporales.

Prioridades 480–488: deben ganar a system.info (490) y system.disco (500),
que capturan las palabras "cpu", "ram" y "disco".

Notas de implementación honestas:
  • Temperatura CPU: WMI MSAcpi_ThermalZoneTemperature; muchos equipos no la
    exponen sin drivers del fabricante → se avisa en vez de inventar.
  • Temperatura GPU: nvidia-smi si hay GPU NVIDIA.
  • "Optimiza memoria": EmptyWorkingSet real sobre los procesos accesibles
    (psapi) y se reporta cuánta RAM disponible se ganó.
  • "Limpia temporales": borra %TEMP% con confirmación; lo en uso se omite.
"""

from __future__ import annotations

import ctypes
import logging
import os
import shutil
import subprocess
import threading

from core.intent import IntentSpec
from core.matchers import contains_any
from core.skill import Skill

logger = logging.getLogger("lia.plugin.salud")

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

_GB = 1024 ** 3
_MB = 1024 ** 2


def _cpu(ctx, m):
    if psutil is None:
        ctx.say("Necesito psutil para eso.")
        return
    uso = psutil.cpu_percent(interval=1)
    nucleos = psutil.cpu_count(logical=True)
    freq = psutil.cpu_freq()
    extra = f", a {freq.current / 1000:.1f} gigahertz" if freq else ""
    ctx.say(f"CPU al {uso:.0f} por ciento, {nucleos} núcleos lógicos{extra}.")


def _ram(ctx, m):
    if psutil is None:
        ctx.say("Necesito psutil para eso.")
        return
    v = psutil.virtual_memory()
    ctx.say(f"RAM al {v.percent:.0f} por ciento: "
            f"{v.used / _GB:.1f} de {v.total / _GB:.1f} gigas usados, "
            f"{v.available / _GB:.1f} libres.")


def _salud_disco(ctx, m):
    if psutil is None:
        ctx.say("Necesito psutil para eso.")
        return
    uso = shutil.disk_usage(os.path.expanduser("~"))
    pct = uso.used / uso.total * 100
    estado = ""
    try:
        out = subprocess.run(
            ["wmic", "diskdrive", "get", "status"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        estados = [l.strip() for l in out.splitlines()[1:] if l.strip()]
        if estados and all(e == "OK" for e in estados):
            estado = " Estado SMART: OK."
        elif estados:
            estado = f" Atención, SMART reporta: {', '.join(set(estados))}."
    except Exception as ex:
        logger.debug("SMART no disponible: %s", ex)
    ctx.say(f"Disco al {pct:.0f} por ciento, {uso.free / _GB:.0f} gigas libres "
            f"de {uso.total / _GB:.0f}.{estado}")


def _temp_cpu(ctx, m):
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
             "| Select-Object -First 1 -ExpandProperty CurrentTemperature"],
            capture_output=True, text=True, timeout=15,
        ).stdout.strip()
        if out:
            celsius = int(out) / 10.0 - 273.15
            if 0 < celsius < 120:
                ctx.say(f"La zona térmica del CPU está a {celsius:.0f} grados.")
                return
    except Exception as ex:
        logger.debug("Temperatura CPU no disponible: %s", ex)
    ctx.say("Tu equipo no expone la temperatura del CPU a Windows. "
            "Necesitarías una herramienta como HWMonitor para verla.")


def _temp_gpu(ctx, m):
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if out and out.splitlines()[0].strip().isdigit():
            ctx.say(f"La GPU está a {out.splitlines()[0].strip()} grados.")
            return
    except Exception as ex:
        logger.debug("nvidia-smi no disponible: %s", ex)
    ctx.say("No encontré una GPU NVIDIA con nvidia-smi. "
            "Si tu gráfica es integrada, Windows no expone su temperatura.")


def _optimizar_memoria(ctx, m):
    if psutil is None:
        ctx.say("Necesito psutil para eso.")
        return
    ctx.say("Optimizando memoria, dame unos segundos.")

    def _run():
        antes = psutil.virtual_memory().available
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi
        PROCESS_SET_QUOTA = 0x0100
        PROCESS_QUERY_INFORMATION = 0x0400
        optimizados = 0
        for proc in psutil.process_iter(["pid"]):
            try:
                handle = kernel32.OpenProcess(
                    PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, False, proc.pid)
                if handle:
                    if psapi.EmptyWorkingSet(handle):
                        optimizados += 1
                    kernel32.CloseHandle(handle)
            except Exception:
                continue
        despues = psutil.virtual_memory().available
        ganado = max(0, despues - antes) / _MB
        ctx.say(f"Listo: recorté el working set de {optimizados} procesos "
                f"y liberé {ganado:.0f} megas de RAM.")
        ctx.registrar_actividad(f"Optimizó memoria ({ganado:.0f} MB)")

    threading.Thread(target=_run, daemon=True).start()


def _limpiar_temporales(ctx, m):
    temp = os.environ.get("TEMP") or os.environ.get("TMP")
    if not temp or not os.path.isdir(temp):
        ctx.say("No encontré la carpeta de temporales.")
        return

    def _confirm(r):
        if not any(w in r.lower() for w in ("sí", "si", "claro", "dale", "hazlo",
                                            "ok", "okay", "adelante", "limpia")):
            ctx.say("De acuerdo, no toco nada.")
            return
        ctx.say("Limpiando temporales...")

        def _run():
            borrados, bytes_ = 0, 0
            for entrada in os.scandir(temp):
                try:
                    if entrada.is_file() or entrada.is_symlink():
                        bytes_ += entrada.stat().st_size
                        os.unlink(entrada.path)
                        borrados += 1
                    elif entrada.is_dir():
                        tam = sum(f.stat().st_size for f in os.scandir(entrada.path)
                                  if f.is_file())
                        shutil.rmtree(entrada.path)
                        bytes_ += tam
                        borrados += 1
                except Exception:
                    continue  # en uso por otro proceso: se omite
            ctx.say(f"Limpieza lista: {borrados} elementos, "
                    f"{bytes_ / _MB:.0f} megas recuperados. Lo que estaba en uso se omitió.")
            ctx.registrar_actividad(f"Limpió temporales ({bytes_ / _MB:.0f} MB)")

        threading.Thread(target=_run, daemon=True).start()

    ctx.ask("Voy a borrar los archivos temporales de Windows. ¿Confirmas? Di sí.", _confirm)


class SaludSistemaSkill(Skill):
    name = "salud_sistema"
    category = "sistema"

    def intents(self, ctx):
        return [
            IntentSpec(
                name="salud.temp_cpu", priority=482,
                matcher=contains_any(("temperatura cpu", "temperatura del cpu",
                                      "temperatura del procesador",
                                      "qué temperatura tiene el cpu",
                                      "que temperatura tiene el cpu")),
                handler=_temp_cpu,
                description="Temperatura del CPU (si el equipo la expone)",
                aliases=("temperatura cpu",),
                examples=("temperatura cpu",),
            ),
            IntentSpec(
                name="salud.temp_gpu", priority=483,
                matcher=contains_any(("temperatura gpu", "temperatura de la gpu",
                                      "temperatura de la gráfica",
                                      "temperatura de la grafica",
                                      "temperatura de la tarjeta")),
                handler=_temp_gpu,
                description="Temperatura de la GPU (NVIDIA vía nvidia-smi)",
                aliases=("temperatura gpu",),
                examples=("temperatura gpu",),
            ),
            IntentSpec(
                name="salud.cpu", priority=484,
                matcher=contains_any(("uso de cpu", "uso del cpu", "cuánta cpu",
                                      "cuanta cpu", "uso del procesador")),
                handler=_cpu,
                description="Porcentaje de uso del CPU en este momento",
                aliases=("uso de cpu",),
                examples=("uso de cpu",),
            ),
            IntentSpec(
                name="salud.ram", priority=485,
                matcher=contains_any(("uso de ram", "uso de memoria", "cuánta ram",
                                      "cuanta ram", "memoria disponible",
                                      "cuánta memoria queda", "cuanta memoria queda")),
                handler=_ram,
                description="Uso y disponibilidad de RAM",
                aliases=("uso de ram",),
                examples=("uso de ram", "cuánta ram queda"),
            ),
            IntentSpec(
                name="salud.disco", priority=486,
                matcher=contains_any(("salud del disco", "estado del disco",
                                      "cómo está el disco", "como esta el disco",
                                      "revisa el disco")),
                handler=_salud_disco,
                description="Espacio libre y estado SMART del disco",
                aliases=("salud del disco",),
                examples=("salud del disco",),
            ),
            IntentSpec(
                name="salud.optimizar", priority=487,
                matcher=contains_any(("optimiza memoria", "optimiza la memoria",
                                      "libera memoria", "libera ram",
                                      "optimizar memoria")),
                handler=_optimizar_memoria,
                description="Libera RAM recortando el working set de los procesos",
                aliases=("optimiza memoria", "libera memoria"),
                examples=("optimiza memoria",),
            ),
            IntentSpec(
                name="salud.temporales", priority=488,
                matcher=contains_any(("limpia temporales", "limpia los temporales",
                                      "borra temporales", "limpia archivos temporales",
                                      "borra los archivos temporales")),
                handler=_limpiar_temporales,
                description="Borra los archivos temporales de Windows (pide confirmación)",
                aliases=("limpia temporales",),
                examples=("limpia temporales",),
            ),
        ]
