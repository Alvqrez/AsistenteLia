#!/usr/bin/env python3
# mod_audio.py — Detector de aplausos v2.
#
# PROBLEMA RAÍZ identificado: la versión anterior elevó los umbrales demasiado
# (HARD_MIN_PEAK=0.22, crest_factor_min=4.5) causando que aplausos reales no
# pasaran el filtro.  Esta versión equilibra sensibilidad vs rechazo de teclado:
#
#   • HARD_MIN_PEAK bajado a 0.13 (la mayoría de mics captura aplausos > 0.14)
#   • crest_factor_min en 3.2 (teclado ≈ 2-3, aplauso ≈ 4-8)
#   • Calibración: multiplicador 4× (antes 6×), mínimo 0.13 (antes 0.22)
#   • is_keyboard_like() sigue activo como filtro principal anti-teclado
#   • Comando "recalibra" de Lia lo resetea si las condiciones cambian

import numpy as np
import sounddevice as sd
import time
from collections import deque

# Piso absoluto — sólo filtra ruidos casi inaudibles, NO aplausos reales
HARD_MIN_PEAK = 0.13


class AudioAnalyzer:

    def __init__(self, sample_rate: int = 44100):
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
            "sub_bass": np.sum(spectrum[freqs < 150])                         / total,
            "bass":     np.sum(spectrum[(freqs >= 150)  & (freqs < 400)])     / total,
            "low_mid":  np.sum(spectrum[(freqs >= 400)  & (freqs < 1500)])    / total,
            "high_mid": np.sum(spectrum[(freqs >= 1500) & (freqs < 3000)])    / total,
            "high":     np.sum(spectrum[freqs >= 3000])                       / total,
        }

    def high_freq_ratio(self, audio: np.ndarray) -> float:
        return self.spectral_bands(audio)["high"]

    def spectral_centroid(self, audio: np.ndarray) -> float:
        spectrum = np.abs(np.fft.rfft(audio))
        freqs    = np.fft.rfftfreq(len(audio), d=1.0 / self.sample_rate)
        total    = np.sum(spectrum) + 1e-12
        return float(np.sum(freqs * spectrum) / total)

    def dominant_freq(self, audio: np.ndarray) -> float:
        spectrum = np.abs(np.fft.rfft(audio))
        freqs    = np.fft.rfftfreq(len(audio), d=1.0 / self.sample_rate)
        return float(freqs[np.argmax(spectrum)])

    def zcr(self, audio: np.ndarray) -> float:
        return float(np.sum(np.abs(np.diff(np.sign(audio)))) / len(audio))

    def peak_duration(self, audio: np.ndarray, threshold_ratio: float = 0.55) -> float:
        thr     = self.peak(audio) * threshold_ratio
        indices = np.where(np.abs(audio) > thr)[0]
        if len(indices) < 2:
            return 0.0
        return float((indices[-1] - indices[0]) / self.sample_rate)

    def is_table_impact(self, audio: np.ndarray) -> bool:
        bands      = self.spectral_bands(audio)
        low_energy = bands["sub_bass"] + bands["bass"]
        if self.peak_duration(audio) < 0.015:
            return True
        if low_energy > 0.50:
            return True
        mid      = len(audio) // 2
        e_first  = np.sqrt(np.mean(audio[:mid] ** 2))
        e_second = np.sqrt(np.mean(audio[mid:] ** 2))
        if e_first > 1e-9 and (e_second / e_first) > 0.70 and bands["high"] < 0.20:
            return True
        return False

    def is_voice_like(self, audio: np.ndarray) -> bool:
        bands      = self.spectral_bands(audio)
        low_energy = bands["sub_bass"] + bands["bass"] + bands["low_mid"]
        by_bands   = (low_energy > 0.50) and (bands["high"] < 0.22)
        return (by_bands and self.spectral_centroid(audio) < 2500) or self.dominant_freq(audio) < 2000

    def is_keyboard_like(self, audio: np.ndarray) -> bool:
        """
        Teclado: transitorios muy breves (<10 ms), crest factor moderado (< 4)
        y centroide espectral en zona media-alta (2-8 kHz).
        Se rechaza si cumple ≥ 2 criterios simultáneamente.
        A diferencia del aplauso, el teclado es demasiado breve y su CF es bajo.
        """
        score = 0

        # Criterio 1: duración de pico muy corta (< 10 ms)
        if self.peak_duration(audio) < 0.010:
            score += 1

        # Criterio 2: crest factor moderado (teclado ≈ 2-3.5; aplauso ≈ 4+)
        pk  = self.peak(audio)
        rms = self.rms(audio)
        if rms > 1e-6:
            cf = pk / rms
            if cf < 4.0:
                score += 1

        # Criterio 3: centroide espectral en zona media-alta plana
        centroid = self.spectral_centroid(audio)
        if 2000 < centroid < 8000:
            score += 1

        return score >= 2


class ClapDetector:

    def __init__(self, on_sequence, sample_rate: int = 44100):
        self.on_sequence       = on_sequence
        self.sample_rate       = sample_rate
        self.analyzer          = AudioAnalyzer(sample_rate)

        # ── Umbrales equilibrados ─────────────────────────────────────────────
        # Suficientemente altos para ignorar teclado, pero detectan aplausos reales
        self.clap_threshold    = 0.13   # mínimo de pico para considerar cualquier sonido
        self.min_clap_rms      = 0.02   # energía mínima sostenida (evita chicharras breves)
        self.crest_factor_min  = 3.2    # teclado queda en ~2-3; aplauso en ~4-8
        self.crest_factor_max  = 22.0
        self.min_high_freq     = 0.14   # fracción mínima de energía en frecuencias altas
        self.max_zcr           = 0.38
        self.max_peak_duration = 0.11   # aplausos duran 30-110 ms; teclado < 10 ms
        self.clap_cooldown     = 0.18   # evita doble conteo del mismo golpe

        self.clap_window       = 2.5
        self.sequence_gap      = 0.90
        self.clap_events       = deque(maxlen=20)
        self.last_clap_time    = 0.0
        self.calibrando        = True
        self.noise_floor       = 0.0
        self.lia_hablando      = False
        self._active           = True

    def set_lia_hablando(self, estado: bool):
        self.lia_hablando = estado

    def set_active(self, estado: bool):
        self._active = estado

    def calibrar(self, duracion: float = 2.0) -> float:
        """
        Calibración: threshold = max(0.13, noise_floor × 4).
        Multiplicador 4× — equilibrio entre rechazo de ruido y detección de aplausos.
        """
        print(f"Calibrando ruido ambiente — mantén silencio {duracion:.0f}s…")
        try:
            rec = sd.rec(int(duracion * self.sample_rate),
                         samplerate=self.sample_rate, channels=1, dtype='float32')
            sd.wait()
            self.noise_floor    = float(np.abs(rec).max())
            self.clap_threshold = max(HARD_MIN_PEAK, self.noise_floor * 4.0)
            self.min_clap_rms   = max(0.018, self.noise_floor * 1.5)
            print(f"   Ruido base: {self.noise_floor:.4f} | "
                  f"Threshold: {self.clap_threshold:.4f} | "
                  f"Min RMS: {self.min_clap_rms:.4f}")
        except Exception as e:
            print(f"Calibración fallida ({e}). Usando valores por defecto.")
        finally:
            self.calibrando = False
        return self.clap_threshold

    def _es_aplauso_valido(self, audio: np.ndarray) -> bool:
        if self.lia_hablando or self.calibrando or not self._active:
            return False

        az = self.analyzer
        pk = az.peak(audio)

        # Barrera 1: piso absoluto
        if pk < HARD_MIN_PEAK or pk < self.clap_threshold:
            return False

        # Barrera 2: energía sostenida mínima
        rms = az.rms(audio)
        if rms < self.min_clap_rms:
            return False

        # Barrera 3: filtro de ruido de teclado (el más específico)
        if az.is_keyboard_like(audio):
            return False

        # Barrera 4: golpe de mesa o voz
        if az.is_table_impact(audio) or az.is_voice_like(audio):
            return False

        # Barrera 5: crest factor (forma del transitorio)
        cf = pk / (rms + 1e-9)
        if not (self.crest_factor_min <= cf <= self.crest_factor_max):
            return False

        # Barrera 6: contenido de altas frecuencias
        if az.high_freq_ratio(audio) < self.min_high_freq:
            return False

        # Barrera 7: zero-crossing rate
        if az.zcr(audio) > self.max_zcr:
            return False

        # Barrera 8: duración del pico
        if az.peak_duration(audio) > self.max_peak_duration:
            return False

        # Barrera 9: cooldown entre aplausos
        now = time.time()
        if (now - self.last_clap_time) < self.clap_cooldown:
            return False

        self.last_clap_time = now
        self.clap_events.append(now)
        print(f"  ✓ Aplauso: pk={pk:.3f} | cf={cf:.1f} | hf={az.high_freq_ratio(audio):.2f}")
        return True

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"Audio: {status}")
        self._es_aplauso_valido(indata[:, 0].copy())

    def start_loop(self, shutdown_flag=None):
        print("Detección de aplausos activa.\n")
        block = int(self.sample_rate * 0.05)
        with sd.InputStream(channels=1, samplerate=self.sample_rate,
                            callback=self._audio_callback,
                            blocksize=block, dtype="float32"):
            while True:
                if shutdown_flag and shutdown_flag.is_set():
                    break
                now = time.time()
                while self.clap_events and (now - self.clap_events[0]) > self.clap_window:
                    self.clap_events.popleft()
                if self.clap_events and (now - self.clap_events[-1]) > self.sequence_gap:
                    count = len(self.clap_events)
                    self.clap_events.clear()
                    print(f"\nSecuencia: {count} aplauso(s)\n")
                    try:
                        self.on_sequence(count)
                    except Exception as e:
                        print(f"Error en callback: {e}")
                time.sleep(0.04)
