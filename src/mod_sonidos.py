#!/usr/bin/env python3

import threading
import platform

_OS = platform.system()

if _OS == "Windows":
    import winsound
    def _beep(freq: int, dur: int):
        try:
            winsound.Beep(freq, dur)
        except Exception:
            pass
else:
    def _beep(freq: int, dur: int):
        try:
            import subprocess
            subprocess.run(
                ["python3", "-c",
                 f"import math,wave,struct,os; "
                 f"sr=44100; f={freq}; d={dur}/1000; "
                 f"frames=[struct.pack('<h',int(32767*math.sin(2*math.pi*f*i/sr))) for i in range(int(sr*d))]; "
                 f"open('/tmp/_lia_beep.wav','wb').write(b'RIFF'+struct.pack('<I',36+len(frames)*2)+b'WAVEfmt '+struct.pack('<IHHIIHH',16,1,1,sr,sr*2,2,16)+b'data'+struct.pack('<I',len(frames)*2)+b''.join(frames)); "
                 f"os.system('aplay /tmp/_lia_beep.wav -q 2>/dev/null')"],
                timeout=2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass


def _play(secuencia: list):
    for freq, dur in secuencia:
        _beep(freq, dur)


def _en_hilo(secuencia: list):
    t = threading.Thread(target=_play, args=(secuencia,), daemon=True)
    t.start()


def sonido_inicio():
    _en_hilo([(440, 80), (550, 80), (660, 120)])


def sonido_escuchando():
    _en_hilo([(880, 60)])


def sonido_confirmacion():
    _en_hilo([(660, 70), (880, 100)])


def sonido_error():
    _en_hilo([(300, 120), (250, 150)])


def sonido_cancelar():
    _en_hilo([(500, 80), (350, 120)])


def sonido_apagado():
    _play([(660, 80), (550, 80), (440, 120)])