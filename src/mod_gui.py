#!/usr/bin/env python3
"""
mod_gui.py — Interfaz Glass Luxury (grafito + platino, modo oscuro)
====================================================================
Estética minimalista premium:
    - Fondo grafito profundo casi negro.
    - Acentos en platino (gris claro luminoso).
    - Paneles de cristal con borde sutil.
    - Tipografía sistema con tracking ancho en títulos.

Pestañas:
    Estado · Aplausos · Resumen · Enfoque · Ajustes
"""

import json
import os
import sys
import threading
from datetime import datetime

from PySide6.QtCore import (Qt, QThread, Signal, QTimer, QSize)
from PySide6.QtGui import (QColor, QFont, QIcon, QPainter, QPixmap,
                            QPen, QBrush, QAction, QPalette)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QComboBox, QSpinBox, QTextEdit, QFrame,
    QDialog, QDialogButtonBox, QSystemTrayIcon, QMenu,
    QMessageBox, QFileDialog, QCheckBox,
    QGraphicsDropShadowEffect, QProgressBar
)

_SRC_DIR    = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR   = os.path.dirname(_SRC_DIR)
_MODOS_PATH = os.path.join(_ROOT_DIR, "../lia_modos.json")

# ─────────────────────────────────────────────────────────────────
#  PALETA — Glass Luxury (grafito + platino, dark mode)
# ─────────────────────────────────────────────────────────────────
_C_BG_DEEP   = "#0c0d10"      # negro grafito profundo
_C_BG_BASE   = "#15171c"      # superficie base
_C_GLASS_1   = "#1c1f25"      # cristal claro
_C_GLASS_2   = "#22262e"      # cristal más claro
_C_GLASS_3   = "#2a2e37"      # hover / selección suave
_C_BORDER    = "#2f333d"
_C_BORDER_HI = "#3a3f4a"

_C_TEXT      = "#e6e8ec"      # platino claro
_C_TEXT_DIM  = "#a8aeb8"
_C_MUTED     = "#6c727d"

_C_ACCENT    = "#c9ccd2"      # platino acento
_C_ACCENT_HI = "#e8eaee"      # platino brillante
_C_ACCENT_LO = "#7d8088"

_C_SUCCESS   = "#7ec894"
_C_WARN      = "#d4b574"
_C_ERROR     = "#cc7a7a"
_C_INFO      = "#8aa8c8"


def _make_icon(color: str = _C_ACCENT, size: int = 32) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidth(2)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(3, 3, size - 6, size - 6)
    p.setBrush(QBrush(QColor(color)))
    p.setPen(Qt.NoPen)
    inner = size // 4
    p.drawEllipse((size - inner) // 2, (size - inner) // 2, inner, inner)
    p.end()
    return QIcon(pix)


def _status_dot(color: str, size: int = 10) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QBrush(QColor(color + "60")))
    p.setPen(Qt.NoPen)
    p.drawEllipse(0, 0, size, size)
    p.setBrush(QBrush(QColor(color)))
    p.drawEllipse(size // 4, size // 4, size // 2, size // 2)
    p.end()
    return pix


STYLE_GLOBAL = f"""
* {{ font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif; }}

QWidget {{
    background-color: {_C_BG_DEEP};
    color: {_C_TEXT};
    font-size: 13px;
    selection-background-color: {_C_ACCENT_LO};
    selection-color: {_C_TEXT};
}}
QMainWindow {{ background-color: {_C_BG_DEEP}; }}

QTabWidget::pane {{
    border: 1px solid {_C_BORDER};
    border-top: none;
    background: {_C_GLASS_1};
    border-bottom-left-radius: 14px;
    border-bottom-right-radius: 14px;
}}
QTabBar {{ background: transparent; qproperty-drawBase: 0; }}
QTabBar::tab {{
    background: transparent;
    color: {_C_TEXT_DIM};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 13px 22px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.6px;
    text-transform: uppercase;
}}
QTabBar::tab:hover:!selected {{ color: {_C_TEXT}; }}
QTabBar::tab:selected {{
    color: {_C_ACCENT_HI};
    border-bottom: 2px solid {_C_ACCENT};
}}

QPushButton {{
    background: {_C_GLASS_2};
    color: {_C_TEXT};
    border: 1px solid {_C_BORDER};
    border-radius: 10px;
    padding: 9px 18px;
    font-weight: 500;
    font-size: 12px;
    letter-spacing: 0.4px;
}}
QPushButton:hover {{
    background: {_C_GLASS_3};
    border-color: {_C_BORDER_HI};
    color: {_C_ACCENT_HI};
}}
QPushButton:pressed {{ background: {_C_BG_BASE}; }}
QPushButton:disabled {{ color: {_C_MUTED}; background: {_C_GLASS_1}; }}
QPushButton#btn_primary {{
    background: {_C_ACCENT};
    color: {_C_BG_DEEP};
    border: 1px solid {_C_ACCENT};
    font-weight: 600;
    padding: 11px 24px;
}}
QPushButton#btn_primary:hover {{
    background: {_C_ACCENT_HI};
    color: {_C_BG_DEEP};
}}
QPushButton#btn_danger {{
    background: transparent;
    border-color: {_C_ERROR};
    color: {_C_ERROR};
}}
QPushButton#btn_danger:hover {{ background: {_C_ERROR}22; color: {_C_ERROR}; }}
QPushButton#btn_success {{
    background: transparent;
    border-color: {_C_SUCCESS};
    color: {_C_SUCCESS};
}}
QPushButton#btn_success:hover {{ background: {_C_SUCCESS}22; }}
QPushButton#btn_ghost {{
    background: transparent;
    border: 1px solid {_C_BORDER};
    color: {_C_TEXT_DIM};
}}
QPushButton#btn_ghost:hover {{ color: {_C_ACCENT_HI}; border-color: {_C_BORDER_HI}; }}

QLineEdit, QComboBox, QSpinBox {{
    background: {_C_BG_BASE};
    border: 1px solid {_C_BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    color: {_C_TEXT};
    font-size: 12px;
    selection-background-color: {_C_ACCENT_LO};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {_C_ACCENT};
    background: {_C_GLASS_1};
}}
QComboBox::drop-down {{ border: none; padding-right: 10px; width: 16px; }}
QComboBox QAbstractItemView {{
    background: {_C_GLASS_2};
    border: 1px solid {_C_BORDER_HI};
    border-radius: 8px;
    selection-background-color: {_C_GLASS_3};
    selection-color: {_C_ACCENT_HI};
    padding: 4px;
    outline: 0;
}}

QTableWidget {{
    background: {_C_BG_BASE};
    border: 1px solid {_C_BORDER};
    border-radius: 10px;
    gridline-color: transparent;
    selection-background-color: {_C_GLASS_3};
    selection-color: {_C_ACCENT_HI};
    alternate-background-color: {_C_GLASS_1};
}}
QTableWidget::item {{
    padding: 10px;
    border-bottom: 1px solid {_C_BORDER};
}}
QTableWidget::item:selected {{ background: {_C_GLASS_3}; color: {_C_ACCENT_HI}; }}
QHeaderView::section {{
    background: {_C_GLASS_1};
    color: {_C_MUTED};
    border: none;
    border-bottom: 1px solid {_C_BORDER};
    padding: 12px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
}}

QTextEdit {{
    background: {_C_BG_BASE};
    border: 1px solid {_C_BORDER};
    border-radius: 10px;
    padding: 12px;
    font-family: "JetBrains Mono", "Consolas", "Menlo", monospace;
    font-size: 11px;
    color: {_C_TEXT_DIM};
    selection-background-color: {_C_ACCENT_LO};
}}

QScrollBar:vertical {{ background: transparent; width: 6px; margin: 4px; }}
QScrollBar::handle:vertical {{
    background: {_C_BORDER_HI};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {_C_ACCENT_LO}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QFrame#separator {{ background: {_C_BORDER}; max-height: 1px; }}
QFrame#separator_lux {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 transparent, stop:0.5 {_C_BORDER_HI}, stop:1 transparent);
    max-height: 1px;
}}
QCheckBox {{ color: {_C_TEXT}; font-size: 12px; spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {_C_BORDER_HI};
    border-radius: 4px;
    background: {_C_BG_BASE};
}}
QCheckBox::indicator:checked {{
    background: {_C_ACCENT};
    border-color: {_C_ACCENT};
}}
QProgressBar {{
    background: {_C_BG_BASE};
    border: 1px solid {_C_BORDER};
    border-radius: 6px;
    text-align: center;
    color: {_C_TEXT_DIM};
    font-size: 11px;
    height: 12px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {_C_ACCENT_LO}, stop:1 {_C_ACCENT});
    border-radius: 5px;
}}

QLabel#title_huge {{
    color: {_C_ACCENT_HI};
    font-size: 36px;
    font-weight: 200;
    letter-spacing: 8px;
    background: transparent;
}}
QLabel#title_section {{
    color: {_C_MUTED};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    background: transparent;
}}
QLabel#subtitle {{
    color: {_C_TEXT_DIM};
    font-size: 11px;
    letter-spacing: 1px;
    background: transparent;
}}
QLabel#muted {{
    color: {_C_MUTED};
    font-size: 11px;
    background: transparent;
}}
"""


# ═══════════════════════════════════════════════════════════════════
class LiaWorker(QThread):
    status_changed  = Signal(str)
    log_updated     = Signal(str)
    activity_logged = Signal(str)

    def __init__(self, lia_instance):
        super().__init__()
        self.lia = lia_instance

    def run(self):
        try:
            self.lia.run()
        except Exception as ex:
            self.log_updated.emit(f"[ERROR] {ex}")


class GlassFrame(QFrame):
    """Tarjeta de cristal con sombra suave y borde luxury."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glass_frame")
        self.setStyleSheet(f"""
            QFrame#glass_frame {{
                background: {_C_GLASS_1};
                border: 1px solid {_C_BORDER};
                border-radius: 14px;
            }}
        """)
        sombra = QGraphicsDropShadowEffect(self)
        sombra.setBlurRadius(28)
        sombra.setOffset(0, 6)
        sombra.setColor(QColor(0, 0, 0, 110))
        self.setGraphicsEffect(sombra)


class StatusCard(GlassFrame):
    """Tarjeta principal con marca LIA y estado en vivo."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(28, 26, 28, 26)

        marca_row = QHBoxLayout()
        marca_row.setSpacing(0)
        title = QLabel("LIA")
        title.setObjectName("title_huge")
        marca_row.addWidget(title)
        marca_row.addStretch()
        version = QLabel("v 10.0")
        version.setStyleSheet(
            f"color: {_C_MUTED}; font-size: 10px; "
            f"letter-spacing: 2.4px; background: transparent;"
        )
        marca_row.addWidget(version, alignment=Qt.AlignBottom)
        layout.addLayout(marca_row)

        subtitle = QLabel("ASISTENTE PERSONAL · AT YOUR SERVICE")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        sep = QFrame()
        sep.setObjectName("separator_lux")
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        self.dot_lbl = QLabel()
        self.dot_lbl.setPixmap(_status_dot(_C_SUCCESS, 12))
        self.status_lbl = QLabel("ACTIVA · ESCUCHANDO")
        self.status_lbl.setStyleSheet(
            f"color: {_C_SUCCESS}; font-weight: 600; "
            f"font-size: 11px; letter-spacing: 2px; background: transparent;"
        )
        status_row.addWidget(self.dot_lbl)
        status_row.addWidget(self.status_lbl)
        status_row.addStretch()
        layout.addLayout(status_row)

    def set_status(self, estado: str):
        estados = {
            "activa":    (_C_SUCCESS, "ACTIVA · ESCUCHANDO"),
            "pausada":   (_C_WARN,    "EN PAUSA"),
            "apagada":   (_C_ERROR,   "DESCONECTADA"),
            "iniciando": (_C_INFO,    "INICIANDO…"),
            "silencio":  (_C_MUTED,   "MODO SILENCIOSO"),
        }
        color, texto = estados.get(estado, (_C_MUTED, estado.upper()))
        self.dot_lbl.setPixmap(_status_dot(color, 12))
        self.status_lbl.setText(texto)
        self.status_lbl.setStyleSheet(
            f"color: {color}; font-weight: 600; "
            f"font-size: 11px; letter-spacing: 2px; background: transparent;"
        )


# ═══════════════════════════════════════════════════════════════════
#  TAB ESTADO
# ═══════════════════════════════════════════════════════════════════
class TabEstado(QWidget):

    def __init__(self, parent_window):
        super().__init__()
        self.win = parent_window
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(20, 20, 20, 20)

        self.status_card = StatusCard()
        layout.addWidget(self.status_card)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_toggle = QPushButton("PAUSAR")
        self.btn_toggle.setObjectName("btn_primary")
        self.btn_toggle.setFixedHeight(44)
        self.btn_toggle.clicked.connect(self._toggle_lia)

        btn_reiniciar = QPushButton("REINICIAR")
        btn_reiniciar.setObjectName("btn_ghost")
        btn_reiniciar.setFixedHeight(44)
        btn_reiniciar.clicked.connect(self._reiniciar_lia)

        btn_apagar = QPushButton("APAGAR")
        btn_apagar.setObjectName("btn_danger")
        btn_apagar.setFixedHeight(44)
        btn_apagar.clicked.connect(self._apagar_lia)

        btn_row.addWidget(self.btn_toggle)
        btn_row.addWidget(btn_reiniciar)
        btn_row.addWidget(btn_apagar)
        layout.addLayout(btn_row)

        log_lbl = QLabel("ACTIVIDAD")
        log_lbl.setObjectName("title_section")
        layout.addWidget(log_lbl)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Los mensajes de Lia aparecerán aquí…")
        layout.addWidget(self.log_box)

    def _toggle_lia(self):
        lia = self.win.lia
        if lia is None:
            return
        if lia.is_active:
            lia.is_active = False
            lia.detector.set_active(False)
            self.btn_toggle.setText("REANUDAR")
            self.status_card.set_status("pausada")
        else:
            lia.is_active = True
            lia.detector.set_active(True)
            self.btn_toggle.setText("PAUSAR")
            self.status_card.set_status("activa")

    def _reiniciar_lia(self):
        self.win.reiniciar_lia()

    def _apagar_lia(self):
        self.win.apagar_lia()

    def append_log(self, texto: str):
        hora = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(
            f"<span style='color:{_C_MUTED};'>{hora}</span> "
            f"<span style='color:{_C_TEXT_DIM};'>{texto}</span>"
        )
        sb = self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_status(self, estado: str):
        self.status_card.set_status(estado)
        if estado == "activa":
            self.btn_toggle.setText("PAUSAR")
        elif estado == "pausada":
            self.btn_toggle.setText("REANUDAR")


# ═══════════════════════════════════════════════════════════════════
#  TAB MODOS DE APLAUSO
# ═══════════════════════════════════════════════════════════════════
class DialogEditarModo(QDialog):

    def __init__(self, modo: dict, parent=None):
        super().__init__(parent)
        self.modo = dict(modo)
        self.setWindowTitle("Editar modo")
        self.setMinimumWidth(500)
        self.setStyleSheet(STYLE_GLOBAL)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(28, 28, 28, 28)

        title = QLabel("EDITAR MODO")
        title.setObjectName("title_section")
        layout.addWidget(title)

        def _row(label, widget):
            r = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(140)
            lbl.setStyleSheet(f"color: {_C_TEXT_DIM}; background: transparent;")
            r.addWidget(lbl)
            r.addWidget(widget)
            layout.addLayout(r)

        self.inp_aplausos = QSpinBox()
        self.inp_aplausos.setRange(1, 10)
        self.inp_aplausos.setValue(modo.get("aplausos", 1))
        _row("Aplausos:", self.inp_aplausos)

        self.inp_nombre = QLineEdit(modo.get("nombre", ""))
        self.inp_nombre.setPlaceholderText("Nombre del modo")
        _row("Nombre:", self.inp_nombre)

        self.inp_desc = QLineEdit(modo.get("descripcion", ""))
        self.inp_desc.setPlaceholderText("Descripción breve")
        _row("Descripción:", self.inp_desc)

        self.inp_tipo = QComboBox()
        self.inp_tipo.addItems(["builtin", "apps_custom"])
        idx = self.inp_tipo.findText(modo.get("tipo", "builtin"))
        if idx >= 0:
            self.inp_tipo.setCurrentIndex(idx)
        _row("Tipo:", self.inp_tipo)

        self.inp_accion = QComboBox()
        builtins = ["modo_estudio", "modo_programacion", "modo_juego"]
        self.inp_accion.addItems(builtins)
        idx2 = self.inp_accion.findText(modo.get("accion", "modo_estudio"))
        if idx2 >= 0:
            self.inp_accion.setCurrentIndex(idx2)
        _row("Acción builtin:", self.inp_accion)

        apps_lbl = QLabel("Apps (una por línea):")
        apps_lbl.setStyleSheet(f"color: {_C_TEXT_DIM}; background: transparent;")
        layout.addWidget(apps_lbl)

        self.inp_apps = QTextEdit()
        self.inp_apps.setFixedHeight(110)
        apps_actuales = modo.get("apps_display", [])
        self.inp_apps.setPlainText("\n".join(apps_actuales))
        layout.addWidget(self.inp_apps)

        self.inp_tipo.currentTextChanged.connect(self._on_tipo_changed)
        self._on_tipo_changed(self.inp_tipo.currentText())

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._guardar)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.Save).setObjectName("btn_primary")
        btns.button(QDialogButtonBox.Save).setText("GUARDAR")
        btns.button(QDialogButtonBox.Cancel).setText("CANCELAR")
        btns.button(QDialogButtonBox.Cancel).setObjectName("btn_ghost")
        layout.addWidget(btns)

    def _on_tipo_changed(self, tipo: str):
        self.inp_accion.setEnabled(tipo == "builtin")

    def _guardar(self):
        self.modo["aplausos"]    = self.inp_aplausos.value()
        self.modo["nombre"]      = self.inp_nombre.text().strip()
        self.modo["descripcion"] = self.inp_desc.text().strip()
        self.modo["tipo"]        = self.inp_tipo.currentText()
        self.modo["accion"]      = self.inp_accion.currentText()
        apps_texto = self.inp_apps.toPlainText().strip()
        self.modo["apps_display"] = [a.strip() for a in apps_texto.split("\n") if a.strip()]
        self.accept()


class TabModos(QWidget):

    def __init__(self, parent_window):
        super().__init__()
        self.win = parent_window
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        header_row = QHBoxLayout()
        lbl = QLabel("MODOS DE APLAUSO")
        lbl.setObjectName("title_section")
        header_row.addWidget(lbl)
        header_row.addStretch()

        btn_agregar = QPushButton("+ AGREGAR")
        btn_agregar.setObjectName("btn_success")
        btn_agregar.clicked.connect(self._agregar_modo)
        header_row.addWidget(btn_agregar)
        layout.addLayout(header_row)

        hint = QLabel("Doble clic sobre una fila para editar.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["Aplausos", "Nombre", "Descripción", "Apps"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.doubleClicked.connect(self._editar_seleccionado)
        layout.addWidget(self.tabla)

        btn_row = QHBoxLayout()
        btn_editar = QPushButton("EDITAR")
        btn_editar.setObjectName("btn_ghost")
        btn_editar.clicked.connect(self._editar_seleccionado)
        btn_eliminar = QPushButton("ELIMINAR")
        btn_eliminar.setObjectName("btn_danger")
        btn_eliminar.clicked.connect(self._eliminar_seleccionado)
        btn_row.addWidget(btn_editar)
        btn_row.addWidget(btn_eliminar)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._cargar_tabla()

    def _cargar_tabla(self):
        modos = _leer_modos()
        self.tabla.setRowCount(0)
        for modo in modos:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            self.tabla.setItem(row, 0, QTableWidgetItem(str(modo.get("aplausos", ""))))
            self.tabla.setItem(row, 1, QTableWidgetItem(modo.get("nombre", "")))
            self.tabla.setItem(row, 2, QTableWidgetItem(modo.get("descripcion", "")))
            apps = ", ".join(modo.get("apps_display", []))
            self.tabla.setItem(row, 3, QTableWidgetItem(apps))
            self.tabla.setRowHeight(row, 44)

    def _editar_seleccionado(self):
        rows = self.tabla.selectionModel().selectedRows()
        if not rows: return
        row_idx = rows[0].row()
        modos = _leer_modos()
        if row_idx >= len(modos): return
        dlg = DialogEditarModo(modos[row_idx], self)
        if dlg.exec() == QDialog.Accepted:
            modos[row_idx] = dlg.modo
            _guardar_modos(modos)
            self._cargar_tabla()

    def _agregar_modo(self):
        nuevo = {
            "aplausos": 4, "nombre": "Nuevo Modo", "descripcion": "",
            "tipo": "builtin", "accion": "modo_estudio", "apps_display": []
        }
        dlg = DialogEditarModo(nuevo, self)
        if dlg.exec() == QDialog.Accepted:
            modos = _leer_modos()
            modos.append(dlg.modo)
            _guardar_modos(modos)
            self._cargar_tabla()

    def _eliminar_seleccionado(self):
        rows = self.tabla.selectionModel().selectedRows()
        if not rows: return
        row_idx = rows[0].row()
        modos = _leer_modos()
        if row_idx >= len(modos): return
        resp = QMessageBox.question(
            self, "Confirmar",
            f"¿Eliminar el modo '{modos[row_idx].get('nombre', '')}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp == QMessageBox.Yes:
            modos.pop(row_idx)
            _guardar_modos(modos)
            self._cargar_tabla()


# ═══════════════════════════════════════════════════════════════════
#  TAB RESUMEN — estadísticas del día
# ═══════════════════════════════════════════════════════════════════
class TabResumen(QWidget):

    def __init__(self, parent_window):
        super().__init__()
        self.win = parent_window
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("RESUMEN")
        header.setObjectName("title_section")
        layout.addWidget(header)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        self.card_hoy   = self._stat_card("HOY", "0")
        self.card_total = self._stat_card("ACUMULADO", "0")
        self.card_modos = self._stat_card("MODOS HOY", "0")

        cards_row.addWidget(self.card_hoy)
        cards_row.addWidget(self.card_total)
        cards_row.addWidget(self.card_modos)
        layout.addLayout(cards_row)

        det_lbl = QLabel("DETALLE DEL DÍA")
        det_lbl.setObjectName("title_section")
        layout.addWidget(det_lbl)

        self.detalle = QTextEdit()
        self.detalle.setReadOnly(True)
        self.detalle.setPlaceholderText("Aquí aparecerá el detalle por categorías…")
        layout.addWidget(self.detalle)

        btn_refresh = QPushButton("ACTUALIZAR")
        btn_refresh.setObjectName("btn_primary")
        btn_refresh.setFixedHeight(40)
        btn_refresh.clicked.connect(self.refrescar)
        layout.addWidget(btn_refresh)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refrescar)
        self.timer.start(30_000)
        QTimer.singleShot(800, self.refrescar)

    def _stat_card(self, titulo: str, valor: str) -> GlassFrame:
        card = GlassFrame()
        v = QVBoxLayout(card)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(4)
        t = QLabel(titulo)
        t.setObjectName("title_section")
        valor_lbl = QLabel(valor)
        valor_lbl.setStyleSheet(
            f"color: {_C_ACCENT_HI}; font-size: 28px; "
            f"font-weight: 200; background: transparent;"
        )
        v.addWidget(t)
        v.addWidget(valor_lbl)
        card.valor_lbl = valor_lbl
        return card

    def refrescar(self):
        if not self.win.lia or not hasattr(self.win.lia, "resumen"):
            return
        try:
            stats = self.win.lia.resumen.estadisticas_dict()
            self.card_hoy.valor_lbl.setText(str(stats["total_hoy"]))
            self.card_total.valor_lbl.setText(str(stats["total_global"]))
            modos_hoy = sum(
                v for k, v in stats["categorias"].items()
                if k in ("estudio", "código", "juego")
            )
            self.card_modos.valor_lbl.setText(str(modos_hoy))

            detalle = []
            for cat, n in sorted(stats["categorias"].items(), key=lambda x: -x[1]):
                detalle.append(f"  • {cat.title():<16} {n}")
            self.detalle.setPlainText(
                "\n".join(detalle) if detalle else "Sin actividad registrada hoy."
            )
        except Exception as ex:
            self.detalle.setPlainText(f"No se pudo cargar el resumen: {ex}")


# ═══════════════════════════════════════════════════════════════════
#  TAB MODO ENFOQUE
# ═══════════════════════════════════════════════════════════════════
class TabEnfoque(QWidget):

    def __init__(self, parent_window):
        super().__init__()
        self.win = parent_window
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("MODO ENFOQUE")
        header.setObjectName("title_section")
        layout.addWidget(header)

        self.card = GlassFrame()
        cv = QVBoxLayout(self.card)
        cv.setContentsMargins(28, 28, 28, 28)
        cv.setSpacing(14)

        self.lbl_estado = QLabel("INACTIVO")
        self.lbl_estado.setStyleSheet(
            f"color: {_C_MUTED}; font-size: 11px; "
            f"letter-spacing: 2px; background: transparent;"
        )
        self.lbl_estado.setAlignment(Qt.AlignCenter)
        cv.addWidget(self.lbl_estado)

        self.lbl_tiempo = QLabel("00:00")
        self.lbl_tiempo.setStyleSheet(
            f"color: {_C_ACCENT_HI}; font-size: 56px; "
            f"font-weight: 200; letter-spacing: 6px; background: transparent;"
        )
        self.lbl_tiempo.setAlignment(Qt.AlignCenter)
        cv.addWidget(self.lbl_tiempo)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        cv.addWidget(self.progress)

        layout.addWidget(self.card)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(10)
        lbl_min = QLabel("MINUTOS:")
        lbl_min.setObjectName("muted")
        self.spn_min = QSpinBox()
        self.spn_min.setRange(5, 240)
        self.spn_min.setValue(25)
        self.btn_iniciar = QPushButton("INICIAR ENFOQUE")
        self.btn_iniciar.setObjectName("btn_primary")
        self.btn_iniciar.setFixedHeight(40)
        self.btn_iniciar.clicked.connect(self._iniciar)
        self.btn_detener = QPushButton("DETENER")
        self.btn_detener.setObjectName("btn_danger")
        self.btn_detener.setFixedHeight(40)
        self.btn_detener.clicked.connect(self._detener)

        ctrl_row.addWidget(lbl_min)
        ctrl_row.addWidget(self.spn_min)
        ctrl_row.addWidget(self.btn_iniciar)
        ctrl_row.addWidget(self.btn_detener)
        layout.addLayout(ctrl_row)

        info = QLabel(
            "El modo enfoque bloquea sitios distractores (redes sociales, "
            "streaming) durante el tiempo definido. Requiere permisos "
            "de administrador. Sin ellos, Lia hace recordatorios cada "
            "5 minutos en su lugar."
        )
        info.setObjectName("muted")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)
        self._minutos_total = 25

    def _iniciar(self):
        if not self.win.lia: return
        minutos = self.spn_min.value()
        self._minutos_total = minutos
        self.win.lia.focus.activar(minutos)

    def _detener(self):
        if not self.win.lia: return
        self.win.lia.focus.desactivar()

    def _tick(self):
        if not self.win.lia or not hasattr(self.win.lia, "focus"):
            return
        focus = self.win.lia.focus
        if focus.activo:
            seg = focus.tiempo_restante()
            mins, secs = divmod(seg, 60)
            self.lbl_tiempo.setText(f"{mins:02d}:{secs:02d}")
            self.lbl_estado.setText("EN PROGRESO")
            self.lbl_estado.setStyleSheet(
                f"color: {_C_SUCCESS}; font-size: 11px; "
                f"letter-spacing: 2px; background: transparent;"
            )
            total_seg = self._minutos_total * 60
            transcurrido = total_seg - seg
            pct = int((transcurrido / total_seg) * 100) if total_seg else 0
            self.progress.setValue(min(100, max(0, pct)))
        else:
            self.lbl_tiempo.setText("00:00")
            self.lbl_estado.setText("INACTIVO")
            self.lbl_estado.setStyleSheet(
                f"color: {_C_MUTED}; font-size: 11px; "
                f"letter-spacing: 2px; background: transparent;"
            )
            self.progress.setValue(0)


# ═══════════════════════════════════════════════════════════════════
#  TAB CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════
class TabConfiguracion(QWidget):

    def __init__(self, parent_window):
        super().__init__()
        self.win = parent_window
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(28, 28, 28, 28)

        def _seccion(titulo):
            lbl = QLabel(titulo)
            lbl.setObjectName("title_section")
            layout.addWidget(lbl)
            sep = QFrame()
            sep.setObjectName("separator_lux")
            sep.setFrameShape(QFrame.HLine)
            layout.addWidget(sep)

        def _fila(etiqueta, widget, desc=""):
            col = QVBoxLayout()
            row = QHBoxLayout()
            lbl = QLabel(etiqueta)
            lbl.setFixedWidth(220)
            lbl.setStyleSheet(f"color: {_C_TEXT}; background: transparent;")
            row.addWidget(lbl)
            row.addWidget(widget)
            col.addLayout(row)
            if desc:
                d = QLabel(desc)
                d.setStyleSheet(
                    f"color: {_C_MUTED}; font-size: 11px; "
                    f"background: transparent; margin-left: 224px;"
                )
                col.addWidget(d)
            layout.addLayout(col)

        _seccion("VOZ Y RECONOCIMIENTO")

        self.spn_rate = QSpinBox()
        self.spn_rate.setRange(100, 300)
        self.spn_rate.setValue(180)
        self.spn_rate.setSuffix(" palabras/min")
        _fila("Velocidad de voz:", self.spn_rate, "Velocidad a la que Lia habla")

        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems(["es-MX", "es-ES", "es-AR", "es-CO"])
        _fila("Idioma de reconocimiento:", self.cmb_lang,
              "Variante del español para el reconocedor de voz")

        self.chk_silencio = QCheckBox("Iniciar en modo silencioso")
        layout.addWidget(self.chk_silencio)

        _seccion("APLAUSOS")

        self.spn_threshold = QSpinBox()
        self.spn_threshold.setRange(1, 100)
        self.spn_threshold.setValue(15)
        self.spn_threshold.setSuffix("%")
        _fila("Sensibilidad del micrófono:", self.spn_threshold,
              "Umbral mínimo para detectar un aplauso")

        self.spn_window = QSpinBox()
        self.spn_window.setRange(1, 5)
        self.spn_window.setValue(2)
        self.spn_window.setSuffix(" segundos")
        _fila("Ventana de tiempo:", self.spn_window,
              "Tiempo máximo entre aplausos para contar como secuencia")

        _seccion("PENDIENTES")

        self.inp_pendientes_path = QLineEdit()
        self.inp_pendientes_path.setText(
            os.path.join(os.path.expanduser("~"), "Documents", "Notas", "Pendientes.md")
        )
        row_path = QHBoxLayout()
        lbl_p = QLabel("Ruta de Pendientes.md:")
        lbl_p.setFixedWidth(220)
        lbl_p.setStyleSheet(f"color: {_C_TEXT}; background: transparent;")
        btn_path = QPushButton("…")
        btn_path.setObjectName("btn_ghost")
        btn_path.setFixedWidth(40)
        btn_path.clicked.connect(self._buscar_pendientes)
        row_path.addWidget(lbl_p)
        row_path.addWidget(self.inp_pendientes_path)
        row_path.addWidget(btn_path)
        layout.addLayout(row_path)

        layout.addStretch()

        btn_guardar = QPushButton("GUARDAR CONFIGURACIÓN")
        btn_guardar.setObjectName("btn_primary")
        btn_guardar.setFixedHeight(42)
        btn_guardar.clicked.connect(self._guardar)
        layout.addWidget(btn_guardar)

    def _buscar_pendientes(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Pendientes.md",
            os.path.expanduser("~"), "Markdown (*.md);;All (*.*)"
        )
        if path:
            self.inp_pendientes_path.setText(path)

    def _guardar(self):
        try:
            if self.win.lia and hasattr(self.win.lia, "voz"):
                self.win.lia.voz.set_rate(self.spn_rate.value())
        except Exception:
            pass
        QMessageBox.information(
            self, "Configuración guardada",
            "Los cambios se han aplicado.\n"
            "Algunos ajustes (sensibilidad, idioma) requieren reiniciar Lia."
        )


# ═══════════════════════════════════════════════════════════════════
#  Helpers JSON modos
# ═══════════════════════════════════════════════════════════════════
def _leer_modos() -> list:
    try:
        if os.path.exists(_MODOS_PATH):
            with open(_MODOS_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("modos", [])
    except Exception as ex:
        print(f"Error leyendo modos: {ex}")
    return []


def _guardar_modos(modos: list):
    try:
        with open(_MODOS_PATH, "w", encoding="utf-8") as f:
            json.dump({"modos": modos}, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        print(f"Error guardando modos: {ex}")


# ═══════════════════════════════════════════════════════════════════
#  VENTANA PRINCIPAL
# ═══════════════════════════════════════════════════════════════════
class LiaMainWindow(QMainWindow):
    signal_log    = Signal(str)
    signal_status = Signal(str)

    def __init__(self, lia_instance=None):
        super().__init__()
        self.lia    = lia_instance
        self.worker = None

        self.setWindowTitle("Lia · Asistente Personal")
        self.setWindowIcon(_make_icon(_C_ACCENT))
        self.setMinimumSize(720, 620)
        self.resize(820, 720)
        self.setStyleSheet(STYLE_GLOBAL)

        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(_C_BG_DEEP))
        self.setPalette(pal)

        central = QWidget()
        central.setStyleSheet(f"QWidget {{ background-color: {_C_BG_DEEP}; }}")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Barra de marca superior
        brand_bar = QFrame()
        brand_bar.setFixedHeight(54)
        brand_bar.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {_C_BG_DEEP}, stop:0.5 {_C_GLASS_1}, stop:1 {_C_BG_DEEP});
                border: none;
                border-bottom: 1px solid {_C_BORDER};
            }}
        """)
        brand_layout = QHBoxLayout(brand_bar)
        brand_layout.setContentsMargins(24, 0, 24, 0)
        brand_dot = QLabel()
        brand_dot.setPixmap(_status_dot(_C_ACCENT, 8))
        brand_lbl = QLabel("L  I  A")
        brand_lbl.setStyleSheet(
            f"color: {_C_ACCENT_HI}; font-size: 12px; "
            f"font-weight: 600; letter-spacing: 8px; background: transparent;"
        )
        brand_sub = QLabel("ASISTENTE PERSONAL · v 10.0")
        brand_sub.setStyleSheet(
            f"color: {_C_MUTED}; font-size: 9px; "
            f"letter-spacing: 2.4px; background: transparent;"
        )
        brand_layout.addWidget(brand_dot)
        brand_layout.addSpacing(12)
        brand_layout.addWidget(brand_lbl)
        brand_layout.addStretch()
        brand_layout.addWidget(brand_sub)
        main_layout.addWidget(brand_bar)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        main_layout.addWidget(tabs)

        self.tab_estado    = TabEstado(self)
        self.tab_modos     = TabModos(self)
        self.tab_resumen   = TabResumen(self)
        self.tab_enfoque   = TabEnfoque(self)
        self.tab_config    = TabConfiguracion(self)

        tabs.addTab(self.tab_estado,   "  Estado  ")
        tabs.addTab(self.tab_modos,    "  Aplausos  ")
        tabs.addTab(self.tab_resumen,  "  Resumen  ")
        tabs.addTab(self.tab_enfoque,  "  Enfoque  ")
        tabs.addTab(self.tab_config,   "  Ajustes  ")

        self.signal_log.connect(self.tab_estado.append_log)
        self.signal_status.connect(self.tab_estado.set_status)

        self._setup_tray()

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(_make_icon(_C_ACCENT))
        self.tray.setToolTip("Lia · Asistente Personal")

        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{
                background: {_C_GLASS_2};
                border: 1px solid {_C_BORDER_HI};
                border-radius: 10px;
                padding: 6px;
                color: {_C_TEXT};
                font-family: "Segoe UI";
                font-size: 12px;
            }}
            QMenu::item {{
                padding: 9px 22px;
                border-radius: 6px;
                letter-spacing: 0.6px;
            }}
            QMenu::item:selected {{
                background: {_C_GLASS_3};
                color: {_C_ACCENT_HI};
            }}
            QMenu::separator {{
                height: 1px;
                background: {_C_BORDER};
                margin: 4px 8px;
            }}
        """)

        act_abrir     = QAction("Abrir Lia", self)
        act_pausar    = QAction("Pausar / Reanudar", self)
        act_reiniciar = QAction("Reiniciar", self)
        act_salir     = QAction("Salir", self)

        act_abrir.triggered.connect(self._mostrar_ventana)
        act_pausar.triggered.connect(self._toggle_desde_tray)
        act_reiniciar.triggered.connect(self.reiniciar_lia)
        act_salir.triggered.connect(self.apagar_lia)

        menu.addAction(act_abrir)
        menu.addSeparator()
        menu.addAction(act_pausar)
        menu.addAction(act_reiniciar)
        menu.addSeparator()
        menu.addAction(act_salir)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._mostrar_ventana()

    def _mostrar_ventana(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _toggle_desde_tray(self):
        if self.lia and self.lia.is_active:
            self.lia.is_active = False
            self.lia.detector.set_active(False)
            self.signal_status.emit("pausada")
            self.tray.setIcon(_make_icon(_C_WARN))
        elif self.lia:
            self.lia.is_active = True
            self.lia.detector.set_active(True)
            self.signal_status.emit("activa")
            self.tray.setIcon(_make_icon(_C_ACCENT))

    def reiniciar_lia(self):
        if self.lia:
            self.lia._shutdown_flag.set()
        self.signal_status.emit("iniciando")
        self.signal_log.emit("Reiniciando Lia…")
        QTimer.singleShot(1500, self._relanzar_lia)

    def _relanzar_lia(self):
        try:
            import importlib
            import mod_audio, mod_sistema, mod_memoria, mod_internet
            import mod_dev, mod_personalidad, mod_voz
            import mod_productividad, mod_focus, mod_resumen
            for m in [mod_audio, mod_sistema, mod_memoria, mod_internet,
                      mod_dev, mod_personalidad, mod_voz,
                      mod_productividad, mod_focus, mod_resumen]:
                importlib.reload(m)

            from Lia import LiaAssistant
            self.lia = LiaAssistant()
            self.lia._gui_window = self
            self.worker = LiaWorker(self.lia)
            self.worker.start()
            self.signal_status.emit("activa")
            self.signal_log.emit("Lia reiniciada correctamente.")
        except Exception as ex:
            self.signal_log.emit(f"Error al reiniciar: {ex}")

    def apagar_lia(self):
        if self.lia:
            self.lia._shutdown_flag.set()
        self.signal_status.emit("apagada")
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "Lia sigue activa",
            "Continúa en segundo plano. Clic derecho en el ícono del systray.",
            QSystemTrayIcon.Information, 2000
        )

    def set_lia(self, lia_instance):
        self.lia = lia_instance

    def log(self, texto: str):
        self.signal_log.emit(texto)

    def set_status(self, estado: str):
        self.signal_status.emit(estado)
        colores = {
            "activa": _C_ACCENT, "pausada": _C_WARN,
            "apagada": _C_ERROR, "iniciando": _C_INFO,
        }
        color = colores.get(estado, _C_MUTED)
        self.tray.setIcon(_make_icon(color))
