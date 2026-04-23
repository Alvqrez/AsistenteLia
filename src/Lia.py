#!/usr/bin/env python3
# Asistente Lia

import numpy as np
import sounddevice as sd
import speech_recognition as sr
import pyttsx3
import webbrowser
import subprocess
import platform
import time
import threading
import datetime
import requests
import os
import json
from collections import deque
import sys


class LiaAssistant:
    def __init__(self):
        self.is_active = True
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.lia_hablando = False
        self.modo_silencioso = False  # NUEVO: Para trabajar sin interrupciones

        # --- CONFIGURACIÓN DE VOZ (TTS) ---
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 180)

        # --- CALIBRACIÓN MEJORADA DE AUDIO ---
        self.sample_rate = 44100
        self.clap_threshold = 0.08
        self.crest_factor_min = 2.8
        self.crest_factor_max = 28.0
        self.min_high_freq_ratio = 0.18  # subido para filtrar voz fuerte
        self.max_zcr = 0.50
        self.clap_duration_max = 0.18
        self.clap_cooldown = 0.12  # más corto para no perder el 3er aplauso
        self.clap_window = 2.5  # ventana un poco más amplia
        self.sequence_gap = 0.85  # silencio para cerrar la secuencia

        self.clap_events = deque(maxlen=20)
        self.last_clap_time = 0.0

        # Calibración dinámica
        self.noise_floor = 0.0
        self.calibrando = True

        # Sistema operativo
        self.os_type = platform.system()

        # NUEVO: Historial de actividades
        self.historial_file = "../lia_historial.json"
        self.historial = self.cargar_historial()

        #Pendientes en Obsidian
        self.ruta_pendientes = r"C:\Users\dell\Documents\Notas\Pendientes.md"

        # Inicialización
        self.calibrar_ruido_ambiente()
        self.hablar("Hola, aquí estoy!.")
        self.mostrar_menu()

    def calibrar_ruido_ambiente(self):
        """Calibra automáticamente el nivel de ruido del ambiente"""
        print("🎤 Calibrando ruido ambiente (mantén silencio 2 segundos)...")
        try:
            duracion = 2
            recording = sd.rec(int(duracion * self.sample_rate),
                             samplerate=self.sample_rate,
                             channels=1,
                             dtype='float32')
            sd.wait()

            self.noise_floor = np.abs(recording).max()
            # Ajusta el threshold dinámicamente
            self.clap_threshold = max(0.28, self.noise_floor * 3.5)

            print(f"✅ Calibración completa:")
            print(f"   - Ruido base: {self.noise_floor:.3f}")
            print(f"   - Threshold ajustado: {self.clap_threshold:.3f}")
            self.calibrando = False
        except Exception as e:
            print(f"⚠️ Error en calibración: {e}")
            self.calibrando = False

    def mostrar_menu(self):
        print("\n" + "=" * 60)
        print("🤖 ASISTENTE LIA v2.0 - MODO MEJORADO")
        print("=" * 60)
        print("👏 APLAUSOS:")
        print("   1 Aplauso  → Modo Estudio (ChatGPT + WhatsApp)")
        print("   2 Aplausos → Modo Programación (VS Code + GitHub + Spotify)")
        print("   3 Aplausos → Modo Juego (Discord)")
        print("\n🎤 COMANDOS DE VOZ:")
        print("   'Lia, rutina mañanera'  → Resumen completo del día")
        print("   'Lia, modo silencioso'  → Desactiva voz (solo texto)")
        print("   'Lia, habla normal'     → Reactiva voz")
        print("   'Lia, pausate'          → Pausar asistente")
        print("   'Lia, estadísticas'     → Ver uso de modos")
        print("   'Lia, ayuda'            → Mostrar este menú")
        print("=" * 60 + "\n")

    def hablar(self, texto):
        """TTS mejorado con modo silencioso"""
        print(f"🗣️ Lia: {texto}")

        if self.modo_silencioso:
            return  # No habla en modo silencioso

        try:
            self.lia_hablando = True
            engine = pyttsx3.init('sapi5')
            engine.setProperty('rate', 180)
            voices = engine.getProperty('voices')

            # Busca voz en español
            for voice in voices:
                if "spanish" in voice.name.lower() or "mexico" in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break

            engine.say(texto)
            engine.runAndWait()
            engine.stop()
            time.sleep(0.2)
        except Exception as e:
            print(f"❌ Error de voz: {e}")
        finally:
            self.lia_hablando = False

    def zcr_rate(self, audio_data):
        """
        NUEVO: Calcula Zero Crossing Rate
        Aplausos tienen ZCR alto, voz/risa tienen ZCR bajo
        """
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_data))))
        return zero_crossings / len(audio_data)

    def high_freq_ratio(self, audio_data):
        """
        Analiza frecuencias agudas (mejorado)
        Aplausos: mucha energía >3kHz
        Voz/risa: energía concentrada <2kHz
        """
        spectrum = np.abs(np.fft.rfft(audio_data))
        freqs = np.fft.rfftfreq(len(audio_data), d=1/self.sample_rate)

        # Energía en diferentes bandas
        very_high = np.sum(spectrum[freqs >= 3000])  # >3kHz (aplausos)
        high = np.sum(spectrum[(freqs >= 1500) & (freqs < 3000)])
        mid = np.sum(spectrum[(freqs >= 500) & (freqs < 1500)])
        low = np.sum(spectrum[freqs < 500])

        total = very_high + high + mid + low
        if total == 0:
            return 0

        # Los aplausos tienen mucha energía en very_high
        return very_high / total

    def is_voice_like(self, audio_data):
        """
        Detecta si el sonido se parece más a voz que a aplauso.
        La voz suele concentrarse más en graves/medios.
        """
        spectrum = np.abs(np.fft.rfft(audio_data))
        freqs = np.fft.rfftfreq(len(audio_data), d=1 / self.sample_rate)

        total = np.sum(spectrum) + 1e-9
        low = np.sum(spectrum[(freqs >= 80) & (freqs < 1500)]) / total
        high = np.sum(spectrum[freqs >= 2500]) / total
        centroid = np.sum(freqs * spectrum) / total
        dominant_freq = freqs[np.argmax(spectrum)] if len(spectrum) else 0

        # Voz fuerte: más energía en graves/medios y menos en agudos
        return (low > 0.55 and high < 0.18) or (centroid < 2200 and dominant_freq < 2200)

    def detect_clap_duration(self, audio_data):
        """
        NUEVO: Detecta la duración del pico de energía
        Aplausos son muy cortos (<150ms), voz/risa son más largos
        """
        threshold_local = self.clap_threshold * 0.7
        above_threshold = np.abs(audio_data) > threshold_local

        if not np.any(above_threshold):
            return 1.0  # Sin pico detectado

        # Encuentra el primer y último punto sobre el umbral
        indices = np.where(above_threshold)[0]
        duration_samples = indices[-1] - indices[0]
        duration_seconds = duration_samples / self.sample_rate

        return duration_seconds

    def open_url(self, url, name):
        """Abre URL con logging"""
        try:
            webbrowser.open(url)
            self.hablar(f"Abriendo {name}")
            self.registrar_actividad(f"Abrió {name}")
        except Exception as e:
            print(f"❌ Error al abrir {name}: {e}")

    def open_application(self, app_name):
        """Abre aplicación con logging mejorado"""
        try:
            if self.os_type == "Windows":
                apps = {
                    "vscode": "code",
                    "spotify": "spotify",
                    "discord": os.path.expandvars(r"%LocalAppData%\Discord\Update.exe --processStart Discord.exe")
                }
                if app_name in apps:
                    subprocess.Popen(apps[app_name], shell=True)
                    self.hablar(f"Abriendo {app_name}")
                    self.registrar_actividad(f"Abrió {app_name}")
        except Exception as e:
            self.hablar(f"Error al abrir {app_name}")
            print(f"❌ {e}")

    def abrir_desde_descargas(self, nombre_objetivo):
        """Busca y abre un archivo desde Descargas por nombre parcial"""
        try:
            carpeta_descargas = os.path.join(os.path.expanduser("~"), "Downloads")

            archivo_encontrado = None
            for root, dirs, files in os.walk(carpeta_descargas):
                for archivo in files:
                    if nombre_objetivo.lower() in archivo.lower():
                        archivo_encontrado = os.path.join(root, archivo)
                        break
                if archivo_encontrado:
                    break

            if archivo_encontrado:
                os.startfile(archivo_encontrado)
                nombre_mostrado = os.path.basename(archivo_encontrado)
                self.hablar(f"Abriendo {nombre_mostrado}")
                self.registrar_actividad(f"Abrió {nombre_mostrado}")
            else:
                self.hablar(f"No encontré {nombre_objetivo} en Descargas.")
                print(f"❌ No se encontró {nombre_objetivo} en Descargas")

        except Exception as e:
            self.hablar(f"No pude abrir {nombre_objetivo}")
            print(f"❌ Error al abrir desde Descargas: {e}")

    def cerrar_todo(self):
        """Cierra las aplicaciones abiertas por Lia"""
        print("\n🛑 CERRANDO TODO")

        procesos = [
            "chrome.exe",
            "msedge.exe",
            "firefox.exe",
            "code.exe",
            "spotify.exe",
            "discord.exe"
        ]

        for proceso in procesos:
            try:
                subprocess.run(
                    ["taskkill", "/f", "/im", proceso],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception as e:
                print(f"No se pudo cerrar {proceso}: {e}")

        self.hablar("He cerrado todas las aplicaciones.")
        self.registrar_actividad("Cerró Todo")

    # --- MODOS DE TRABAJO ---
    def modo_estudio(self):
        """Modo Estudio con logging"""
        print("\n📚 MODO ESTUDIO ACTIVADO")
        self.hablar("Activando modo estudio.")
        self.open_url("https://chat.openai.com", "ChatGPT")
        time.sleep(0.3)
        self.open_url("https://web.whatsapp.com", "WhatsApp")
        self.registrar_actividad("Modo Estudio")

    def modo_programacion(self):
        """Modo Programación con logging"""
        print("\n💻 MODO PROGRAMACIÓN ACTIVADO")
        self.hablar("Iniciando entorno de programación.")
        self.open_application("vscode")
        time.sleep(0.3)
        self.open_url("https://github.com", "GitHub")
        time.sleep(0.3)
        self.open_application("spotify")
        self.registrar_actividad("Modo Programación")

    def modo_juego(self):
        """Modo Juego con logging"""
        print("\n🎮 MODO JUEGO ACTIVADO")
        self.hablar("Todo listo para jugar.")
        self.open_application("discord")
        time.sleep(0.5)
        self.abrir_desde_descargas("TimerResolution")
        self.registrar_actividad("Modo Juego")

    def rutina_mananera(self):
        """Rutina mañanera mejorada"""
        self.hablar("Buenos días. Iniciando rutina matutina.")

        # 1. Hora actual
        ahora = datetime.datetime.now()
        hora_texto = ahora.strftime("%I:%M %p")
        if "AM" in hora_texto:
            hora_texto = hora_texto.replace("AM", "de la mañana")
        else:
            hora_texto = hora_texto.replace("PM", "de la tarde")
        self.hablar(f"Son las {hora_texto}.")

        # 2. Día de la semana
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        dia_semana = dias[ahora.weekday()]
        self.hablar(f"Hoy es {dia_semana}, {ahora.day} de {ahora.strftime('%B')}.")

        # 3. Clima detallado
        try:
            url_clima = "https://wttr.in/?format=%C+con+%t&lang=es"
            clima = requests.get(url_clima, timeout=5).text.replace("+", " ")
            self.hablar(f"El clima: {clima}.")
        except:
            self.hablar("No pude consultar el clima, pero seguro es un buen día.")

        # 4. Obsidian (si existe)
        ruta_obsidian = r"C:\Users\dell\Documents\Notas\Pendientes.md"
        if os.path.exists(ruta_obsidian):
            self.hablar("Tus pendientes son:")
            with open(ruta_obsidian, "r", encoding="utf-8") as file:
                count = 0
                for linea in file:
                    clean = linea.replace("- [ ]", "").replace("- [x]", "").replace("#", "").strip()
                    if clean and count < 5:  # Máximo 5 pendientes
                        self.hablar(clean)
                        time.sleep(0.3)
                        count += 1

        # 5. Abrir herramientas
        self.hablar("Abriendo tus herramientas esenciales.")
        self.open_url("https://github.com", "GitHub")
        time.sleep(0.5)
        self.open_url("https://calendar.google.com", "Google Calendar")

        self.registrar_actividad("Rutina Mañanera")

    def agregar_pendiente(self, texto):
        """Agrega un pendiente nuevo a la nota de Obsidian"""
        try:
            texto = texto.strip()
            texto = texto.rstrip(".")
            texto = texto.strip()

            if not texto:
                self.hablar("No entendí qué pendiente quieres agregar.")
                return

            carpeta = os.path.dirname(self.ruta_pendientes)
            if carpeta and not os.path.exists(carpeta):
                os.makedirs(carpeta, exist_ok=True)

            if not os.path.exists(self.ruta_pendientes):
                with open(self.ruta_pendientes, "w", encoding="utf-8") as f:
                    f.write("# Pendientes\n\n")

            with open(self.ruta_pendientes, "a", encoding="utf-8") as f:
                if os.path.getsize(self.ruta_pendientes) > 0:
                    f.write("\n")
                f.write(f"- [ ] {texto}\n")

            self.hablar(f"Listo, anoté: {texto}")
            self.registrar_actividad("Agregó pendiente")

        except Exception as e:
            self.hablar("No pude guardar el pendiente.")
            print(f"❌ Error al agregar pendiente: {e}")

    def decir_pendientes(self):
        """Lee los pendientes guardados en Obsidian"""
        try:
            if not os.path.exists(self.ruta_pendientes):
                self.hablar("No encontré tu lista de pendientes.")
                return

            pendientes = []

            with open(self.ruta_pendientes, "r", encoding="utf-8") as file:
                for linea in file:
                    if "- [ ]" in linea:
                        clean = linea.replace("- [ ]", "").strip()
                        if clean:
                            pendientes.append(clean)

            if not pendientes:
                self.hablar("No tienes pendientes.")
                return

            self.hablar(f"Tienes {len(pendientes)} pendientes.")

            for pendiente in pendientes[:5]:  # máximo 5
                self.hablar(pendiente)
                time.sleep(0.3)

        except Exception as e:
            print(f"❌ Error leyendo pendientes: {e}")
            self.hablar("No pude leer tus pendientes.")

    # --- SISTEMA DE HISTORIAL ---
    def cargar_historial(self):
        """Carga el historial de actividades"""
        try:
            if os.path.exists(self.historial_file):
                with open(self.historial_file, 'r') as f:
                    return json.load(f)
            return {"actividades": [], "estadisticas": {}}
        except:
            return {"actividades": [], "estadisticas": {}}

    def guardar_historial(self):
        """Guarda el historial"""
        try:
            with open(self.historial_file, 'w') as f:
                json.dump(self.historial, f, indent=2)
        except Exception as e:
            print(f"❌ Error al guardar historial: {e}")

    def registrar_actividad(self, actividad):
        """Registra una actividad en el historial"""
        timestamp = datetime.datetime.now().isoformat()
        self.historial["actividades"].append({
            "timestamp": timestamp,
            "actividad": actividad
        })

        # Actualiza estadísticas
        if actividad not in self.historial["estadisticas"]:
            self.historial["estadisticas"][actividad] = 0
        self.historial["estadisticas"][actividad] += 1

        # Guarda solo las últimas 100 actividades
        if len(self.historial["actividades"]) > 100:
            self.historial["actividades"] = self.historial["actividades"][-100:]

        self.guardar_historial()

    def mostrar_estadisticas(self):
        """Muestra estadísticas de uso"""
        print("\n" + "=" * 50)
        print("📊 ESTADÍSTICAS DE USO")
        print("=" * 50)

        if not self.historial["estadisticas"]:
            print("No hay actividades registradas aún.")
            self.hablar("No hay estadísticas disponibles todavía.")
            return

        stats = self.historial["estadisticas"]
        total = sum(stats.values())

        print(f"Total de actividades: {total}")
        print("\nDesglose por modo:")

        for actividad, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            porcentaje = (count / total) * 100
            print(f"  {actividad}: {count} veces ({porcentaje:.1f}%)")

        # Modo más usado
        modo_favorito = max(stats.items(), key=lambda x: x[1])[0]
        self.hablar(f"Has usado {total} veces tus modos. Tu favorito es {modo_favorito}.")
        print("=" * 50 + "\n")

    # --- DETECCIÓN DE AUDIO MEJORADA ---
    def detect_clap(self, audio_data):
        """
        Detección más precisa de aplausos.
        Filtra voz fuerte, risa, clicks y ruido ambiente.
        """
        if self.lia_hablando or self.calibrando:
            return False

        peak = np.max(np.abs(audio_data))
        if peak < self.clap_threshold:
            return False

        rms = np.sqrt(np.mean(audio_data ** 2))
        if rms == 0:
            return False

        # Filtro extra: voz fuerte
        if self.is_voice_like(audio_data):
            return False

        crest_factor = peak / rms
        if not (self.crest_factor_min <= crest_factor <= self.crest_factor_max):
            return False

        hf_ratio = self.high_freq_ratio(audio_data)
        if hf_ratio < self.min_high_freq_ratio:
            return False

        zcr = self.zcr_rate(audio_data)
        if zcr > self.max_zcr:
            return False

        duration = self.detect_clap_duration(audio_data)
        if duration > self.clap_duration_max:
            return False

        current_time = time.time()
        if (current_time - self.last_clap_time) < self.clap_cooldown:
            return False

        self.last_clap_time = current_time
        self.clap_events.append(current_time)

        print(f"👏 APLAUSO DETECTADO:")
        print(f"   Peak: {peak:.3f} | Crest: {crest_factor:.2f}")
        print(f"   Freq Alta: {hf_ratio:.3f} | ZCR: {zcr:.3f}")
        print(f"   Duración: {duration*1000:.1f}ms")

        return True

    def audio_callback(self, indata, frames, time_info, status):
        """Callback de audio"""
        if status:
            print(f"⚠️ Audio status: {status}")

        audio = indata[:, 0]
        self.detect_clap(audio)

    def listen_for_commands(self):
        """Escucha comandos de voz mejorada"""
        with self.microphone as source:
            print("🎤 Ajustando micrófono...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Listo para comandos de voz")

            while True:
                if not self.is_active:
                    time.sleep(0.5)
                    continue

                try:
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=5)

                    try:
                        command = self.recognizer.recognize_google(audio, language="es-MX").lower()
                        print(f"🎤 Comando: {command}")

                        if "lia" in command or "lía" in command:
                            # Comandos existentes
                            if "rutina mañanera" in command or "buenos días" in command:
                                self.rutina_mananera()

                            elif "pausa" in command or "pausate" in command:
                                self.is_active = False
                                self.hablar("Me pausaré. Despiértame con 3 aplausos.")

                            # NUEVOS COMANDOS
                            elif "modo silencioso" in command or "silencio" in command:
                                self.modo_silencioso = True
                                print("🔇 Modo silencioso activado (solo texto)")

                            elif "habla" in command or "voz" in command:
                                self.modo_silencioso = False
                                self.hablar("Modo de voz reactivado.")

                            elif "estadísticas" in command or "estadistica" in command:
                                self.mostrar_estadisticas()

                            elif "cierra todo" in command or "cerrar todo" in command:
                                self.cerrar_todo()

                            elif "pendientes" in command:
                                self.decir_pendientes()

                            elif "anota" in command or "apunta" in command or "agrega pendiente" in command or "recuerda" in command:
                                texto = command
                                texto = texto.replace("lia", "")
                                texto = texto.replace("lía", "")
                                texto = texto.replace("anota", "")
                                texto = texto.replace("apunta", "")
                                texto = texto.replace("agrega pendiente", "")
                                texto = texto.replace("recuerda", "")
                                texto = texto.strip(" ,.-:")

                                if texto:
                                    self.agregar_pendiente(texto)
                                else:
                                    self.hablar("Dime qué quieres que anote.")

                            elif "ayuda" in command or "comandos" in command:
                                self.mostrar_menu()
                                self.hablar("Te mostré el menú de comandos.")

                            elif "recalibrar" in command:
                                self.calibrar_ruido_ambiente()

                            elif "apagate" in command or "apagar" in command:
                                self.hablar("Apagando sistemas.")
                                sys.exit()

                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError as e:
                        print(f"❌ Error de reconocimiento: {e}")

                except Exception as e:
                    pass
                    time.sleep(0.5)

    def start_clap_detection(self):
        """Inicia detección de aplausos mejorada"""
        print("👏 Sistema de detección de aplausos iniciado")
        print("   (Optimizado para evitar falsos positivos)\n")

        try:
            with sd.InputStream(
                channels=1,
                samplerate=self.sample_rate,
                callback=self.audio_callback,
                blocksize=int(self.sample_rate * 0.05),
                dtype="float32"
            ):
                while True:
                    current_time = time.time()

                    # Limpia eventos viejos fuera de la ventana
                    while self.clap_events and (current_time - self.clap_events[0]) > self.clap_window:
                        self.clap_events.popleft()

                    # Procesa la secuencia cuando ya hubo silencio suficiente
                    if self.clap_events and (current_time - self.clap_events[-1]) > self.sequence_gap:
                        count = len(self.clap_events)

                        print(f"\n✅ SECUENCIA COMPLETA: {count} aplausos detectados\n")

                        if not self.is_active and count >= 3:
                            self.is_active = True
                            self.hablar("Sistemas reactivados.")

                        elif self.is_active:
                            if count == 1:
                                self.modo_estudio()
                            elif count == 2:
                                self.modo_programacion()
                            elif count >= 3:
                                self.modo_juego()

                        self.clap_events.clear()

                    time.sleep(0.05)

        except KeyboardInterrupt:
            print("\n👋 Lia desactivada por el usuario")
        except Exception as e:
            print(f"❌ Error crítico: {e}")

    def run(self):
        """Ejecuta el asistente"""
        # Thread para comandos de voz
        voice_thread = threading.Thread(target=self.listen_for_commands, daemon=True)
        voice_thread.start()

        # Loop principal de detección de aplausos
        self.start_clap_detection()


if __name__ == "__main__":
    print("Asistente Lia")

    lia = LiaAssistant()
    lia.run()
