#!/usr/bin/env python3
"""
mod_audio.py  –  Módulo de Audio
Responsabilidades:
  · AudioAnalyzer  : análisis de señal (FFT, crest, ZCR, etc.)
  · ClapDetector   : pipeline de filtros + loop de detección de aplausos

Lia.py importa ClapDetector y le pasa un callback para recibir
la secuencia detectada sin acoplamiento circular.
"""

import numpy as np
import sounddevice as sd
import time
from collections import deque


# ══════════════════════════════════════════════════════════════
#  ANÁLISIS DE SEÑAL
# ══════════════════════════════════════════════════════════════

class AudioAnalyzer:
    """
    Analiza una ventana de audio crudo (numpy array float32).
    No sabe nada de Lia ni de aplausos: solo matemáticas de señal.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    # ── Energía ──────────────────────────────────────────────

    def peak(self, audio: np.ndarray) -> float:
        return float(np.max(np.abs(audio)))

    def rms(self, audio: np.ndarray) -> float:
        return float(np.sqrt(np.mean(audio ** 2)))

    def crest_factor(self, audio: np.ndarray) -> float:
        r = self.rms(audio)
        return self.peak(audio) / r if r > 1e-9 else 0.0

    # ── Distribución espectral ────────────────────────────────

    def spectral_bands(self, audio: np.ndarray) -> dict:
        """
        Divide la energía espectral en 5 bandas.
        Retorna fracción de energía total en cada banda.
        """
        spectrum = np.abs(np.fft.rfft(audio))
        freqs    = np.fft.rfftfreq(len(audio), d=1.0 / self.sample_rate)
        total    = np.sum(spectrum) + 1e-12

        return {
            "sub_bass": np.sum(spectrum[freqs < 150])                            / total,
            "bass":     np.sum(spectrum[(freqs >= 150)  & (freqs < 400)])        / total,
            "low_mid":  np.sum(spectrum[(freqs >= 400)  & (freqs < 1500)])       / total,
            "high_mid": np.sum(spectrum[(freqs >= 1500) & (freqs < 3000)])       / total,
            "high":     np.sum(spectrum[freqs >= 3000])                          / total,
        }

    def high_freq_ratio(self, audio: np.ndarray) -> float:
        """Fracción de energía por encima de 3 kHz (característica de aplausos)."""
        return self.spectral_bands(audio)["high"]

    def spectral_centroid(self, audio: np.ndarray) -> float:
        """Frecuencia promedio ponderada por energía."""
        spectrum = np.abs(np.fft.rfft(audio))
        freqs    = np.fft.rfftfreq(len(audio), d=1.0 / self.sample_rate)
        total    = np.sum(spectrum) + 1e-12
        return float(np.sum(freqs * spectrum) / total)

    def dominant_freq(self, audio: np.ndarray) -> float:
        """Frecuencia con mayor energía."""
        spectrum = np.abs(np.fft.rfft(audio))
        freqs    = np.fft.rfftfreq(len(audio), d=1.0 / self.sample_rate)
        return float(freqs[np.argmax(spectrum)])

    # ── Zero Crossing Rate ────────────────────────────────────

    def zcr(self, audio: np.ndarray) -> float:
        """
        Número de veces que la señal cruza el cero por muestra.
        Voz/risa: alto.  Aplausos: moderado-bajo.
        """
        crossings = np.sum(np.abs(np.diff(np.sign(audio))))
        return float(crossings / len(audio))

    # ── Duración del pico de energía ─────────────────────────

    def peak_duration(self, audio: np.ndarray,
                      threshold_ratio: float = 0.55) -> float:
        """
        Tiempo (segundos) que la señal permanece sobre threshold_ratio * peak.
        Aplausos: < 140 ms.  Voz sostenida / golpe resonante: más largo.
        """
        thr     = self.peak(audio) * threshold_ratio
        indices = np.where(np.abs(audio) > thr)[0]
        if len(indices) < 2:
            return 0.0
        return float((indices[-1] - indices[0]) / self.sample_rate)

    # ── Clasificadores de tipo de sonido ─────────────────────

    def is_table_impact(self, audio: np.ndarray) -> bool:
        bands = self.spectral_bands(audio)
        low_energy = bands["sub_bass"] + bands["bass"]
        duracion = self.peak_duration(audio)

        # 1. Filtro de Clic Mecánico (Teclado)
        # Lo dejamos en 15ms. Tu aplauso es más largo, así que pasará.
        if duracion < 0.015:
            return True

        # 2. Filtro de Graves (Mesa)
        # Subimos a 0.50. Tus aplausos tienen cuerpo, no queremos que se bloqueen.
        if low_energy > 0.50:
            return True

        # 3. Filtro de Resonancia
        mid = len(audio) // 2
        e_first = np.sqrt(np.mean(audio[:mid] ** 2))
        e_second = np.sqrt(np.mean(audio[mid:] ** 2))

        # Aumentamos el ratio a 0.70. Esto es más permisivo con el eco de tu grabación.
        if e_first > 1e-9 and (e_second / e_first) > 0.70:
            if bands["high"] < 0.20:
                return True
        return False

    def is_voice_like(self, audio: np.ndarray) -> bool:
        """
        La voz (incluso a gritos) concentra > 50 % de su energía
        por debajo de 1.5 kHz y muy poca por encima de 3 kHz.
        El centroide espectral también queda < 2500 Hz.
        """
        bands       = self.spectral_bands(audio)
        low_energy  = bands["sub_bass"] + bands["bass"] + bands["low_mid"]
        high_energy = bands["high"]
        centroid    = self.spectral_centroid(audio)
        dom         = self.dominant_freq(audio)

        by_bands    = (low_energy > 0.50) and (high_energy < 0.22)
        by_centroid = centroid < 2500
        by_dominant = dom < 2000

        return (by_bands and by_centroid) or by_dominant


# ══════════════════════════════════════════════════════════════
#  DETECCIÓN DE APLAUSOS
# ══════════════════════════════════════════════════════════════

class ClapDetector:
    """
    Detecta aplausos usando un pipeline de 8 filtros en cascada y
    notifica a Lia mediante un callback cuando se completa una secuencia.

    Uso desde Lia.py:
        detector = ClapDetector(on_sequence=self._handle_clap_sequence)
        detector.calibrar()
        detector.start_loop()   # bloqueante; correr en hilo si hace falta
    """

    def __init__(self, on_sequence, sample_rate: int = 44100):
        """
        on_sequence : callable(count: int)
            Se llama cuando se detecta una pausa tras una secuencia.
            'count' es la cantidad de aplausos contados.
        """
        self.on_sequence   = on_sequence
        self.sample_rate   = sample_rate
        self.analyzer      = AudioAnalyzer(sample_rate)

        # ── Parámetros de detección ──────────────────────────
        # Valores iniciales conservadores; calibrar() los ajusta.
        self.clap_threshold    = 0.12   # pico mínimo para pasar (se recalibra)
        self.crest_factor_min  = 2.2   # qué tan "seco/picudo" debe ser
        self.crest_factor_max  = 25.0   # evita clicks extremos
        self.min_high_freq     = 0.12   # mínimo de energía > 3 kHz
        self.max_zcr           = 0.40   # máximo de cruces por cero
        self.max_peak_duration = 0.12   # duración máxima del pico (seg)
        self.clap_cooldown     = 0.15   # segundos mínimos entre aplausos
        self.clap_window       = 2.5    # ventana de tiempo de la secuencia
        self.sequence_gap      = 0.90   # silencio que cierra la secuencia

        self.clap_events    = deque(maxlen=20)
        self.last_clap_time = 0.0

        # ── Flags de estado ──────────────────────────────────
        self.calibrando   = True
        self.noise_floor  = 0.0
        self.lia_hablando = False   # Lia.py lo actualiza para suprimir falsos
        self._active      = True    # False cuando Lia está pausada

    # ── Interfaz de control ──────────────────────────────────

    def set_lia_hablando(self, estado: bool):
        """Lia llama a esto antes/después de hablar para suprimir falsos."""
        self.lia_hablando = estado

    def set_active(self, estado: bool):
        """Habilita o deshabilita la detección (pausa de Lia)."""
        self._active = estado

    # ── Calibración ─────────────────────────────────────────

    def calibrar(self, duracion: float = 1.5) -> float:
        """
        Graba 'duracion' segundos de silencio y ajusta el threshold.
        Retorna el threshold calculado.
        """
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
            print(f"⚠️  Calibración fallida ({e}). Usando threshold 0.30.")
        finally:
            self.calibrando = False

        return self.clap_threshold

    # ── Pipeline de filtros ──────────────────────────────────

    def _es_aplauso_valido(self, audio: np.ndarray) -> bool:
        """
        8 filtros en cascada. El primero que falle descarta la muestra.
        """
        if self.lia_hablando or self.calibrando or not self._active:
            return False

        az = self.analyzer
        pk = az.peak(audio)

        # 1. Umbral de energía mínima
        if pk < self.clap_threshold:
            return False

        rms = az.rms(audio)
        if rms < 1e-6:
            return False

        # 2. Golpe de mesa / silla (resonancia grave)
        if az.is_table_impact(audio):
            return False

        # 3. Voz / grito (energía concentrada en graves-medios)
        if az.is_voice_like(audio):
            return False

        # 4. Crest factor: el sonido debe ser "seco y picudo"
        cf = pk / rms
        if not (self.crest_factor_min <= cf <= self.crest_factor_max):
            return False

        # 5. Energía en frecuencias altas (> 3 kHz)
        if az.high_freq_ratio(audio) < self.min_high_freq:
            return False

        # 6. Zero Crossing Rate
        if az.zcr(audio) > self.max_zcr:
            return False

        # 7. Duración del pico (aplausos son muy cortos)
        if az.peak_duration(audio) > self.max_peak_duration:
            return False

        # 8. Cooldown anti-eco / doble detección
        now = time.time()
        if (now - self.last_clap_time) < self.clap_cooldown:
            return False

        # ✅ Todos los filtros pasados
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

    # ── Loop principal ───────────────────────────────────────

    def start_loop(self, shutdown_flag=None):
        """
        Abre el stream de audio y procesa secuencias de aplausos.
        Bloqueante. Llama a self.on_sequence(count) cuando detecta una.

        shutdown_flag : threading.Event opcional para detener el loop.
        """
        print("👏 Detección de aplausos activa.\n")
        block = int(self.sample_rate * 0.05)   # 50 ms por bloque

        with sd.InputStream(channels=1,
                            samplerate=self.sample_rate,
                            callback=self._audio_callback,
                            blocksize=block,
                            dtype="float32"):
            while True:
                if shutdown_flag and shutdown_flag.is_set():
                    break

                now = time.time()

                # Purga eventos fuera de la ventana de tiempo
                while (self.clap_events
                       and (now - self.clap_events[0]) > self.clap_window):
                    self.clap_events.popleft()

                # Si hay silencio después de la secuencia → procesar
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