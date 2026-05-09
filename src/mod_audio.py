#!/usr/bin/env python3
"""
mod_audio.py — Detector de aplausos v4 (basado en perfil personalizado)

Al iniciar, carga data/lia_audio_profile.json generado por calibrar_perfil.py.
Si no existe el perfil, usa defaults conservadores y avisa al usuario.

El detector usa los umbrales exactos del perfil para distinguir aplausos
de voz, teclado y ruido ambiente medidos en el entorno real del usuario.
"""

import json
import logging
import os
import sys
import time
from collections import deque

import numpy as np
import sounddevice as sd

logger = logging.getLogger("lia.audio")

# ── Paths ──────────────────────────────────────────────────────────────────────
_SRC_DIR      = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR     = os.path.dirname(_SRC_DIR)
_DATA_DIR     = os.path.join(_ROOT_DIR, "data")
PROFILE_PATH  = os.path.join(_DATA_DIR, "lia_audio_profile.json")

# ── Paths ──────────────────────────────────────────────────────────────────────
_SRC_DIR      = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR     = os.path.dirname(_SRC_DIR)
_DATA_DIR     = os.path.join(_ROOT_DIR, "data")
PROFILE_PATH  = os.path.join(_DATA_DIR, "lia_audio_profile.json")

# Auto-detectar configuración del micrófono por defecto
try:
    _default_device = sd.default.device
    _device_info = sd.query_devices(_default_device[0])  # input device
    SAMPLE_RATE = int(_device_info["default_samplerate"])
    CHANNELS = int(_device_info["max_input_channels"])
    logger_init = logging.getLogger("lia.audio.init")
    logger_init.info("Micrófono detectado: %s | %d Hz | %d canales",
                     _device_info.get("name", "desconocido"), SAMPLE_RATE, CHANNELS)
except Exception as ex:
    # Fallback si no se puede detectar
    SAMPLE_RATE = 44100
    CHANNELS = 1
    logger_init = logging.getLogger("lia.audio.init")
    logger_init.warning("No se pudo detectar el micrófono (%s). Usando 44.1 kHz, mono.", ex)

BLOCK_MS      = 80               # ms por bloque de análisis
BLOCK_SIZE    = int(SAMPLE_RATE * BLOCK_MS / 1000)

# Defaults conservadores usados SOLO si no existe perfil calibrado
# Ajustados para 48 kHz (más sensibles que 44.1 kHz)
_DEFAULTS = {
    "clap_threshold":    0.12,    # antes 0.15 — más permisivo
    "min_clap_rms":      0.015,   # antes 0.020 — más sensible
    "crest_factor_min":  3.5,     # antes 4.0 — captura aplausos suaves
    "crest_factor_max":  28.0,
    "min_high_freq":     0.15,    # antes 0.18 — menos restrictivo
    "max_peak_duration": 0.12,    # antes 0.10 — 48kHz requiere más tiempo
    "voz_low_thr":       0.18,    # antes 0.20
    "voz_centroid_thr":  3500.0,
    "noise_floor":       0.05,
}


# ── Carga de perfil ────────────────────────────────────────────────────────────

def cargar_perfil(path: str = PROFILE_PATH) -> dict:
    """
    Carga el perfil personalizado de calibración.
    Si no existe o está corrupto, devuelve defaults y registra una advertencia.
    """
    if not os.path.exists(path):
        logger.warning(
            "Perfil de audio no encontrado (%s). "
            "Ejecuta 'python src/calibrar_perfil.py' para calibrar el detector. "
            "Usando valores por defecto.", path
        )
        return dict(_DEFAULTS)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        umbrales = data.get("umbrales", {})
        # Completar cualquier clave faltante con el default correspondiente
        for k, v in _DEFAULTS.items():
            umbrales.setdefault(k, v)
        logger.info("Perfil de audio cargado desde %s (calibrado: %s)",
                    path, data.get("timestamp", "desconocido"))
        return umbrales
    except Exception as ex:
        logger.error("Error al leer perfil de audio (%s): %s. Usando defaults.", path, ex)
        return dict(_DEFAULTS)


# ── Analizador espectral ───────────────────────────────────────────────────────

class AudioAnalyzer:

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def peak(self, audio: np.ndarray) -> float:
        return float(np.max(np.abs(audio)))

    def rms(self, audio: np.ndarray) -> float:
        return float(np.sqrt(np.mean(audio ** 2)))

    def spectral_bands(self, audio: np.ndarray) -> dict:
        spectrum = np.abs(np.fft.rfft(audio))
        freqs    = np.fft.rfftfreq(len(audio), d=1.0 / self.sample_rate)
        total    = np.sum(spectrum) + 1e-12
        return {
            "sub_bass": float(np.sum(spectrum[freqs < 150])                         / total),
            "bass":     float(np.sum(spectrum[(freqs >= 150)  & (freqs < 400)])     / total),
            "low_mid":  float(np.sum(spectrum[(freqs >= 400)  & (freqs < 1500)])    / total),
            "high_mid": float(np.sum(spectrum[(freqs >= 1500) & (freqs < 3000)])    / total),
            "high":     float(np.sum(spectrum[freqs >= 3000])                       / total),
        }

    def high_freq_ratio(self, audio: np.ndarray) -> float:
        return self.spectral_bands(audio)["high"]

    def spectral_centroid(self, audio: np.ndarray) -> float:
        spectrum = np.abs(np.fft.rfft(audio))
        freqs    = np.fft.rfftfreq(len(audio), d=1.0 / self.sample_rate)
        total    = np.sum(spectrum) + 1e-12
        return float(np.sum(freqs * spectrum) / total)

    def peak_duration(self, audio: np.ndarray, threshold_ratio: float = 0.45) -> float:
        thr     = self.peak(audio) * threshold_ratio
        indices = np.where(np.abs(audio) > thr)[0]
        if len(indices) < 2:
            return 0.0
        return float((indices[-1] - indices[0]) / self.sample_rate)


# ── Detector de aplausos ───────────────────────────────────────────────────────

class ClapDetector:
    """
    Detecta aplausos usando umbrales obtenidos de la calibración personalizada
    (data/lia_audio_profile.json). Si no existe el perfil, usa defaults y avisa.

    Para recalibrar:
        python src/calibrar_perfil.py
    O decirle a Lia:
        "Lia, calibrar aplausos"
    """

    def __init__(self, on_sequence, sample_rate: int = SAMPLE_RATE):
        self.on_sequence  = on_sequence
        self.sample_rate  = sample_rate
        self.analyzer     = AudioAnalyzer(sample_rate)

        # Cargar perfil personalizado
        perfil = cargar_perfil()
        self._aplicar_perfil(perfil)

        self.clap_window    = 3.0    # antes 2.5s — ventana más amplia
        self.sequence_gap   = 1.2    # antes 0.9s — más tolerancia entre aplausos
        self.clap_cooldown  = 0.16
        self.clap_events    = deque(maxlen=20)
        self.last_clap_time = 0.0

        self.calibrando   = False
        self.lia_hablando = False
        self._active      = True
        self._voz_hasta   = 0.0   # supresión temporal por voz detectada

    def _aplicar_perfil(self, perfil: dict):
        """Aplica los valores del perfil a los atributos de detección."""
        self.clap_threshold    = perfil["clap_threshold"]
        self.min_clap_rms      = perfil["min_clap_rms"]
        self.crest_factor_min  = perfil["crest_factor_min"]
        self.crest_factor_max  = perfil["crest_factor_max"]
        self.min_high_freq     = perfil["min_high_freq"]
        self.max_peak_duration = perfil["max_peak_duration"]
        self.voz_low_thr       = perfil["voz_low_thr"]
        self.voz_centroid_thr  = perfil["voz_centroid_thr"]
        self.noise_floor       = perfil["noise_floor"]

    def recargar_perfil(self):
        """Recarga el perfil desde disco (útil tras recalibrar)."""
        perfil = cargar_perfil()
        self._aplicar_perfil(perfil)
        logger.info("Perfil de audio recargado.")

    # ── Control externo ────────────────────────────────────────────────────────

    def set_lia_hablando(self, estado: bool):
        self.lia_hablando = estado

    def set_active(self, estado: bool):
        self._active = estado

    def notificar_voz_detectada(self, duracion_supresion: float = 1.5):
        """
        Llamar desde el reconocedor de voz al capturar audio.
        Suprime el detector por `duracion_supresion` segundos para evitar
        que plosivos del habla ("Lia, abre") se cuenten como aplausos.
        """
        self._voz_hasta = time.time() + duracion_supresion

    # ── Clasificación ──────────────────────────────────────────────────────────

    def _es_voz(self, audio: np.ndarray) -> bool:
        """
        Usa los umbrales de voz del perfil en vez de condiciones hardcodeadas.
        Un sonido es "voz" si su contenido de altas frecuencias es bajo
        relativo a lo que se midió en la calibración.
        """
        az    = self.analyzer
        bands = az.spectral_bands(audio)
        low_e = bands["sub_bass"] + bands["bass"] + bands["low_mid"]
        hf    = bands["high"]
        cent  = az.spectral_centroid(audio)

        # Si tiene mucha energía baja Y centroide bajo → voz/plosivo
        if low_e > 0.45 and cent < self.voz_centroid_thr:
            return True
        # Si sus altas frecuencias son bajas relativo al umbral del perfil
        if hf < self.voz_low_thr and low_e > 0.35:
            return True
        return False

    def _es_aplauso_valido(self, audio: np.ndarray) -> bool:
        # Guards globales
        if self.lia_hablando or self.calibrando or not self._active:
            return False
        if time.time() < self._voz_hasta:
            return False

        az = self.analyzer
        pk = az.peak(audio)

        # ── B1: Piso de energía (del perfil) ──────────────────────────────────
        if pk < self.clap_threshold:
            return False

        rms = az.rms(audio)

        # ── B2: RMS mínimo ────────────────────────────────────────────────────
        if rms < self.min_clap_rms:
            return False

        # ── B3: Filtro de voz/plosivos (umbrales del perfil) ─────────────────
        if self._es_voz(audio):
            return False

        # ── B4: Crest factor ──────────────────────────────────────────────────
        cf = pk / (rms + 1e-9)
        if not (self.crest_factor_min <= cf <= self.crest_factor_max):
            return False

        # ── B5: Contenido de altas frecuencias ───────────────────────────────
        hf = az.high_freq_ratio(audio)
        if hf < self.min_high_freq:
            return False

        # ── B6: Duración del pico ─────────────────────────────────────────────
        dur = az.peak_duration(audio)
        if dur > self.max_peak_duration:
            return False

        # ── B7: Cooldown ──────────────────────────────────────────────────────
        now = time.time()
        if (now - self.last_clap_time) < self.clap_cooldown:
            return False

        self.last_clap_time = now
        self.clap_events.append(now)
        logger.debug("Aplauso: pk=%.3f cf=%.1f hf=%.2f dur=%.3f", pk, cf, hf, dur)
        print(f"  ✓ Aplauso: pk={pk:.3f} cf={cf:.1f} hf={hf:.2f} dur={dur:.3f}")
        return True

    # ── Callback y loop ────────────────────────────────────────────────────────

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.debug("Audio status: %s", status)
        # Convertir estéreo a mono si es necesario
        audio = indata[:, 0].copy() if indata.shape[1] > 1 else indata[:, 0].copy()
        self._es_aplauso_valido(audio)

    def start_loop(self, shutdown_flag=None):
        logger.info("Detección de aplausos activa (perfil: %s, %d Hz, %d canales).",
                    PROFILE_PATH, SAMPLE_RATE, CHANNELS)
        print(f"Detección de aplausos activa ({SAMPLE_RATE} Hz, {CHANNELS} canales).\n")

        if not os.path.exists(PROFILE_PATH):
            print("  ⚠  Sin perfil calibrado. Para mejor precisión ejecuta:")
            print("     python src/calibrar_perfil.py\n")

        with sd.InputStream(channels=CHANNELS, samplerate=self.sample_rate,
                            callback=self._audio_callback,
                            blocksize=BLOCK_SIZE, dtype="float32"):
            while True:
                if shutdown_flag and shutdown_flag.is_set():
                    break
                now = time.time()
                # Limpiar eventos fuera de la ventana de tiempo
                while self.clap_events and (now - self.clap_events[0]) > self.clap_window:
                    self.clap_events.popleft()
                # Disparar callback cuando la secuencia esté completa
                if self.clap_events and (now - self.clap_events[-1]) > self.sequence_gap:
                    count = len(self.clap_events)
                    self.clap_events.clear()
                    print(f"\nSecuencia: {count} aplauso(s)\n")
                    try:
                        self.on_sequence(count)
                    except Exception as ex:
                        logger.error("Error en callback de secuencia: %s", ex)
                time.sleep(0.04)
