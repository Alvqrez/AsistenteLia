#!/usr/bin/env python3
"""
files.py — Crear archivos/carpetas, abrir carpetas y búsqueda (web o local).

Porta los parsers `_cmd_crear_archivo`, `_cmd_crear_carpeta`,
`_cmd_abrir_carpeta` y `_cmd_buscar` del antiguo Lia.py, delegando en
`mod_sistema` / `mod_sistema_extra` e `mod_internet`.
"""

from __future__ import annotations

import logging

from core.intent import IntentSpec
from core.matchers import contains_any
from core.skill import Skill

logger = logging.getLogger("lia.skill.files")

_ATAJOS_CARPETA = {
    "documentos": "documentos", "descargas": "descargas", "escritorio": "escritorio",
    "imágenes": "imágenes", "imagenes": "imágenes", "música": "música",
    "musica": "música", "videos": "videos",
}

_KEYWORDS_WEB = (
    "en internet", "en la web", "en google", "en línea", "en linea",
    "en el buscador", "online", "en la red", "por internet",
)

_ALIAS_CARPETA = (
    "documentos", "mis documentos", "descargas", "escritorio", "imágenes",
    "imagenes", "fotos", "videos", "música", "musica", "notas", "onedrive",
    "desktop", "downloads", "documents", "pictures", "home", "usuario",
)


# ── Crear archivo ────────────────────────────────────────────────────────────
def _crear_archivo(ctx, match):
    cmd_l = match.text
    for trigger in ("crea un archivo ", "crea archivo ", "nuevo archivo ", "crear archivo "):
        if trigger in cmd_l:
            resto = cmd_l.split(trigger, 1)[-1].strip()
            break
    else:
        resto = cmd_l

    carpeta = None
    if " en " in resto:
        partes = resto.rsplit(" en ", 1)
        resto, carpeta = partes[0].strip(), partes[1].strip()

    tokens = resto.split()
    tipo = tokens[0] if tokens else "txt"
    nombre = " ".join(tokens[1:]) if len(tokens) > 1 else "nuevo_archivo"

    if carpeta:
        ctx.sistema.crear_archivo(tipo=tipo, nombre=nombre, carpeta=carpeta)
    else:
        ctx.ask(
            f"¿En qué carpeta quieres crear el archivo {nombre}.{tipo}?",
            lambda r: ctx.sistema.crear_archivo(tipo=tipo, nombre=nombre, carpeta=r),
        )


# ── Crear carpeta ────────────────────────────────────────────────────────────
def _crear_carpeta(ctx, match):
    cmd_l = match.text
    for trigger in ("crea una carpeta ", "crea carpeta ", "nueva carpeta ", "crear carpeta "):
        if trigger in cmd_l:
            resto = cmd_l.split(trigger, 1)[-1].strip()
            break
    else:
        resto = cmd_l

    ruta_padre = None
    if " en " in resto:
        partes = resto.rsplit(" en ", 1)
        resto, ruta_padre = partes[0].strip(), partes[1].strip()

    nombre = resto
    if ruta_padre:
        ctx.sistema.crear_carpeta(nombre=nombre, ruta_padre=ruta_padre)
    else:
        ctx.ask(
            f"¿En qué carpeta quieres crear '{nombre}'?",
            lambda r: ctx.sistema.crear_carpeta(nombre=nombre, ruta_padre=r),
        )


# ── Abrir carpeta ────────────────────────────────────────────────────────────
def _abrir_carpeta(ctx, match):
    cmd_l = match.text
    for atajo, clave in _ATAJOS_CARPETA.items():
        if atajo in cmd_l:
            ctx.sistema.abrir_carpeta_conocida(clave)
            return
    for trigger in ("abre carpeta ", "abrir carpeta ", "abre la carpeta "):
        if trigger in cmd_l:
            nombre = cmd_l.split(trigger, 1)[-1].strip()
            ctx.sistema.abrir_carpeta_conocida(nombre)
            return
    ctx.say("¿Qué carpeta quieres que abra?")


# ── Buscar (web o carpeta) ─────────────────────────────────────────────────────
def _buscar(ctx, match):
    cmd_l = match.text
    resto = cmd_l
    for trigger in ("buscar información sobre ", "busca información sobre ",
                    "buscar información de ", "busca información de ",
                    "busca ", "buscar ", "encuentra "):
        if trigger in cmd_l:
            resto = cmd_l.split(trigger, 1)[-1].strip()
            break

    if not resto:
        ctx.say("¿Qué quieres que busque?")
        return

    # Caso 1: búsqueda web explícita
    for kw in _KEYWORDS_WEB:
        if resto.endswith(kw) or f" {kw} " in resto:
            consulta = resto
            for k in _KEYWORDS_WEB:
                consulta = consulta.replace(k, "").strip()
            consulta = consulta.strip(" ,.")
            if consulta:
                ctx.internet.buscar_google(consulta)
            else:
                ctx.say("¿Qué quieres buscar en internet?")
            return

    # Caso 2: "en la carpeta X"
    if "en la carpeta " in resto:
        partes = resto.split("en la carpeta ", 1)
        termino = partes[0].strip().strip(" ,.")
        nombre_carpeta = partes[1].strip()
        if termino:
            ctx.sistema.buscar_en_carpeta(termino, nombre_carpeta)
        else:
            ctx.say("¿Qué quieres buscar?")
        return

    # Caso 3: "en [carpeta conocida]"
    if " en " in resto:
        partes = resto.rsplit(" en ", 1)
        termino, destino = partes[0].strip(), partes[1].strip()
        if destino in _ALIAS_CARPETA or ctx.sistema.es_carpeta_conocida(destino):
            ctx.sistema.buscar_en_carpeta(termino, destino)
            return
        ctx.internet.buscar_google(resto)
        return

    # Caso 4: sin destino → Google
    ctx.internet.buscar_google(resto)


class FilesSkill(Skill):
    name = "files"
    category = "archivos"

    def intents(self, ctx):
        return [
            IntentSpec(
                name="files.crear_archivo", priority=220,
                matcher=contains_any(("crea archivo", "crea un archivo",
                                      "nuevo archivo", "crear archivo")),
                handler=_crear_archivo,
                description="Crea un archivo (python, txt, ...) en una carpeta",
                aliases=("crea archivo python hola en documentos",),
                examples=("crea archivo python hola en documentos",),
            ),
            IntentSpec(
                name="files.crear_carpeta", priority=230,
                matcher=contains_any(("crea carpeta", "crea una carpeta",
                                      "nueva carpeta", "crear carpeta")),
                handler=_crear_carpeta,
                description="Crea una carpeta nueva donde indiques",
                aliases=("crea carpeta proyectos en escritorio",),
                examples=("crea carpeta proyectos en escritorio",),
            ),
            IntentSpec(
                name="files.abrir_carpeta", priority=240,
                matcher=contains_any(("abre carpeta", "abrir carpeta", "abre la carpeta",
                                      "abre mis documentos", "abre documentos", "abre descargas",
                                      "abre el escritorio", "abre escritorio",
                                      "abre imágenes", "abre imagenes")),
                handler=_abrir_carpeta,
                description="Abre una carpeta conocida en el explorador",
                aliases=("abre documentos", "abre carpeta proyectos"),
                examples=("abre documentos", "abre carpeta proyectos"),
            ),
            IntentSpec(
                name="files.buscar", priority=250,
                matcher=contains_any(("busca ", "buscar ", "encuentra ",
                                      "buscar información ", "busca información ")),
                handler=_buscar,
                description="Busca en Google o dentro de una carpeta local",
                aliases=("busca gatos en internet",),
                examples=("busca gatos en internet", "busca informe en documentos"),
            ),
        ]
