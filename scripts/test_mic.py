#!/usr/bin/env python3
"""
test_mic.py — Diagnóstico de micrófono independiente de Lia.
Ejecuta: python scripts/test_mic.py

Comprueba paso a paso:
  1. ¿Está PyAudio instalado?
  2. ¿Qué micrófonos están disponibles?
  3. ¿Puede grabar audio?
  4. ¿Google Speech lo reconoce?
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

print("\n══════ DIAGNÓSTICO DE MICRÓFONO ══════\n")

# 1 — PyAudio
print("1) Verificando PyAudio...")
try:
    import pyaudio
    pa = pyaudio.PyAudio()
    count = pa.get_device_count()
    print(f"   PyAudio OK — {count} dispositivos de audio encontrados")
    print("   Dispositivos de entrada disponibles:")
    for i in range(count):
        info = pa.get_device_info_by_index(i)
        if info["maxInputChannels"] > 0:
            default = " ← DEFAULT" if i == pa.get_default_input_device_info()["index"] else ""
            print(f"     [{i}] {info['name']}{default}")
    pa.terminate()
except Exception as e:
    print(f"   ERROR: {e}")
    print("   Instala PyAudio: pip install pyaudio")
    sys.exit(1)

# 2 — speech_recognition
print("\n2) Verificando speech_recognition...")
try:
    import speech_recognition as sr
    print(f"   speech_recognition v{sr.__version__} OK")
except Exception as e:
    print(f"   ERROR: {e}")
    sys.exit(1)

# 3 — Intentar abrir el micrófono y medir energía
print("\n3) Abriendo micrófono y midiendo nivel de energía...")
print("   (5 segundos — no digas nada todavía)")
try:
    r = sr.Recognizer()
    with sr.Microphone() as src:
        r.adjust_for_ambient_noise(src, duration=2)
        print(f"   Umbral de energía calibrado: {r.energy_threshold:.0f}")
        if r.energy_threshold > 4000:
            print("   ⚠  Umbral muy alto — el micrófono puede no capturar tu voz")
        elif r.energy_threshold < 200:
            print("   ⚠  Umbral muy bajo — detectará demasiado ruido")
        else:
            print("   Umbral en rango normal")
except Exception as e:
    print(f"   ERROR al abrir el micrófono: {e}")
    sys.exit(1)

# 4 — Capturar y reconocer una frase
print("\n4) Captura de voz en vivo — habla ahora:")
print("   Di cualquier cosa (tiempo límite: 8 segundos)...")
try:
    with sr.Microphone() as src:
        r2 = sr.Recognizer()
        r2.energy_threshold = 500       # umbral muy permisivo para el test
        r2.dynamic_energy_threshold = True
        r2.pause_threshold = 1.0
        print("   Escuchando...")
        audio = r2.listen(src, timeout=8, phrase_time_limit=6)
        print("   Audio capturado — enviando a Google...")
        texto = r2.recognize_google(audio, language="es-MX")
        print(f"\n   ✓ RECONOCIDO: '{texto}'")
        print("\n══════ DIAGNÓSTICO OK — El micrófono funciona ══════\n")
except sr.WaitTimeoutError:
    print("   ✗ No se detectó audio en 8 segundos")
    print("   → El umbral de energía es demasiado alto o el micrófono no funciona")
    print(f"   → Umbral actual: {r.energy_threshold:.0f}")
    print("   → Solución: baja el umbral en lia_config.json con 'mic_energy_threshold': 1000")
except sr.UnknownValueError:
    print("   ✓ Audio capturado pero no reconocido (habla más claro o revisa conexión)")
except sr.RequestError as e:
    print(f"   ✗ Error de API Google: {e}")
    print("   → Revisa tu conexión a internet")
except Exception as e:
    print(f"   ERROR: {e}")
