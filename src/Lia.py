#!/usr/bin/env python3
# Asistente Lia v3.0 - Arquitectura Modular (Bloque 1)

from mod_internet import ModuloInternet
from mod_memoria import ModuloMemoria
from mod_sistema import ModuloSistema
from mod_dev import ModuloDev

import numpy as np
import sounddevice as sd
import speech_recognition as sr
import pyttsx3
import subprocess
import platform
import time
import threading
import datetime
import os
import random
import glob
from collections import deque

# Importar los nuevos módulos
from mod_internet import ModuloInternet
from mod_memoria import ModuloMemoria


class LiaAssistant:
    def __init__(self):
        self.is_active = True
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.lia_hablando = False
        self.modo_silencioso = False
        self.ultimo_modo = None

        # --- INICIALIZAR MÓDULOS ---
        # Le pasamos la función self.hablar para que los módulos tengan voz
        self.internet = ModuloInternet(self.hablar)
        self.memoria = ModuloMemoria(self.hablar)
        self.sistema = ModuloSistema(self.hablar)
        self.dev = ModuloDev(self.hablar)

        # --- CONFIGURACIÓN DE VOZ (TTS) ---
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 175)

        # --- CALIBRACIÓN DE AUDIO ---
        self.sample_rate = 44100
        self.clap_threshold = 0.08
        self.crest_factor_min = 2.8
        self.crest_factor_max = 28.0
        self.min_high_freq_ratio = 0.20
        self.max_zcr = 0.50
        self.clap_duration_max = 0.15
        self.clap_cooldown = 0.12
        self.clap_window = 2.5
        self.sequence_gap = 0.85

        self.clap_events = deque(maxlen=20)
        self.last_clap_time = 0.0
        self.noise_floor = 0.0
        self.calibrando = True

        self.calibrar_ruido_ambiente()
        self.hablar("Hola. Sistemas modulares en línea.")

        # Activar recordatorios automáticos al iniciar
        self.memoria.recordar_pendientes_activos()

    def calibrar_ruido_ambiente(self):
        print("🎤 Calibrando ruido ambiente (mantén silencio 2 segundos)...")
        try:
            recording = sd.rec(int(2 * self.sample_rate), samplerate=self.sample_rate, channels=1, dtype='float32')
            sd.wait()
            self.noise_floor = np.abs(recording).max()
            self.clap_threshold = max(0.28, self.noise_floor * 3.5)
            print(f"✅ Calibración completa.")
            self.calibrando = False
        except Exception:
            self.calibrando = False

    def hablar(self, texto):
        print(f"🗣️ Lia: {texto}")
        if self.modo_silencioso: return

        try:
            self.lia_hablando = True
            engine = pyttsx3.init('sapi5')
            engine.setProperty('rate', 175)
            for voice in engine.getProperty('voices'):
                if "spanish" in voice.name.lower() or "mexico" in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break
            engine.say(texto)
            engine.runAndWait()
            engine.stop()
            time.sleep(0.2)
        except Exception:
            pass
        finally:
            self.lia_hablando = False

    # --- LÓGICA DE APLAUSOS (Mantenida intacta) ---
    def zcr_rate(self, audio_data):
        return np.sum(np.abs(np.diff(np.sign(audio_data)))) / len(audio_data)

    def high_freq_ratio(self, audio_data):
        spectrum = np.abs(np.fft.rfft(audio_data))
        freqs = np.fft.rfftfreq(len(audio_data), d=1 / self.sample_rate)
        total = np.sum(spectrum)
        return np.sum(spectrum[freqs >= 3000]) / total if total > 0 else 0

    def is_thump_or_voice(self, audio_data):
        spectrum = np.abs(np.fft.rfft(audio_data))
        freqs = np.fft.rfftfreq(len(audio_data), d=1 / self.sample_rate)
        total = np.sum(spectrum) + 1e-9
        if (np.sum(spectrum[freqs < 250]) / total) > 0.40: return True
        if (np.sum(spectrum[(freqs >= 80) & (freqs < 1500)]) / total) > 0.55 and (
                np.sum(spectrum[freqs >= 2500]) / total) < 0.18: return True
        return False

    def detect_clap_duration(self, audio_data):
        above_threshold = np.abs(audio_data) > (self.clap_threshold * 0.7)
        if not np.any(above_threshold): return 1.0
        indices = np.where(above_threshold)[0]
        return (indices[-1] - indices[0]) / self.sample_rate

    def detect_clap(self, audio_data):
        if self.lia_hablando or self.calibrando: return False
        peak = np.max(np.abs(audio_data))
        if peak < self.clap_threshold: return False
        rms = np.sqrt(np.mean(audio_data ** 2))
        if rms == 0 or self.is_thump_or_voice(audio_data): return False
        if not (self.crest_factor_min <= (peak / rms) <= self.crest_factor_max): return False
        if self.high_freq_ratio(audio_data) < self.min_high_freq_ratio: return False
        if self.zcr_rate(audio_data) > self.max_zcr: return False
        if self.detect_clap_duration(audio_data) > self.clap_duration_max: return False
        current_time = time.time()
        if (current_time - self.last_clap_time) < self.clap_cooldown: return False

        self.last_clap_time = current_time
        self.clap_events.append(current_time)
        print("👏 APLAUSO DETECTADO")
        return True

    # --- CONTROL DE APPS BASE ---
    def buscar_y_abrir_app(self, app_name, silent=False):
        app_name = app_name.lower().strip()
        if not silent: self.hablar(f"Buscando {app_name}...")
        paths = [
            os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs\**\*.lnk"),
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\**\*.lnk")
        ]
        archivos_lnk = []
        for path in paths: archivos_lnk.extend(glob.glob(path, recursive=True))
        for lnk in archivos_lnk:
            if app_name in os.path.basename(lnk).lower():
                try:
                    os.startfile(lnk)
                    if not silent: self.hablar(f"Iniciando {app_name}.")
                    return True
                except Exception:
                    pass
        try:
            subprocess.Popen(["start", app_name], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except:
            return False

    # --- MODOS ---
    def modo_estudio(self):
        self.hablar("Modo estudio activado.")
        self.internet.abrir_url("https://chat.openai.com", "ChatGPT", silent=True)
        self.ultimo_modo = "estudio"
        self.memoria.registrar_accion("modo_estudio")

    def modo_programacion(self):
        self.hablar("Entorno de desarrollo listo.")
        self.buscar_y_abrir_app("visual studio code", silent=True)
        self.internet.abrir_url("https://github.com", "GitHub", silent=True)
        self.ultimo_modo = "programacion"
        self.memoria.registrar_accion("modo_programacion")

    def modo_juego(self):
        self.hablar("Entorno de juego preparado.")
        self.buscar_y_abrir_app("discord", silent=True)
        ruta_tr = os.path.expandvars(r"%USERPROFILE%\Downloads\TimerResolution.exe")
        if os.path.exists(ruta_tr): os.startfile(ruta_tr)
        self.ultimo_modo = "juego"
        self.memoria.registrar_accion("modo_juego")

    # --- BUCLE PRINCIPAL ---
    def listen_for_commands(self):
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            while True:
                if not self.is_active:
                    time.sleep(0.5)
                    continue
                try:
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=5)
                    command = self.recognizer.recognize_google(audio, language="es-MX").lower()
                    print(f"🎤 > {command}")

                    if "lia" in command or "lía" in command:

                        # --- INTERNET (NUEVO) ---
                        if "busca" in command and "en google" in command:
                            consulta = command.split("busca ")[1].replace("en google", "").strip()
                            self.internet.buscar_en_google(consulta)
                            self.memoria.registrar_accion("buscar_google")

                        # --- TAREAS Y MEMORIA (REFACTORIZADO) ---
                        elif "completada" in command and "tarea" in command:
                            tarea = command.split("tarea ")[1].split(" completada")[0].strip()
                            self.memoria.completar_pendiente(tarea)
                        elif any(x in command for x in ["anota", "apunta"]):
                            texto = command.replace("lia", "").replace("anota", "").replace("apunta", "").strip(" ,.")
                            self.memoria.agregar_pendiente(texto)
                        elif "pendientes" in command:
                            self.memoria.recordar_pendientes_activos()

                        # --- SISTEMA ---
                        elif "abre " in command:
                            app = command.split("abre ")[1].strip()
                            self.buscar_y_abrir_app(app)
                            self.memoria.registrar_accion(f"abrir_{app.replace(' ', '_')}")

                            # --- ABORTAR (Modificado para cancelar apagados) ---
                        elif "aborta" in command:
                            self.sistema.cancelar_apagado()
                            self.abortar_ultimo_modo()  # Tu función original que cierra Chrome/VSCode

                        # --- CONTROL DE SISTEMA ---
                        elif "apaga la pc" in command or "apaga el equipo" in command:
                            self.sistema.apagar_pc()
                            self.memoria.registrar_accion("apagar_pc")
                        elif "reinicia" in command:
                            self.sistema.reiniciar_pc()
                        elif "el volumen" in command:
                            self.sistema.cambiar_volumen(command)

                        # --- DESARROLLO Y PROYECTOS ---
                        elif "crea proyecto en" in command:
                            # Comando: "Lia, crea proyecto en python llamado test"
                            partes = command.split("crea proyecto en ")[1].split(" llamado ")
                            if len(partes) == 2:
                                lenguaje = partes[0].strip()
                                nombre = partes[1].strip()
                                self.dev.crear_proyecto(lenguaje, nombre)
                                self.memoria.registrar_accion("crear_proyecto")
                            else:
                                self.hablar("Dime el lenguaje y luego la palabra llamado, seguido del nombre.")

                        elif "carpeta" in command and ("crea" in command or "elimina" in command):
                            # Comando: "Lia, crea carpeta pruebas"
                            accion = "crea" if "crea" in command else "elimina"
                            nombre = command.replace("lia", "").replace(accion, "").replace("carpeta", "").strip()
                            if nombre:
                                self.dev.gestionar_carpeta(accion, nombre)

                except sr.UnknownValueError:
                    pass
                except Exception as e:
                    time.sleep(0.5)

    def start_clap_detection(self):
        try:
            with sd.InputStream(channels=1, samplerate=self.sample_rate,
                                callback=lambda i, f, t, s: self.detect_clap(i[:, 0]),
                                blocksize=int(self.sample_rate * 0.05), dtype="float32"):
                while True:
                    current_time = time.time()
                    while self.clap_events and (current_time - self.clap_events[0]) > self.clap_window:
                        self.clap_events.popleft()
                    if self.clap_events and (current_time - self.clap_events[-1]) > self.sequence_gap:
                        count = len(self.clap_events)
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
            os._exit(0)

    def run(self):
        threading.Thread(target=self.listen_for_commands, daemon=True).start()
        self.start_clap_detection()


if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    LiaAssistant().run()