#!/usr/bin/env python3

import numpy as np
import sounddevice as sd
import time
from collections import deque


class AudioAnalyzer:

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    def peak(self, audio: np.ndarray) -> float:
        return float(np.max(np.abs(audio)))

    def rms(self, audio: np.ndarray) -> float:
        return float(np.sqrt(np.mean(audio ** 2)))

    def crest_factor(self, audio: np.ndarray) -> float:
        r = self.rms(audio)
        return self.peak(audio) / r if r > 1e-9 else 0.0

    def spectral_bands(self, audio: np.ndarray) -> dict:
        spectrum = np.abs(np.fft.rfft(audio))
        freqs    = np.fft.rfftfreq(len(audio), d=1.0 / self.sample_rate)
        total    = np.sum(spectrum) + 1e-12
        return {
            "sub_bass": np.sum(spectrum[freqs < 150])                          / total,
            "bass":     np.sum(spectrum[(freqs >= 150)  & (freqs < 400)])      / total,
            "low_mid":  np.sum(spectrum[(freqs >= 400)  & (freqs < 1500)])     / total,
            "high_mid": np.sum(spectrum[(freqs >= 1500) & (freqs < 3000)])     / total,
            "high":     np.sum(spectrum[freqs >= 3000])                        / total,
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
        crossings = np.sum(np.abs(np.diff(np.sign(audio))))
        return float(crossings / len(audio))

    def peak_duration(self, audio: np.ndarray, threshold_ratio: float = 0.55) -> float:
        thr     = self.peak(audio) * threshold_ratio
        indices = np.where(np.abs(audio) > thr)[0]
        if len(indices) < 2:
            return 0.0
        return float((indices[-1] - indices[0]) / self.sample_rate)

    def is_table_impact(self, audio: np.ndarray) -> bool:
        bands      = self.spectral_bands(audio)
        low_energy = bands["sub_bass"] + bands["bass"]
        duracion   = self.peak_duration(audio)
        if duracion < 0.015:
            return True
        if low_energy > 0.50:
            return True
        mid      = len(audio) // 2
        e_first  = np.sqrt(np.mean(audio[:mid] ** 2))
        e_second = np.sqrt(np.mean(audio[mid:] ** 2))
        if e_first > 1e-9 and (e_second / e_first) > 0.70:
            if bands["high"] < 0.20:
                return True
        return False

    def is_voice_like(self, audio: np.ndarray) -> bool:
        bands       = self.spectral_bands(audio)
        low_energy  = bands["sub_bass"] + bands["bass"] + bands["low_mid"]
        high_energy = bands["high"]
        centroid    = self.spectral_centroid(audio)
        dom         = self.dominant_freq(audio)
        by_bands    = (low_energy > 0.50) and (high_energy < 0.22)
        by_centroid = centroid < 2500
        by_dominant = dom < 2000
        return (by_bands and by_centroid) or by_dominant


class ClapDetector:

    def __init__(self, on_sequence, sample_rate: int = 44100):
        self.on_sequence  = on_sequence
        self.sample_rate  = sample_rate
        self.analyzer     = AudioAnalyzer(sample_rate)

        self.clap_threshold    = 0.12
        self.crest_factor_min  = 2.2
        self.crest_factor_max  = 25.0
        self.min_high_freq     = 0.12
        self.max_zcr           = 0.40
        self.max_peak_duration = 0.12
        self.clap_cooldown     = 0.15
        self.clap_window       = 2.5
        self.sequence_gap      = 0.90

        self.clap_events    = deque(maxlen=20)
        self.last_clap_time = 0.0

        self.calibrando   = True
        self.noise_floor  = 0.0
        self.lia_hablando = False
        self._active      = True

    def set_lia_hablando(self, estado: bool):
        self.lia_hablando = estado

    def set_active(self, estado: bool):
        self._active = estado

    def calibrar(self, duracion: float = 1.5) -> float:
        print(f"🎤 Calibrando ruido ambiente — mantén silencio {duracion:.0f}s…")
        try:
            rec = sd.rec(int(duracion * self.sample_rate),
                         samplerate=self.sample_rate,
                         channels=1, dtype='float32')
            sd.wait()
            self.noise_floor    = float(np.abs(rec).max())
            self.clap_threshold = max(0.15, self.noise_floor * 3.0)
            print(f"   Ruido base      : {self.noise_floor:.4f}")
            print(f"   Threshold final : {self.clap_threshold:.4f}")
        except Exception as e:
            print(f"⚠️  Calibración fallida ({e}). Usando threshold 0.15.")
        finally:
            self.calibrando = False
        return self.clap_threshold

    def _es_aplauso_valido(self, audio: np.ndarray) -> bool:
        if self.lia_hablando or self.calibrando or not self._active:
            return False
        az = self.analyzer
        pk = az.peak(audio)
        if pk < self.clap_threshold:
            return False
        rms = az.rms(audio)
        if rms < 1e-6:
            return False
        if az.is_table_impact(audio):
            return False
        if az.is_voice_like(audio):
            return False
        cf = pk / rms
        if not (self.crest_factor_min <= cf <= self.crest_factor_max):
            return False
        if az.high_freq_ratio(audio) < self.min_high_freq:
            return False
        if az.zcr(audio) > self.max_zcr:
            return False
        if az.peak_duration(audio) > self.max_peak_duration:
            return False
        now = time.time()
        if (now - self.last_clap_time) < self.clap_cooldown:
            return False
        self.last_clap_time = now
        self.clap_events.append(now)
        print(f"  👏 pk={pk:.3f}  cf={cf:.1f}"
              f"  hf={az.high_freq_ratio(audio):.2f}"
              f"  zcr={az.zcr(audio):.3f}"
              f"  dur={az.peak_duration(audio)*1000:.0f}ms")
        return True

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"⚠️  Audio: {status}")
        self._es_aplauso_valido(indata[:, 0].copy())

    def start_loop(self, shutdown_flag=None):
        print("👏 Detección de aplausos activa.\n")
        block = int(self.sample_rate * 0.05)
        with sd.InputStream(channels=1, samplerate=self.sample_rate,
                            callback=self._audio_callback,
                            blocksize=block, dtype="float32"):
            while True:
                if shutdown_flag and shutdown_flag.is_set():
                    break
                now = time.time()
                while (self.clap_events
                       and (now - self.clap_events[0]) > self.clap_window):
                    self.clap_events.popleft()
                if (self.clap_events
                        and (now - self.clap_events[-1]) > self.sequence_gap):
                    count = len(self.clap_events)
                    self.clap_events.clear()
                    print(f"\n✅ Secuencia: {count} aplauso(s)\n")
                    try:
                        self.on_sequence(count)
                    except Exception as e:
                        print(f"❌ Error en callback de secuencia: {e}")
                time.sleep(0.04)