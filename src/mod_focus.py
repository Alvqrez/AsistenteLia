#!/usr/bin/env python3
# Modo Enfoque: bloquea sitios distractores editando el hosts file.
# Requiere permisos de administrador. Sin ellos, usa modo suave
# (recordatorios cada 5 minutos).

import logging
import os
import platform
import shutil
import threading
import time

logger = logging.getLogger("lia.focus")

SITIOS_DISTRACTORES = [
    "facebook.com", "www.facebook.com",
    "twitter.com", "www.twitter.com", "x.com", "www.x.com",
    "instagram.com", "www.instagram.com",
    "tiktok.com", "www.tiktok.com",
    "reddit.com", "www.reddit.com",
    "youtube.com", "www.youtube.com",
    "twitch.tv", "www.twitch.tv",
    "netflix.com", "www.netflix.com",
]

_HOSTS_WIN  = r"C:\Windows\System32\drivers\etc\hosts"
_HOSTS_UNIX = "/etc/hosts"
_MARCA      = "# LIA-FOCUS"


class FocusTools:

    def __init__(self, parent_lia):
        self.lia      = parent_lia
        self.persona  = parent_lia.persona
        self.os_type  = platform.system()
        self._timer   = None
        self._activo  = False
        self._fin     = None

    # ----- helpers -----
    def _hosts_path(self):
        return _HOSTS_WIN if self.os_type == "Windows" else _HOSTS_UNIX

    def _es_admin(self):
        try:
            if self.os_type == "Windows":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            return os.geteuid() == 0
        except Exception:
            return False

    def _backup(self):
        try:
            src = self._hosts_path()
            dst = src + ".lia.bak"
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
            return True
        except Exception as ex:
            logger.error("No se pudo respaldar hosts: %s", ex)
            return False

    def _restaurar(self):
        ruta = self._hosts_path()
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                lineas = f.readlines()
            nuevas = [ln for ln in lineas if _MARCA not in ln]
            with open(ruta, "w", encoding="utf-8") as f:
                f.writelines(nuevas)
        except Exception as ex:
            logger.error("Error restaurando hosts: %s", ex)

    # ----- API publica -----
    @property
    def activo(self):
        return self._activo

    def tiempo_restante(self):
        if not self._activo or not self._fin:
            return 0
        return max(0, int(self._fin - time.time()))

    def activar(self, minutos=25, sitios=None):
        if self._activo:
            self.lia.hablar(
                f"Modo enfoque ya activo, {self.persona.nombre}. "
                f"Quedan {self.tiempo_restante() // 60} minutos."
            )
            return

        sitios = sitios or SITIOS_DISTRACTORES

        if not self._es_admin():
            self.lia.hablar(
                f"Sin permisos de administrador, {self.persona.nombre}. "
                f"Activare el modo suave: recordatorios cada cinco minutos."
            )
            self._modo_suave(minutos)
            return

        if not self._backup():
            self.lia.hablar("No pude respaldar el hosts. Cancelo.")
            return

        try:
            ruta = self._hosts_path()
            with open(ruta, "a", encoding="utf-8") as f:
                f.write(f"\n{_MARCA}\n")
                for sitio in sitios:
                    f.write(f"127.0.0.1 {sitio} {_MARCA}\n")

            self._activo = True
            self._fin    = time.time() + minutos * 60
            self._timer  = threading.Timer(minutos * 60, self._auto_desactivar)
            self._timer.daemon = True
            self._timer.start()

            self.lia.hablar(
                f"Modo enfoque activado por {minutos} minutos, {self.persona.nombre}. "
                f"He bloqueado las distracciones habituales."
            )
            self.lia.registrar_actividad(f"Activo modo enfoque {minutos} min")

        except PermissionError:
            self.lia.hablar(
                "Necesito permisos de administrador para editar el hosts. "
                "Ejecute Lia como administrador."
            )
        except Exception as ex:
            logger.error("Error activando enfoque: %s", ex)
            self.lia.hablar("Hubo un problema activando el modo enfoque.")

    def desactivar(self):
        if not self._activo:
            self.lia.hablar(f"No hay modo enfoque activo, {self.persona.nombre}.")
            return

        if self._timer:
            try:
                self._timer.cancel()
            except Exception:
                pass

        if self._es_admin():
            self._restaurar()

        self._activo = False
        self._fin    = None
        self.lia.hablar(
            f"Modo enfoque desactivado, {self.persona.nombre}. "
            f"Las distracciones esperan, como siempre."
        )
        self.lia.registrar_actividad("Desactivo modo enfoque")

    def _auto_desactivar(self):
        if self._activo and self._es_admin():
            self._restaurar()
        self._activo = False
        self._fin    = None
        try:
            self.lia.hablar(
                f"Tiempo de enfoque terminado, {self.persona.nombre}. "
                f"Bien hecho. Le devuelvo el internet completo."
            )
            self.lia.registrar_actividad("Modo enfoque finalizado")
        except Exception:
            pass

    def _modo_suave(self, minutos):
        self._activo = True
        self._fin    = time.time() + minutos * 60

        def _loop():
            inicio = time.time()
            while self._activo and (time.time() - inicio) < minutos * 60:
                time.sleep(300)
                if not self._activo:
                    return
                try:
                    self.lia.hablar(
                        f"Recordatorio de enfoque, {self.persona.nombre}: "
                        f"sin redes sociales."
                    )
                except Exception:
                    pass
            self._activo = False
            self._fin    = None
            try:
                self.lia.hablar(
                    f"Periodo de enfoque cumplido, {self.persona.nombre}."
                )
            except Exception:
                pass

        threading.Thread(target=_loop, daemon=True).start()
