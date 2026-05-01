#!/usr/bin/env python3
# Personalidad J.A.R.V.I.S. para Lia: sarcástica + formal.
# Cada metodo devuelve una variante aleatoria.

import random
import datetime


class Persona:

    def __init__(self, nombre="Leonardo"):
        self.nombre = nombre

    def _r(self, opciones):
        return random.choice(opciones)

    def _saludo_horario(self):
        h = datetime.datetime.now().hour
        if 5 <= h < 12:
            return "Buenos dias"
        if 12 <= h < 19:
            return "Buenas tardes"
        return "Buenas noches"

    # ----- Inicio / arranque -----
    def saludo_inicio(self):
        return self._r([
            f"{self._saludo_horario()}, {self.nombre}. Sistemas en linea. A su disposicion.",
            f"{self._saludo_horario()}, {self.nombre}. Todos los sistemas operativos. Como siempre.",
            f"En linea, {self.nombre}. Asumo que necesitara de mi, como de costumbre.",
            f"{self._saludo_horario()}, {self.nombre}. Lia operativa y, milagrosamente, de buen humor.",
        ])

    def reactivacion(self):
        return self._r([
            f"De vuelta al servicio, {self.nombre}. Me extranio?",
            f"Sistemas reactivados. Espero que el descanso le haya servido, {self.nombre}.",
            f"Aqui estoy de nuevo, {self.nombre}. No es que tuviera adonde ir.",
        ])

    def apagado(self):
        return self._r([
            f"Apagando. Procure no extraniarme, {self.nombre}.",
            f"Sistemas en standby. Hasta luego, {self.nombre}.",
            f"Desconectando. Que la productividad lo acompanie, {self.nombre}.",
        ])

    # ----- Modos -----
    def modo_activado(self, nombre_modo):
        return self._r([
            f"Modo {nombre_modo} activado, {self.nombre}.",
            f"{nombre_modo} en marcha. Confio en que sabe lo que hace.",
            f"Modo {nombre_modo} listo, {self.nombre}. Suerte con eso.",
        ])

    def modo_estudio(self):
        return self._r([
            f"Modo Estudio activado, {self.nombre}. Intentemos concentrarnos esta vez.",
            f"Modo Estudio listo. He abierto sus distracciones... digo, sus herramientas.",
            f"Modo Estudio en marcha. Por favor, evite YouTube. Otra vez.",
        ])

    def modo_codigo(self):
        return self._r([
            f"Modo Codigo activado, {self.nombre}. Procuremos que compile a la primera.",
            f"Entorno de desarrollo listo. Stack Overflow esta a un Alt-Tab, como siempre.",
            f"Modo Codigo en linea. Buena suerte con los bugs, {self.nombre}.",
        ])

    def modo_juego(self):
        return self._r([
            f"Modo Juego activado, {self.nombre}. Recuerde que maniana hay que trabajar.",
            f"Todo listo para jugar. La productividad puede esperar, evidentemente.",
            f"Modo Juego en linea. Que gane esta vez.",
        ])

    # ----- Comandos cotidianos -----
    def gracias(self):
        return self._r([
            f"Es mi trabajo, {self.nombre}. Aunque agradezco el detalle.",
            f"Para servirle, {self.nombre}. Como si tuviera otra opcion.",
            f"De nada. Veo que aun recuerda los modales, {self.nombre}.",
            f"Siempre, {self.nombre}. Aqui estare cuando vuelva a necesitarme.",
        ])

    def saludo_corto(self):
        return self._r([
            f"Aqui estoy, {self.nombre}.",
            f"A la orden, {self.nombre}.",
            f"Diga, {self.nombre}.",
            f"Le escucho, {self.nombre}.",
        ])

    def confirmacion(self):
        return self._r([
            "Por supuesto.",
            "De inmediato.",
            "Como ordene.",
            f"Hecho, {self.nombre}.",
            "Procediendo.",
        ])

    def no_entendi(self):
        return self._r([
            f"Disculpe, {self.nombre}, podria repetirlo?",
            f"No le he entendido, {self.nombre}. Pruebe articulando.",
            f"Mi reconocimiento de voz tiene sus limites, {self.nombre}. Repitalo, por favor.",
        ])

    def pausa(self):
        return self._r([
            f"En pausa, {self.nombre}. Tres aplausos cuando me necesite.",
            f"Esperando, {self.nombre}. Tomese su tiempo.",
            "Pausada. Aprovechare para no hacer absolutamente nada.",
        ])

    def silencio(self):
        return self._r([
            "Modo silencioso. Entendido.",
            "Callando, como ordene.",
            "En silencio. Aun asi, sigo aqui.",
        ])

    def voz_reactivada(self):
        return self._r([
            f"Voz reactivada, {self.nombre}.",
            "De vuelta al aire.",
            "Sonido restablecido. Me extranio?",
        ])

    # ----- Acciones del sistema -----
    def abriendo_app(self, nombre_app):
        return self._r([
            f"Abriendo {nombre_app}.",
            f"Ahi va {nombre_app}, {self.nombre}.",
            f"{nombre_app} en camino.",
            f"Lanzando {nombre_app}.",
        ])

    def cerrando_todo(self):
        return self._r([
            f"Cerrando todo, {self.nombre}. Espero que haya guardado.",
            f"Limpiando el escritorio. Si tenia algo sin guardar, ya es tarde.",
            "Aplicaciones cerradas. Su CPU se lo agradece.",
        ])

    def app_no_encontrada(self, nombre):
        return self._r([
            f"No encuentro {nombre} en este sistema, {self.nombre}.",
            f"{nombre} no esta instalada o usted la llama distinto, {self.nombre}.",
            f"No se donde quedo {nombre}. Tal vez nunca la instalo.",
        ])

    def bloqueando_pc(self):
        return self._r([
            f"Bloqueando equipo, {self.nombre}. Disfrute la pausa.",
            "Cerrando sesion. No deje secretos a la vista la proxima vez.",
        ])

    # ----- Productividad -----
    def pendiente_agregado(self, texto):
        return self._r([
            f"Anotado: {texto}. Espero que esta vez si lo haga.",
            f"Listo, {self.nombre}. Agregue: {texto}.",
            f"Apuntado. Otro pendiente mas para la pila.",
        ])

    def tarea_completada(self, texto):
        return self._r([
            f"Excelente, {self.nombre}. Marque '{texto}' como completada.",
            f"'{texto}' fuera de la lista. Un milagro.",
            f"Hecho. Una menos, {self.nombre}.",
        ])

    def sin_pendientes(self):
        return self._r([
            f"Su lista esta vacia, {self.nombre}. Sospechoso, pero felicidades.",
            "Cero pendientes. Disfrutelo mientras dure.",
            f"Lista limpia, {self.nombre}. Esta seguro de que esta viviendo?",
        ])

    def pomodoro_inicio(self, minutos):
        return self._r([
            f"Pomodoro de {minutos} minutos, {self.nombre}. Sin distracciones.",
            f"Cronometro en marcha. {minutos} minutos de concentracion real, por favor.",
            f"{minutos} minutos. Veamos cuanto aguanta esta vez.",
        ])

    def pomodoro_fin(self):
        return self._r([
            f"Tiempo, {self.nombre}. Pausa de cinco minutos. Bien merecida.",
            "Pomodoro terminado. Estire las piernas antes de que se le atrofien.",
            "Listo. Cinco minutos para usted, antes de la siguiente ronda.",
        ])

    def recordatorio_creado(self, texto, minutos):
        return self._r([
            f"Le recordare '{texto}' en {minutos:.0f} minutos.",
            f"Recordatorio en {minutos:.0f} minutos. No se preocupe, no lo olvidare por usted.",
            f"Anotado para dentro de {minutos:.0f} minutos: {texto}.",
        ])

    def recordatorio_disparado(self, texto):
        return self._r([
            f"Recordatorio, {self.nombre}: {texto}.",
            f"Tal como prometi: {texto}.",
            f"{self.nombre}, no olvide: {texto}.",
        ])

    # ----- Informacion -----
    def cpu_ram(self, cpu, ram):
        if cpu > 80:
            extra = " Su equipo esta sufriendo, por cierto."
        elif cpu < 10:
            extra = " Tranquilidad absoluta. Casi sospechosa."
        else:
            extra = ""
        return f"CPU al {cpu:.0f} por ciento, RAM al {ram:.0f} por ciento.{extra}"

    def error_generico(self, accion):
        return self._r([
            f"No pude {accion}, {self.nombre}. Algo salio mal.",
            f"Error al {accion}. Sucede, ocasionalmente.",
            f"Fallo la operacion: {accion}. Intentemos otra cosa.",
        ])
