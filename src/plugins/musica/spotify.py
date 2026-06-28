#!/usr/bin/env python3
"""
spotify.py — Control de música por voz (Windows).

Reproducir/pausar/siguiente/anterior usan las teclas multimedia del sistema
(funcionan con Spotify, YouTube, VLC... lo que tenga el foco de medios).
El volumen es el maestro de Windows. "Qué canción está sonando" lee el título
de la ventana de Spotify ("Artista - Canción" cuando reproduce).

Prioridades 92–99: deben ganar a control.pausa (100), que captura la
subcadena "pausa".
"""

from __future__ import annotations

import ctypes
import logging
import os
import threading
import time
import urllib.parse

from core.intent import IntentSpec
from core.matchers import contains_any, regex
from core.skill import Skill

logger = logging.getLogger("lia.plugin.spotify")

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

# Teclas virtuales multimedia de Windows.
_VK_MEDIA_PLAY_PAUSE = 0xB3
_VK_MEDIA_NEXT = 0xB0
_VK_MEDIA_PREV = 0xB1
_VK_VOLUME_UP = 0xAF
_VK_VOLUME_DOWN = 0xAE
_KEYEVENTF_KEYUP = 0x0002
_VK_TAB = 0x09
_VK_RETURN = 0x0D


def _tecla(vk: int, veces: int = 1) -> None:
    user32 = ctypes.windll.user32
    for _ in range(veces):
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, _KEYEVENTF_KEYUP, 0)


def _titulo_spotify() -> str | None:
    """Título de la ventana principal de Spotify, o None si no está abierto."""
    if psutil is None:
        return None
    user32 = ctypes.windll.user32
    titulos: list[str] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _enum(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            if psutil.Process(pid.value).name().lower() != "spotify.exe":
                return True
        except Exception:
            return True
        largo = user32.GetWindowTextLengthW(hwnd)
        if largo > 0:
            buf = ctypes.create_unicode_buffer(largo + 1)
            user32.GetWindowTextW(hwnd, buf, largo + 1)
            titulos.append(buf.value)
        return True

    user32.EnumWindows(_enum, 0)
    # Preferir el título "Artista - Canción" si existe.
    for t in titulos:
        if " - " in t:
            return t
    return titulos[0] if titulos else None


def _reproducir(ctx, m):
    _tecla(_VK_MEDIA_PLAY_PAUSE)
    ctx.say("Reproduciendo.")
    ctx.registrar_actividad("Reproducir/pausar música")


def _pausar(ctx, m):
    _tecla(_VK_MEDIA_PLAY_PAUSE)
    ctx.say("Música pausada.")
    ctx.registrar_actividad("Pausó la música")


def _siguiente(ctx, m):
    _tecla(_VK_MEDIA_NEXT)
    ctx.say("Siguiente canción.")


def _anterior(ctx, m):
    _tecla(_VK_MEDIA_PREV)
    ctx.say("Canción anterior.")


def _subir_volumen(ctx, m):
    _tecla(_VK_VOLUME_UP, veces=5)  # cada pulsación = 2%
    ctx.say("Volumen arriba.")


def _bajar_volumen(ctx, m):
    _tecla(_VK_VOLUME_DOWN, veces=5)
    ctx.say("Volumen abajo.")


def _volumen_a(ctx, m):
    try:
        pct = max(0, min(100, int(m.slot("pct", "50"))))
    except ValueError:
        pct = 50
    # Sin dependencias extra: bajar a 0 (50 pulsaciones de -2%) y subir pct/2.
    _tecla(_VK_VOLUME_DOWN, veces=50)
    _tecla(_VK_VOLUME_UP, veces=round(pct / 2))
    ctx.say(f"Volumen al {pct} por ciento.")


def _cancion_actual(ctx, m):
    titulo = _titulo_spotify()
    if titulo is None:
        ctx.say("No veo Spotify abierto.")
        return
    if " - " in titulo:
        artista, cancion = titulo.split(" - ", 1)
        ctx.say(f"Suena {cancion}, de {artista}.")
    else:
        ctx.say("Spotify está abierto pero no está reproduciendo nada.")


# ── Búsqueda y reproducción por nombre ───────────────────────────────────────

def _hwnd_spotify() -> int | None:
    """Devuelve el hwnd de la ventana principal de Spotify, o None."""
    if psutil is None:
        return None
    user32 = ctypes.windll.user32
    resultado: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _enum(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            if psutil.Process(pid.value).name().lower() == "spotify.exe":
                largo = user32.GetWindowTextLengthW(hwnd)
                if largo > 3:
                    resultado.append(hwnd)
                    return False
        except Exception:
            pass
        return True

    user32.EnumWindows(_enum, 0)
    return resultado[0] if resultado else None


def _abrir_busqueda_spotify(query: str) -> None:
    encoded = urllib.parse.quote(query)
    os.startfile(f"spotify:search:{encoded}")


def _intentar_reproducir_primero() -> None:
    """Espera a que Spotify cargue los resultados e intenta reproducir el primero."""
    time.sleep(2.0)
    hwnd = _hwnd_spotify()
    if not hwnd:
        return
    user32 = ctypes.windll.user32
    try:
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.4)
        # Tab navega al primer resultado de la sección Songs; Enter lo reproduce.
        _tecla(_VK_TAB)
        time.sleep(0.15)
        _tecla(_VK_RETURN)
    except Exception as ex:
        logger.debug("No se pudo auto-reproducir en Spotify: %s", ex)


def _buscar_spotify(ctx, m):
    query = m.slot("query", "").strip()
    if not query:
        ctx.say("¿Qué quieres buscar en Spotify?")
        return
    _abrir_busqueda_spotify(query)
    ctx.say(f"Buscando {query} en Spotify.")
    ctx.registrar_actividad(f"Búsqueda en Spotify: {query}")


def _poner_spotify(ctx, m):
    query = m.slot("query", "").strip()
    if not query:
        ctx.say("¿Qué canción quieres poner en Spotify?")
        return
    _abrir_busqueda_spotify(query)
    ctx.say(f"Buscando {query} en Spotify.")
    threading.Thread(target=_intentar_reproducir_primero, daemon=True).start()
    ctx.registrar_actividad(f"Poner en Spotify: {query}")


def _poner_cancion_artista_spotify(ctx, m):
    cancion = m.slot("cancion", "").strip()
    artista = m.slot("artista", "").strip()
    if not cancion:
        ctx.say("¿Qué canción quieres poner en Spotify?")
        return
    query = f"{cancion} {artista}".strip()
    _abrir_busqueda_spotify(query)
    ctx.say(f"Buscando {cancion} de {artista} en Spotify.")
    threading.Thread(target=_intentar_reproducir_primero, daemon=True).start()
    ctx.registrar_actividad(f"Poner en Spotify: {query}")


class SpotifySkill(Skill):
    name = "spotify"
    category = "musica"

    def intents(self, ctx):
        return [
            # Prioridad 85–87: más específicos que files.buscar (250) y apps.abrir (270).
            IntentSpec(
                name="musica.spotify_cancion_artista", priority=85,
                matcher=regex(
                    r"(?:pon|ponme|reproduce)\s+(?P<cancion>.+?)\s+de\s+(?P<artista>.+?)\s+en\s+spotify"
                ),
                handler=_poner_cancion_artista_spotify,
                description="Busca una canción de un artista concreto en Spotify y la reproduce",
                aliases=("pon bohemian rhapsody de queen en spotify",),
                examples=(
                    "pon bohemian rhapsody de queen en spotify",
                    "reproduce flowers de miley cyrus en spotify",
                ),
            ),
            IntentSpec(
                name="musica.spotify_poner", priority=86,
                matcher=regex(
                    r"(?:pon|ponme|reproduce)\s+(?P<query>.+?)\s+en\s+spotify"
                ),
                handler=_poner_spotify,
                description="Busca una canción o álbum en Spotify y reproduce el primer resultado",
                aliases=("pon bohemian rhapsody en spotify",),
                examples=(
                    "pon bohemian rhapsody en spotify",
                    "ponme reggaeton en spotify",
                    "reproduce lo que sea en spotify",
                ),
            ),
            IntentSpec(
                name="musica.spotify_buscar", priority=87,
                matcher=regex(
                    r"(?:busca|buscar|encuentra)\s+(?P<query>.+?)\s+en\s+spotify"
                ),
                handler=_buscar_spotify,
                description="Busca una canción, artista o álbum en Spotify (sin auto-reproducir)",
                aliases=("busca queen en spotify",),
                examples=(
                    "busca queen en spotify",
                    "busca bohemian rhapsody en spotify",
                    "encuentra bad bunny en spotify",
                ),
            ),
            IntentSpec(
                name="musica.volumen_a", priority=92,
                matcher=regex(r"volumen\s+al?\s+(?P<pct>\d{1,3})"),
                handler=_volumen_a,
                description="Fija el volumen del sistema a un porcentaje",
                aliases=("volumen al 50",),
                examples=("volumen al 50", "pon el volumen a 30"),
            ),
            IntentSpec(
                name="musica.subir_volumen", priority=93,
                matcher=contains_any(("sube el volumen", "sube volumen",
                                      "más volumen", "mas volumen", "súbele")),
                handler=_subir_volumen,
                description="Sube el volumen del sistema",
                aliases=("sube volumen", "sube el volumen"),
                examples=("sube el volumen",),
            ),
            IntentSpec(
                name="musica.bajar_volumen", priority=94,
                matcher=contains_any(("baja el volumen", "baja volumen",
                                      "menos volumen", "bájale", "bajale")),
                handler=_bajar_volumen,
                description="Baja el volumen del sistema",
                aliases=("baja volumen", "baja el volumen"),
                examples=("baja el volumen",),
            ),
            IntentSpec(
                name="musica.pausar", priority=95,
                matcher=contains_any(("pausa la música", "pausa la musica",
                                      "pausa la canción", "pausa la cancion",
                                      "pausa música", "pausa musica",
                                      "pausa spotify", "detén la canción",
                                      "deten la cancion", "detén la música",
                                      "deten la musica")),
                handler=_pausar,
                description="Pausa la música que está sonando",
                aliases=("pausa la música", "pausa spotify"),
                examples=("pausa la música", "detén la canción"),
            ),
            IntentSpec(
                name="musica.reproducir", priority=96,
                matcher=contains_any(("reproduce música", "reproduce musica",
                                      "reproduce la música", "reproduce la musica",
                                      "reproduce spotify", "reproduce en spotify",
                                      "pon música", "pon musica",
                                      "pon spotify", "play spotify",
                                      "reanuda la música", "reanuda la musica",
                                      "dale play", "continúa la música",
                                      "continua la musica")),
                handler=_reproducir,
                description="Reproduce o reanuda la música",
                aliases=("reproduce música", "pon música", "reproduce spotify"),
                examples=("reproduce música", "dale play", "reproduce spotify", "pon spotify"),
            ),
            IntentSpec(
                name="musica.siguiente", priority=97,
                matcher=contains_any(("siguiente canción", "siguiente cancion",
                                      "salta la canción", "salta la cancion",
                                      "cambia la canción", "cambia la cancion",
                                      "siguiente tema", "pasa la canción",
                                      "pasa la cancion")),
                handler=_siguiente,
                description="Salta a la siguiente canción",
                aliases=("siguiente canción",),
                examples=("siguiente canción", "salta la canción"),
            ),
            IntentSpec(
                name="musica.anterior", priority=98,
                matcher=contains_any(("canción anterior", "cancion anterior",
                                      "anterior canción", "anterior cancion",
                                      "regresa la canción", "regresa la cancion",
                                      "tema anterior")),
                handler=_anterior,
                description="Vuelve a la canción anterior",
                aliases=("canción anterior",),
                examples=("canción anterior",),
            ),
            IntentSpec(
                name="musica.cancion_actual", priority=99,
                matcher=contains_any(("qué canción está sonando", "que cancion esta sonando",
                                      "qué canción suena", "que cancion suena",
                                      "qué está sonando", "que esta sonando",
                                      "quién canta", "quien canta",
                                      "cómo se llama esta canción",
                                      "como se llama esta cancion")),
                handler=_cancion_actual,
                description="Dice qué canción está sonando en Spotify y quién la canta",
                aliases=("qué canción está sonando", "quién canta"),
                examples=("qué canción está sonando", "quién canta esta canción"),
            ),
        ]
