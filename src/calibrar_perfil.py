#!/usr/bin/env python3
"""
calibrar_perfil.py — Calibración personalizada del detector de aplausos de Lia.

Guía al usuario para grabar muestras reales de:
  1. Silencio ambiente
  2. Tecleo de teclado
  3. Su voz (hablando normalmente, incluyendo "Lia, abre...")
  4. Sus aplausos

Analiza cada muestra y calcula umbrales que MAXIMIZAN la separación entre
aplausos y todo lo demás, guardándolos en data/lia_audio_profile.json.

Uso:
    python src/calibrar_perfil.py
    python src/calibrar_perfil.py --output data/lia_audio_profile.json
"""

import os
import sys
import json
import time
import argparse
import numpy as np
import sounddevice as sd

# ── Paths ─────────────────────────────────────────────────────────────────────
_SRC_DIR  = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_SRC_DIR)
_DATA_DIR = os.path.join(_ROOT_DIR, "data")
os.makedirs(_DATA_DIR, exist_ok=True)

DEFAULT_PROFILE = os.path.join(_DATA_DIR, "lia_audio_profile.json")

# Auto-detectar configuración del micrófono
try:
    _default_device = sd.default.device
    _device_info = sd.query_devices(_default_device[0])  # input device
    SAMPLE_RATE = int(_device_info["default_samplerate"])
    CHANNELS = int(_device_info["max_input_channels"])
    print(f"  Micrófono: {_device_info.get('name', 'desconocido')} | "
          f"{SAMPLE_RATE} Hz | {CHANNELS} canales\n")
except Exception as ex:
    SAMPLE_RATE = 44100
    CHANNELS = 1
    print(f"  ⚠ No se pudo detectar el micrófono ({ex}).\n"
          f"    Usando 44.1 kHz, mono.\n")

BLOCK_SIZE      = int(SAMPLE_RATE * 0.08)   # 80ms — igual que el detector


# ── Análisis espectral ────────────────────────────────────────────────────────

def _extract_features(audio: np.ndarray) -> dict:
    """
    Extrae el vector de características acústicas de un bloque de audio.
    Devuelve los mismos 6 valores que usa el detector en tiempo real.
    """
    audio = audio.flatten()
    pk    = float(np.max(np.abs(audio)))
    rms   = float(np.sqrt(np.mean(audio ** 2)))
    cf    = pk / (rms + 1e-9)

    spectrum = np.abs(np.fft.rfft(audio))
    freqs    = np.fft.rfftfreq(len(audio), d=1.0 / SAMPLE_RATE)
    total    = np.sum(spectrum) + 1e-12

    bands = {
        "sub_bass": float(np.sum(spectrum[freqs < 150])                           / total),
        "bass":     float(np.sum(spectrum[(freqs >= 150)  & (freqs < 400)])       / total),
        "low_mid":  float(np.sum(spectrum[(freqs >= 400)  & (freqs < 1500)])      / total),
        "high_mid": float(np.sum(spectrum[(freqs >= 1500) & (freqs < 3000)])      / total),
        "high":     float(np.sum(spectrum[freqs >= 3000])                         / total),
    }
    centroid = float(np.sum(freqs * spectrum) / total)

    thr_dur  = pk * 0.45
    idx_dur  = np.where(np.abs(audio) > thr_dur)[0]
    dur      = float((idx_dur[-1] - idx_dur[0]) / SAMPLE_RATE) if len(idx_dur) > 1 else 0.0

    return {
        "pk": pk, "rms": rms, "cf": cf,
        "hf": bands["high"], "centroid": centroid, "dur": dur,
        "low_energy": bands["sub_bass"] + bands["bass"] + bands["low_mid"],
        **bands
    }


def _analyze_chunks(recording: np.ndarray, min_pk: float = 0.03) -> list[dict]:
    """
    Divide una grabación en bloques de 80ms y extrae características
    de los bloques donde hay sonido real (pk > min_pk).
    """
    n      = len(recording)
    chunks = [recording[i: i + BLOCK_SIZE] for i in range(0, n - BLOCK_SIZE, BLOCK_SIZE)]
    feats  = []
    for chunk in chunks:
        f = _extract_features(chunk)
        if f["pk"] > min_pk:
            feats.append(f)
    return feats


def _percentile_safe(values: list, p: float, fallback: float) -> float:
    return float(np.percentile(values, p)) if values else fallback


# ── Grabación ─────────────────────────────────────────────────────────────────

def _grabar(segundos: float, mensaje: str) -> np.ndarray:
    print(f"\n  {mensaje}")
    for i in range(3, 0, -1):
        print(f"    {i}…", end="\r")
        time.sleep(1)
    print("    ¡Grabando! ", end="\r")
    rec = sd.rec(int(segundos * SAMPLE_RATE),
                 samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32")
    sd.wait()
    # Si es estéreo, convertir a mono (promediar canales)
    if rec.ndim > 1 and rec.shape[1] > 1:
        rec = np.mean(rec, axis=1, keepdims=True)
    print(f"    ✓ Grabado ({segundos:.0f}s)")
    return rec


# ── Secciones de calibración ──────────────────────────────────────────────────

def _calibrar_silencio() -> dict:
    print("\n─── 1/4  SILENCIO AMBIENTE ─────────────────────────────────────────")
    print("  No hagas ningún ruido. Solo el ambiente normal de tu cuarto/oficina.")
    rec   = _grabar(3, "Mantén silencio total…")
    feats = _analyze_chunks(rec, min_pk=0.0)   # incluir TODO, incluso ruido suave
    pks   = [f["pk"] for f in feats]
    rmss  = [f["rms"] for f in feats]
    noise = {
        "pk_p95":  _percentile_safe(pks,  95, 0.05),
        "rms_p95": _percentile_safe(rmss, 95, 0.01),
        "pk_max":  float(np.max(pks)) if pks else 0.05,
    }
    print(f"  Ruido ambiente → pico máx: {noise['pk_max']:.4f} | p95: {noise['pk_p95']:.4f}")
    return noise


def _calibrar_teclado() -> dict:
    print("\n─── 2/4  TECLEO ────────────────────────────────────────────────────")
    print("  Teclea normalmente durante 4 segundos. Como si estuvieras trabajando.")
    rec   = _grabar(4, "Teclea normalmente…")
    feats = _analyze_chunks(rec, min_pk=0.01)
    if not feats:
        print("  ⚠ No se captaron golpes de teclado. Verifica el micrófono.")
        return {"pk_p95": 0.08, "cf_p50": 3.5, "hf_p50": 0.25, "dur_p95": 0.015}
    pks  = [f["pk"]  for f in feats]
    cfs  = [f["cf"]  for f in feats]
    hfs  = [f["hf"]  for f in feats]
    durs = [f["dur"] for f in feats]
    stats = {
        "pk_p95":  _percentile_safe(pks,  95, 0.10),
        "pk_max":  float(np.max(pks)),
        "cf_p50":  _percentile_safe(cfs,  50, 3.5),
        "cf_p95":  _percentile_safe(cfs,  95, 6.0),
        "hf_p50":  _percentile_safe(hfs,  50, 0.25),
        "hf_p95":  _percentile_safe(hfs,  95, 0.40),
        "dur_p95": _percentile_safe(durs, 95, 0.015),
    }
    print(f"  Teclado → pk máx: {stats['pk_max']:.3f} | CF p95: {stats['cf_p95']:.1f} "
          f"| HF p50: {stats['hf_p50']:.2f} | dur p95: {stats['dur_p95']*1000:.1f}ms")
    return stats


def _calibrar_voz() -> dict:
    print("\n─── 3/4  VOZ ───────────────────────────────────────────────────────")
    print("  Habla normalmente durante 5 segundos. Di cosas como:")
    print("  'Lia, abre YouTube', 'Lia, busca el clima', 'Lia, pon música'…")
    rec   = _grabar(5, "Habla con voz normal…")
    feats = _analyze_chunks(rec, min_pk=0.02)
    if not feats:
        print("  ⚠ No se captó voz. Habla más fuerte o acerca el micrófono.")
        return {"pk_p95": 0.15, "cf_p50": 3.0, "hf_p50": 0.30, "centroid_p50": 2000.0}
    pks       = [f["pk"]       for f in feats]
    cfs       = [f["cf"]       for f in feats]
    hfs       = [f["hf"]       for f in feats]
    centroids = [f["centroid"] for f in feats]
    stats = {
        "pk_p95":        _percentile_safe(pks,       95, 0.20),
        "pk_max":        float(np.max(pks)),
        "cf_p50":        _percentile_safe(cfs,       50, 3.0),
        "cf_p95":        _percentile_safe(cfs,       95, 6.5),
        "hf_p50":        _percentile_safe(hfs,       50, 0.30),
        "hf_p95":        _percentile_safe(hfs,       95, 0.50),
        "centroid_p50":  _percentile_safe(centroids, 50, 2000.0),
        "centroid_p95":  _percentile_safe(centroids, 95, 3500.0),
    }
    print(f"  Voz → pk máx: {stats['pk_max']:.3f} | CF p95: {stats['cf_p95']:.1f} "
          f"| HF p50: {stats['hf_p50']:.2f} | centroide p50: {stats['centroid_p50']:.0f}Hz")
    return stats


def _calibrar_aplausos() -> dict:
    print("\n─── 4/4  APLAUSOS ──────────────────────────────────────────────────")
    print("  Da 5-8 aplausos normales (como cuando aplaudes de verdad).")
    print("  Pausa 0.5-1s entre cada aplauso para que los detecte por separado.")
    rec   = _grabar(8, "Aplaude 5-8 veces con pausas…")
    feats = _analyze_chunks(rec, min_pk=0.04)
    if not feats:
        print("  ⚠ No se captaron aplausos. Aplaude más fuerte.")
        return None
    pks  = [f["pk"]  for f in feats]
    cfs  = [f["cf"]  for f in feats]
    hfs  = [f["hf"]  for f in feats]
    durs = [f["dur"] for f in feats]
    stats = {
        "pk_p10":  _percentile_safe(pks,  10, 0.12),
        "pk_p50":  _percentile_safe(pks,  50, 0.20),
        "pk_min":  float(np.min(pks)),
        "cf_p10":  _percentile_safe(cfs,  10, 4.0),
        "cf_p50":  _percentile_safe(cfs,  50, 5.5),
        "hf_p10":  _percentile_safe(hfs,  10, 0.18),
        "hf_p50":  _percentile_safe(hfs,  50, 0.30),
        "dur_p10": _percentile_safe(durs, 10, 0.025),
        "dur_p90": _percentile_safe(durs, 90, 0.090),
        "count":   len(feats),
    }
    print(f"  Aplausos → pk mín: {stats['pk_min']:.3f} | CF p10: {stats['cf_p10']:.1f} "
          f"| HF p10: {stats['hf_p10']:.2f} | chunks detectados: {stats['count']}")
    return stats


# ── Cálculo de umbrales ───────────────────────────────────────────────────────

def _calcular_umbrales(silencio: dict, teclado: dict, voz: dict,
                        aplausos: dict) -> dict:
    """
    Calcula umbrales que separan aplausos de ruido/teclado/voz.
    Estrategia: el aplauso más suave debe pasar todos los filtros,
    el ruido/teclado/voz más fuerte debe fallar al menos uno.
    """
    # ── Piso de energía ───────────────────────────────────────────────────────
    # Tiene que ser mayor que el ruido ambiente y el teclado suave,
    # pero menor que el aplauso más suave grabado.
    noise_pk    = silencio["pk_p95"]
    teclado_pk  = teclado["pk_p95"]
    aplauso_min = aplausos["pk_min"]

    # Threshold = punto medio entre el máximo del ruido/teclado y el mínimo del aplauso
    piso_candidato = (max(noise_pk, teclado_pk) + aplauso_min) / 2
    # Agregar 10% de margen hacia arriba para robustez
    clap_threshold = min(piso_candidato * 1.10, aplauso_min * 0.92)
    clap_threshold = max(clap_threshold, noise_pk * 2.5, 0.07)

    # ── RMS mínimo ────────────────────────────────────────────────────────────
    min_clap_rms = max(silencio["rms_p95"] * 2.0, 0.010)

    # ── Crest factor ──────────────────────────────────────────────────────────
    # Los aplausos tienen CF ≥ cf_p10 (percentil 10 de aplausos)
    # Los falsos positivos tienen CF ≤ cf_p95 (percentil 95 de voz/teclado)
    # Si hay solapamiento, priorizamos no-falsos-positivos
    cf_min = max(aplausos["cf_p10"] * 0.85,       # 15% de margen por debajo del aplauso
                 max(voz["cf_p95"], teclado["cf_p95"]) * 0.90)
    cf_min = max(cf_min, 2.0)                      # nunca menos de 2.0

    # ── Frecuencias altas ─────────────────────────────────────────────────────
    # Los aplausos tienen HF ≥ hf_p10 de aplausos
    # Voz y teclado suelen tener HF < hf_p95 de sus muestras
    hf_candidato = aplausos["hf_p10"] * 0.80      # 20% de margen
    # Pero no puede ser tan bajo que la voz lo cruce
    hf_min = max(hf_candidato, 0.08)

    # ── Duración del pico ─────────────────────────────────────────────────────
    # Aplausos duran entre dur_p10 y dur_p90
    # Teclado tiene dur_p95 muy corto
    # Máximo = p90 del aplauso + 30% de margen
    dur_max = aplausos["dur_p90"] * 1.30
    dur_max = max(dur_max, 0.06)                   # mínimo absoluto de 60ms

    # ── Umbrales de voz para el filtro espectral ──────────────────────────────
    # El filtro de voz rechazará si:  low_energy > voz_low_thr Y centroid < voz_centroid_thr
    voz_low_thr      = voz["hf_p50"] * 0.60       # zona segura de "esto es voz"
    voz_centroid_thr = voz["centroid_p95"] * 1.10

    return {
        "clap_threshold":    round(clap_threshold, 4),
        "min_clap_rms":      round(min_clap_rms, 4),
        "crest_factor_min":  round(cf_min, 2),
        "crest_factor_max":  28.0,
        "min_high_freq":     round(hf_min, 3),
        "max_peak_duration": round(dur_max, 3),
        "voz_low_thr":       round(voz_low_thr, 3),
        "voz_centroid_thr":  round(voz_centroid_thr, 0),
        "noise_floor":       round(silencio["pk_p95"], 4),
    }


# ── Guardado ──────────────────────────────────────────────────────────────────

def _guardar_perfil(umbrales: dict, raw: dict, output_path: str):
    perfil = {
        "version":   "1.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "umbrales":  umbrales,
        "raw": raw,   # datos crudos para diagnóstico
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(perfil, f, indent=2, ensure_ascii=False)
    print(f"\n  ✓ Perfil guardado en: {output_path}")


# ── Reporte ───────────────────────────────────────────────────────────────────

def _imprimir_reporte(umbrales: dict):
    print("\n" + "="*60)
    print("  UMBRALES CALCULADOS PARA TU MICRÓFONO")
    print("="*60)
    print(f"  Piso de energía (clap_threshold):  {umbrales['clap_threshold']:.4f}")
    print(f"  RMS mínimo      (min_clap_rms):    {umbrales['min_clap_rms']:.4f}")
    print(f"  Crest factor    (mín / máx):       {umbrales['crest_factor_min']:.2f} / {umbrales['crest_factor_max']:.1f}")
    print(f"  Altas frecuencias mínimas:         {umbrales['min_high_freq']:.3f}")
    print(f"  Duración máx del pico:             {umbrales['max_peak_duration']*1000:.0f}ms")
    print(f"  Ruido ambiente detectado:          {umbrales['noise_floor']:.4f}")
    print("="*60)
    print("\n  Lia cargará este perfil automáticamente al iniciar.")
    print("  Si notas problemas, vuelve a correr: python src/calibrar_perfil.py\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def calibrar(output_path: str = DEFAULT_PROFILE):
    print("\n" + "="*60)
    print("  CALIBRACIÓN PERSONALIZADA DE APLAUSOS — LIA")
    print("="*60)
    print("""
  Vamos a grabar 4 muestras de sonido para que Lia aprenda
  a distinguir TUS aplausos de todo lo demás (voz, teclado, ruido).

  Cada sección te dirá exactamente qué hacer.
  Cuenta regresiva de 3s antes de grabar.
""")
    input("  Presiona ENTER cuando estés listo… ")

    silencio = _calibrar_silencio()
    teclado  = _calibrar_teclado()
    voz      = _calibrar_voz()
    aplausos = _calibrar_aplausos()

    if aplausos is None:
        print("\n  ✗ Calibración fallida: no se grabaron aplausos válidos.")
        print("    Intenta de nuevo en un lugar más silencioso o habla más fuerte.")
        sys.exit(1)

    print("\n─── Calculando umbrales personalizados… ────────────────────────")
    umbrales = _calcular_umbrales(silencio, teclado, voz, aplausos)
    _imprimir_reporte(umbrales)

    raw = {"silencio": silencio, "teclado": teclado, "voz": voz, "aplausos": aplausos}
    _guardar_perfil(umbrales, raw, output_path)

    return umbrales


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibración de aplausos para Lia")
    parser.add_argument("--output", default=DEFAULT_PROFILE,
                        help="Ruta del archivo de perfil de salida")
    args = parser.parse_args()
    calibrar(args.output)
