#!/usr/bin/env python3
import json
import math
import os
import sys as _sys
from datetime import datetime

from PySide6.QtCore import (
    Qt, QThread, Signal, QTimer, QSize, QPointF, QRectF,
    QPropertyAnimation, QEasingCurve,
)
from PySide6.QtGui import (
    QColor, QFont, QIcon, QPainter, QPixmap, QPen, QBrush,
    QAction, QPalette, QLinearGradient, QRadialGradient,
    QPainterPath, QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QComboBox, QSpinBox, QTextEdit, QFrame,
    QDialog, QDialogButtonBox, QSystemTrayIcon, QMenu,
    QMessageBox, QFileDialog, QCheckBox, QScrollArea,
    QGraphicsDropShadowEffect, QProgressBar, QStackedWidget,
    QSizePolicy, QAbstractItemView,
)

# ─── Paths ────────────────────────────────────────────────────────────────────
_SRC_DIR    = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = _sys._MEIPASS if getattr(_sys, "frozen", False) else os.path.dirname(_SRC_DIR)
_MODOS_PATH = os.path.join(_ROOT_DIR, "lia_modos.json")

# ─── Palette ──────────────────────────────────────────────────────────────────
_BG_VOID    = "#050810"
_BG_BASE    = "#080d1a"
_BG_PANEL   = "#0c1422"
_BG_SIDEBAR = "#070b17"
_BG_HOVER   = "#111d2e"
_BG_SEL     = "#152640"

_BORDER     = "#1a2540"
_BORDER_HI  = "#243556"

_TEXT       = "#e2e8f0"
_TEXT_DIM   = "#8099b4"
_MUTED      = "#3d5270"

_CYAN       = "#38bdf8"
_CYAN_HI    = "#7dd3fc"
_CYAN_DEEP  = "#0ea5e9"
_CYAN_DIM   = "#0c3a5e"

_OK         = "#34d399"
_WARN       = "#fbbf24"
_ERR        = "#f87171"
_INFO       = "#38bdf8"

_MONO = '"JetBrains Mono", "Consolas", monospace'
_UI   = '"Segoe UI Variable", "Segoe UI", "Inter", sans-serif'

# ─── Global Stylesheet ────────────────────────────────────────────────────────
STYLE_GLOBAL = f"""
* {{
    font-family: {_UI};
    font-size: 13px;
    outline: none;
}}
QMainWindow, QDialog {{
    background: {_BG_VOID};
    color: {_TEXT};
}}
QWidget {{
    background: transparent;
    color: {_TEXT};
    selection-background-color: {_CYAN_DIM};
    selection-color: {_CYAN_HI};
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {_BORDER_HI};
    border-radius: 2px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {_CYAN_DIM};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 0; }}
QPushButton {{
    background: transparent;
    color: {_TEXT_DIM};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 9px 18px;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 1.2px;
}}
QPushButton:hover {{
    background: {_BG_HOVER};
    border-color: {_BORDER_HI};
    color: {_TEXT};
}}
QPushButton:pressed {{
    background: {_BG_SEL};
    border-color: {_CYAN_DIM};
}}
QPushButton:disabled {{
    color: {_MUTED};
    border-color: {_BORDER};
}}
QPushButton#btn_primary {{
    background: {_CYAN_DEEP};
    color: #000000;
    border: none;
    font-weight: 700;
    letter-spacing: 1.5px;
    padding: 10px 22px;
    border-radius: 7px;
}}
QPushButton#btn_primary:hover {{
    background: {_CYAN};
    color: #000000;
}}
QPushButton#btn_primary:pressed {{
    background: {_CYAN_DIM};
    color: {_CYAN_HI};
}}
QPushButton#btn_primary:disabled {{
    background: {_BORDER};
    color: {_MUTED};
}}
QPushButton#btn_danger {{
    color: {_ERR};
    border-color: rgba(248, 113, 113, 0.25);
}}
QPushButton#btn_danger:hover {{
    background: rgba(248, 113, 113, 0.08);
    border-color: {_ERR};
}}
QPushButton#btn_success {{
    color: {_OK};
    border-color: rgba(52, 211, 153, 0.25);
}}
QPushButton#btn_success:hover {{
    background: rgba(52, 211, 153, 0.08);
    border-color: {_OK};
}}
QPushButton#btn_ghost {{
    color: {_MUTED};
    border-color: {_BORDER};
}}
QPushButton#btn_ghost:hover {{
    color: {_CYAN_HI};
    border-color: {_BORDER_HI};
}}
QLineEdit, QComboBox, QSpinBox {{
    background: {_BG_BASE};
    border: 1px solid {_BORDER};
    border-radius: 7px;
    padding: 8px 12px;
    color: {_TEXT};
    font-size: 12px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {_CYAN};
    background: {_BG_PANEL};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{
    border-color: {_BORDER_HI};
}}
QComboBox::drop-down {{ border: none; padding-right: 10px; width: 16px; }}
QComboBox QAbstractItemView {{
    background: {_BG_PANEL};
    border: 1px solid {_BORDER_HI};
    border-radius: 6px;
    selection-background-color: {_BG_SEL};
    selection-color: {_CYAN_HI};
    padding: 4px;
    outline: 0;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: transparent;
    border: none;
    width: 16px;
}}
QTableWidget {{
    background: {_BG_BASE};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    gridline-color: transparent;
    selection-background-color: {_BG_SEL};
    selection-color: {_CYAN_HI};
    alternate-background-color: {_BG_PANEL};
}}
QTableWidget::item {{
    padding: 10px 12px;
    border-bottom: 1px solid {_BORDER};
    color: {_TEXT_DIM};
}}
QTableWidget::item:selected {{
    background: {_BG_SEL};
    color: {_CYAN_HI};
}}
QHeaderView::section {{
    background: {_BG_PANEL};
    color: {_MUTED};
    border: none;
    border-bottom: 1px solid {_BORDER};
    padding: 10px 12px;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 2px;
}}
QTextEdit {{
    background: {_BG_BASE};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 12px;
    font-family: {_MONO};
    font-size: 11.5px;
    color: {_TEXT_DIM};
}}
QProgressBar {{
    background: {_BG_BASE};
    border: none;
    border-radius: 3px;
    height: 3px;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {_CYAN_DEEP};
    border-radius: 3px;
}}
QCheckBox {{
    color: {_TEXT_DIM};
    font-size: 12px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {_BORDER_HI};
    border-radius: 4px;
    background: {_BG_BASE};
}}
QCheckBox::indicator:checked {{
    background: {_CYAN_DEEP};
    border-color: {_CYAN_DEEP};
}}
QMenu {{
    background: {_BG_PANEL};
    border: 1px solid {_BORDER_HI};
    border-radius: 10px;
    padding: 6px;
    color: {_TEXT};
    font-size: 12px;
}}
QMenu::item {{ padding: 9px 20px; border-radius: 6px; }}
QMenu::item:selected {{ background: {_BG_SEL}; color: {_CYAN_HI}; }}
QMenu::separator {{ height: 1px; background: {_BORDER}; margin: 4px 8px; }}
"""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _icon_dot(color: str = _CYAN, size: int = 32) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QBrush(QColor(color)))
    p.setPen(Qt.NoPen)
    p.drawEllipse(size // 2 - 4, size // 2 - 4, 8, 8)
    p.end()
    return QIcon(pix)


def _status_pix(color: str, size: int = 10) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QBrush(QColor(color)))
    p.setPen(Qt.NoPen)
    p.drawEllipse(1, 1, size - 2, size - 2)
    p.end()
    return pix


def _sep(cyan: bool = False) -> QFrame:
    f = QFrame()
    f.setObjectName("sep_cyan" if cyan else "sep")
    f.setFrameShape(QFrame.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(
        f"background: {_CYAN_DIM}; border: none;"
        if cyan else
        f"background: {_BORDER}; border: none;"
    )
    return f


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        f"color: {_MUTED}; font-size: 9px; font-weight: 600; "
        f"letter-spacing: 2.5px; background: transparent;"
    )
    return lbl


# ─── Worker ───────────────────────────────────────────────────────────────────

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


# ══════════════════════════════════════════════════════════════════════════════
#  VOICE ORB WIDGET
# ══════════════════════════════════════════════════════════════════════════════

class VoiceOrbWidget(QWidget):
    """Animated JARVIS-style voice orb with concentric pulsing rings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 160)
        self.setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WA_NoSystemBackground)

        self._phase     = 0.0
        self._speaking  = False
        self._active    = True
        self._ring_ph   = [0.0, 1.1, 2.2]   # staggered ring phases

        self._timer = QTimer(self)
        self._timer.setInterval(33)           # ~30 fps
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        spd = 0.06 if self._speaking else 0.022
        self._phase = (self._phase + spd) % (2 * math.pi)
        for i in range(3):
            self._ring_ph[i] = (self._ring_ph[i] + spd * (1 + i * 0.4)) % (2 * math.pi)
        self.update()

    def set_speaking(self, speaking: bool):
        self._speaking = speaking

    def set_active(self, active: bool):
        self._active = active

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx = self.width()  / 2.0
        cy = self.height() / 2.0

        if not self._active:
            amp = 0.08 + 0.04 * math.sin(self._phase * 0.5)
            ring_color = _MUTED
            core_inner = QColor(60, 80, 100)
            core_outer = QColor(20, 30, 50)
        elif self._speaking:
            amp = 0.65 + 0.35 * math.sin(self._phase * 3.5)
            ring_color = _CYAN
            core_inner = QColor(125, 211, 252)
            core_outer = QColor(14, 165, 233, 180)
        else:
            amp = 0.28 + 0.14 * math.sin(self._phase)
            ring_color = _CYAN_DEEP
            core_inner = QColor(56, 189, 248)
            core_outer = QColor(12, 58, 94, 200)

        # — Outer rings —
        ring_radii  = [72, 56, 40]
        ring_alphas = [0.12, 0.22, 0.35]

        for i, (base_r, base_a) in enumerate(zip(ring_radii, ring_alphas)):
            ph  = self._ring_ph[i]
            r   = base_r + amp * 10 * math.sin(ph)
            a   = base_a * (0.6 + 0.4 * amp)

            # Glow: three concentric strokes, fading outward
            for g in range(3, 0, -1):
                gr = r + g * 3.5
                ga = int(255 * a * 0.35 / g)
                c  = QColor(ring_color)
                c.setAlpha(min(255, ga))
                painter.setPen(QPen(c, 1.2))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(cx, cy), gr, gr)

            # Main ring
            c = QColor(ring_color)
            c.setAlpha(int(255 * a))
            painter.setPen(QPen(c, 1.5))
            painter.drawEllipse(QPointF(cx, cy), r, r)

        # — Core orb —
        core_r = 24 + amp * 5
        grad = QRadialGradient(QPointF(cx, cy - core_r * 0.25), core_r * 1.1)
        grad.setColorAt(0.0,  core_inner)
        grad.setColorAt(0.55, core_outer)
        grad.setColorAt(1.0,  QColor(5, 8, 16, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(QPointF(cx, cy), core_r * 1.4, core_r * 1.4)

        # Solid core
        solid_grad = QRadialGradient(QPointF(cx, cy), core_r)
        solid_grad.setColorAt(0.0,  core_inner)
        solid_grad.setColorAt(1.0,  QColor(14, 165, 233) if self._active else QColor(40, 55, 80))
        painter.setBrush(QBrush(solid_grad))
        painter.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # — Scan line —
        if self._active:
            scan_offset = int((self._phase / (2 * math.pi)) * core_r * 2) - int(core_r)
            if abs(scan_offset) < core_r:
                half_w = math.sqrt(max(0.0, core_r ** 2 - scan_offset ** 2))
                sc = QColor(_CYAN_HI)
                sc.setAlpha(35)
                painter.setPen(QPen(sc, 1))
                painter.drawLine(
                    QPointF(cx - half_w, cy + scan_offset),
                    QPointF(cx + half_w, cy + scan_offset),
                )


# ══════════════════════════════════════════════════════════════════════════════
#  MIC BUTTON
# ══════════════════════════════════════════════════════════════════════════════

class MicButton(QPushButton):
    """Round mic button with animated glow when listening."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(54, 54)
        self.setCheckable(True)
        self.setChecked(True)
        self.setStyleSheet("background: transparent; border: none;")
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Pausar / Reanudar escucha")

        self._glow_phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._anim)
        self._timer.start()

    def _anim(self):
        if self.isChecked():
            self._glow_phase = (self._glow_phase + 0.18) % (2 * math.pi)
            self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx = self.width()  / 2.0
        cy = self.height() / 2.0
        r  = 22.0
        on = self.isChecked()

        if on:
            intensity = 0.55 + 0.45 * math.sin(self._glow_phase)
            # Glow rings
            for g in range(4, 0, -1):
                gr = r + g * 4.5
                ga = int(90 * intensity / g)
                c = QColor(_CYAN)
                c.setAlpha(ga)
                p.setPen(QPen(c, 1.5))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPointF(cx, cy), gr, gr)

            # Fill
            grad = QRadialGradient(QPointF(cx, cy - 6), r * 1.1)
            grad.setColorAt(0.0, QColor(_CYAN_HI))
            grad.setColorAt(0.5, QColor(_CYAN))
            grad.setColorAt(1.0, QColor(_CYAN_DEEP))
        else:
            grad = QRadialGradient(QPointF(cx, cy - 4), r * 1.1)
            grad.setColorAt(0.0, QColor(_BG_PANEL))
            grad.setColorAt(1.0, QColor(_BG_BASE))

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Border
        bc = QColor(_CYAN if on else _BORDER_HI)
        p.setPen(QPen(bc, 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Mic icon
        icon_color = QColor("#000000" if on else _TEXT_DIM)
        p.setPen(QPen(icon_color, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(QBrush(icon_color))

        # Mic capsule
        cap = QPainterPath()
        cap.addRoundedRect(QRectF(cx - 5, cy - 13, 10, 15), 5, 5)
        p.fillPath(cap, QBrush(icon_color))

        # Stand arc
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(icon_color, 2.0, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(QRectF(cx - 8, cy - 5, 16, 16), 0, -180 * 16)
        # Stand line
        p.drawLine(QPointF(cx, cy + 8), QPointF(cx, cy + 12))
        p.drawLine(QPointF(cx - 5, cy + 12), QPointF(cx + 5, cy + 12))


# ══════════════════════════════════════════════════════════════════════════════
#  CHAT WIDGETS
# ══════════════════════════════════════════════════════════════════════════════

class TypingDots(QWidget):
    """Three animated dots (Lia is thinking)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        self._phase = (self._phase + 0.25) % (2 * math.pi)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Bubble background
        bw, bh = 64, 32
        bx, by = 56, 4
        path = QPainterPath()
        path.addRoundedRect(QRectF(bx, by, bw, bh), 12, 12)
        p.setPen(QPen(QColor(_CYAN_DIM), 1))
        p.setBrush(QBrush(QColor(_BG_PANEL)))
        p.drawPath(path)

        # Dots
        dot_r = 3.5
        gap   = 13.0
        base_x = bx + bw / 2 - gap
        base_y = by + bh / 2

        for i in range(3):
            offset = math.sin(self._phase + i * 1.1) * 4
            alpha  = int(200 + 55 * math.sin(self._phase + i * 1.1))
            c = QColor(_CYAN)
            c.setAlpha(min(255, max(80, alpha)))
            p.setBrush(QBrush(c))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(base_x + i * gap, base_y + offset), dot_r, dot_r)


class ChatMessage(QWidget):
    """A single chat message bubble with slide-in animation."""

    ROLE_LIA    = "lia"
    ROLE_USER   = "user"
    ROLE_SYSTEM = "system"
    ROLE_ERROR  = "error"

    def __init__(self, text: str, role: str = ROLE_LIA, parent=None):
        super().__init__(parent)
        self._role = role
        self._setup_ui(text)
        self._animate_in()

    def _setup_ui(self, text: str):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 3, 16, 3)
        outer.setSpacing(0)

        if self._role == self.ROLE_SYSTEM:
            outer.setAlignment(Qt.AlignCenter)
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"color: {_MUTED}; font-size: 10px; font-family: {_MONO}; "
                f"letter-spacing: 1px; background: transparent; padding: 4px 12px;"
            )
            lbl.setWordWrap(True)
            outer.addWidget(lbl)
            return

        if self._role == self.ROLE_ERROR:
            outer.setAlignment(Qt.AlignCenter)
            frame = self._make_frame(
                text, _BG_PANEL, _ERR,
                f"color: {_ERR}; font-size: 12px;",
                label="ERROR"
            )
            outer.addWidget(frame)
            return

        if self._role == self.ROLE_USER:
            outer.setAlignment(Qt.AlignRight)
            outer.addStretch()
            frame = self._make_frame(
                text, _BG_SEL, _CYAN_DIM,
                f"color: {_TEXT}; font-size: 13px;",
                label=None
            )
            outer.addWidget(frame)
        else:  # ROLE_LIA
            outer.setAlignment(Qt.AlignLeft)
            frame = self._make_frame(
                text, _BG_PANEL, _CYAN_DIM,
                f"color: {_TEXT}; font-size: 13px;",
                label="Lia"
            )
            outer.addWidget(frame)
            outer.addStretch()

    def _make_frame(self, text, bg, border_col, text_style, label):
        frame = QFrame()
        frame.setMaximumWidth(520)
        frame.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)
        frame.setStyleSheet(
            f"QFrame {{ background: {bg}; border: 1px solid {border_col}; "
            f"border-radius: 12px; }}"
        )
        v = QVBoxLayout(frame)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(4)

        if label:
            h = QHBoxLayout()
            h.setSpacing(0)
            name = QLabel(label)
            name.setStyleSheet(
                f"color: {_CYAN}; font-size: 10px; font-weight: 600; "
                f"letter-spacing: 1px; background: transparent;"
            )
            h.addWidget(name)
            h.addStretch()
            ts = QLabel(datetime.now().strftime("%H:%M"))
            ts.setStyleSheet(
                f"color: {_MUTED}; font-size: 10px; background: transparent;"
            )
            h.addWidget(ts)
            v.addLayout(h)

        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(text_style + " background: transparent;")
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(lbl)
        return frame

    def _animate_in(self):
        anim = QPropertyAnimation(self, b"maximumHeight", self)
        anim.setDuration(220)
        anim.setStartValue(0)
        anim.setEndValue(300)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QPropertyAnimation.DeleteWhenStopped)


class ChatScrollArea(QScrollArea):
    """Scrollable chat area that auto-scrolls to bottom."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.NoFrame)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setSpacing(4)
        self._layout.setContentsMargins(0, 12, 0, 12)
        self._layout.addStretch()

        self.setWidget(self._container)

        self._typing = TypingDots()
        self._typing.hide()
        self._layout.addWidget(self._typing)

    def add_message(self, text: str, role: str = ChatMessage.ROLE_LIA):
        self.hide_typing()
        msg = ChatMessage(text, role)
        idx = self._layout.count() - 1   # before stretch at end
        self._layout.insertWidget(idx, msg)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def show_typing(self):
        self._typing.show()
        QTimer.singleShot(50, self._scroll_to_bottom)

    def hide_typing(self):
        self._typing.hide()

    def _scroll_to_bottom(self):
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())


# ══════════════════════════════════════════════════════════════════════════════
#  CHAT PAGE
# ══════════════════════════════════════════════════════════════════════════════

class ChatPage(QWidget):
    """Main chat interface: voice orb + messages + text input."""

    def __init__(self, parent_window):
        super().__init__()
        self.win = parent_window
        self._pending_text_response = False
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # — Orb section —
        orb_section = QWidget()
        orb_section.setObjectName("orb_section")
        orb_section.setFixedHeight(220)
        orb_section.setStyleSheet(
            f"QWidget#orb_section {{"
            f"background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"stop:0 {_BG_BASE},stop:1 {_BG_VOID});"
            f"}}"
        )
        orb_lay = QVBoxLayout(orb_section)
        orb_lay.setAlignment(Qt.AlignCenter)
        orb_lay.setContentsMargins(0, 10, 0, 10)

        self.orb = VoiceOrbWidget()
        orb_lay.addWidget(self.orb, alignment=Qt.AlignCenter)

        self._status_lbl = QLabel("LIA · ESCUCHANDO")
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setStyleSheet(
            f"color: {_CYAN}; font-size: 9px; font-weight: 600; "
            f"letter-spacing: 3px; background: transparent;"
        )
        orb_lay.addWidget(self._status_lbl)

        root.addWidget(orb_section)
        root.addWidget(_sep())

        # — Chat scroll area —
        self.chat = ChatScrollArea()
        root.addWidget(self.chat, stretch=1)

        root.addWidget(_sep())

        # — Input bar —
        input_bar = QWidget()
        input_bar.setObjectName("input_bar")
        input_bar.setFixedHeight(68)
        input_bar.setStyleSheet(
            f"QWidget#input_bar {{"
            f"  background: {_BG_BASE};"
            f"  border-top: 1px solid {_BORDER};"
            f"}}"
        )
        bar_lay = QHBoxLayout(input_bar)
        bar_lay.setContentsMargins(16, 10, 16, 10)
        bar_lay.setSpacing(10)

        self.mic_btn = MicButton()
        self.mic_btn.toggled.connect(self._on_mic_toggle)
        bar_lay.addWidget(self.mic_btn)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Escribe aquí o habla…")
        self.input_field.setFixedHeight(40)
        self.input_field.setStyleSheet(
            f"QLineEdit {{ background: {_BG_PANEL}; border: 1px solid {_BORDER_HI}; "
            f"border-radius: 20px; padding: 8px 18px; color: {_TEXT}; font-size: 13px; }}"
            f"QLineEdit:focus {{ border-color: {_CYAN}; }}"
        )
        self.input_field.returnPressed.connect(self._send_text)
        bar_lay.addWidget(self.input_field, stretch=1)

        send_btn = QPushButton("ENVIAR")
        send_btn.setObjectName("btn_primary")
        send_btn.setFixedHeight(40)
        send_btn.setMinimumWidth(90)
        send_btn.clicked.connect(self._send_text)
        bar_lay.addWidget(send_btn)

        root.addWidget(input_bar)

        # Welcome message
        QTimer.singleShot(600, self._welcome)

    def _welcome(self):
        self.chat.add_message(
            "Sistema en línea. Di 'Lia, …' o escribe un comando aquí.",
            ChatMessage.ROLE_SYSTEM
        )

    def _on_mic_toggle(self, checked: bool):
        lia = self.win.lia
        if lia is None:
            return
        if checked:
            lia.is_active = True
            lia.detector.set_active(True)
            self.win.signal_status.emit("activa")
        else:
            lia.is_active = False
            lia.detector.set_active(False)
            self.win.signal_status.emit("pausada")

    def _send_text(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self.chat.add_message(text, ChatMessage.ROLE_USER)

        lia = self.win.lia
        if lia is None:
            self.chat.add_message("Lia aún se está iniciando…", ChatMessage.ROLE_SYSTEM)
            return

        self._pending_text_response = True
        self.chat.show_typing()

        import threading
        threading.Thread(
            target=lambda: lia._parse_command(text),
            daemon=True
        ).start()

    def append_log(self, text: str):
        if text.startswith("🗣"):
            msg = text[1:].strip()
            self.chat.add_message(msg, ChatMessage.ROLE_LIA)
            self._pending_text_response = False
        elif text.startswith("✓"):
            self.chat.add_message(text[1:].strip(), ChatMessage.ROLE_SYSTEM)
        elif "[ERROR]" in text:
            self.chat.add_message(text, ChatMessage.ROLE_ERROR)
        else:
            self.chat.add_message(text, ChatMessage.ROLE_SYSTEM)

    def set_status(self, estado: str):
        labels = {
            "activa":    ("LIA · ESCUCHANDO",   _CYAN),
            "pausada":   ("LIA · PAUSADA",       _WARN),
            "apagada":   ("LIA · DESCONECTADA",  _ERR),
            "iniciando": ("LIA · INICIANDO…",    _INFO),
            "silencio":  ("LIA · SILENCIOSO",    _MUTED),
        }
        txt, color = labels.get(estado, (estado.upper(), _MUTED))
        self._status_lbl.setText(txt)
        self._status_lbl.setStyleSheet(
            f"color: {color}; font-size: 9px; font-weight: 600; "
            f"letter-spacing: 3px; background: transparent;"
        )
        self.orb.set_active(estado == "activa")
        self.orb.set_speaking(estado == "activa")
        self.mic_btn.setChecked(estado not in ("pausada", "apagada"))


# ══════════════════════════════════════════════════════════════════════════════
#  STATUS PAGE  (formerly TabEstado)
# ══════════════════════════════════════════════════════════════════════════════

class StatusCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QWidget#status_card {{"
            f"background: {_BG_PANEL}; border: 1px solid {_BORDER}; "
            f"border-top: 2px solid {_CYAN}; border-radius: 8px; }}"
        )
        self.setObjectName("status_card")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(12)

        top = QHBoxLayout()
        name = QLabel("LIA")
        name.setStyleSheet(
            f"color: {_CYAN_HI}; font-size: 26px; font-weight: 200; "
            f"letter-spacing: 10px; background: transparent;"
        )
        top.addWidget(name)
        top.addStretch()
        ver = QLabel("v5.0.0")
        ver.setStyleSheet(
            f"color: {_MUTED}; font-size: 9px; font-family: {_MONO}; "
            f"letter-spacing: 2px; background: transparent;"
        )
        top.addWidget(ver, alignment=Qt.AlignBottom)
        lay.addLayout(top)

        lay.addWidget(_sep(cyan=True))

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self._dot = QLabel()
        self._dot.setFixedSize(9, 9)
        self._dot.setPixmap(_status_pix(_OK, 9))
        status_row.addWidget(self._dot, alignment=Qt.AlignVCenter)
        self._status_lbl = QLabel("ACTIVA · ESCUCHANDO")
        self._status_lbl.setStyleSheet(
            f"color: {_OK}; font-size: 10px; font-weight: 600; "
            f"letter-spacing: 2px; background: transparent;"
        )
        status_row.addWidget(self._status_lbl)
        status_row.addStretch()
        self._voice_lbl = QLabel("◉ VOZ")
        self._voice_lbl.setStyleSheet(
            f"color: {_MUTED}; font-size: 9px; font-family: {_MONO}; "
            f"letter-spacing: 2px; background: transparent;"
        )
        status_row.addWidget(self._voice_lbl)
        lay.addLayout(status_row)

        self._pulse_state   = True
        self._current_color = _OK
        self._pulse_timer   = QTimer(self)
        self._pulse_timer.setInterval(900)
        self._pulse_timer.timeout.connect(self._pulse)
        self._pulse_timer.start()

    def _pulse(self):
        if self._current_color != _OK:
            return
        self._pulse_state = not self._pulse_state
        c = _OK if self._pulse_state else _MUTED
        self._dot.setPixmap(_status_pix(c, 9))

    def set_status(self, estado: str):
        MAP = {
            "activa":    (_OK,   "ACTIVA · ESCUCHANDO"),
            "pausada":   (_WARN, "EN PAUSA"),
            "apagada":   (_ERR,  "DESCONECTADA"),
            "iniciando": (_INFO, "INICIANDO…"),
            "silencio":  (_MUTED,"MODO SILENCIOSO"),
        }
        color, texto = MAP.get(estado, (_MUTED, estado.upper()))
        self._current_color = color
        self._dot.setPixmap(_status_pix(color, 9))
        self._status_lbl.setText(texto)
        self._status_lbl.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: 600; "
            f"letter-spacing: 2px; background: transparent;"
        )

    def set_voice_active(self, active: bool):
        c = _CYAN if active else _MUTED
        self._voice_lbl.setStyleSheet(
            f"color: {c}; font-size: 9px; font-family: {_MONO}; "
            f"letter-spacing: 2px; background: transparent;"
        )


class StatusPage(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        self.win = parent_window

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        self.status_card = StatusCard()
        root.addWidget(self.status_card)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_toggle = QPushButton("PAUSAR")
        self.btn_toggle.setObjectName("btn_primary")
        self.btn_toggle.setFixedHeight(40)
        self.btn_toggle.clicked.connect(self._toggle)
        btn_reiniciar = QPushButton("REINICIAR")
        btn_reiniciar.setObjectName("btn_ghost")
        btn_reiniciar.setFixedHeight(40)
        btn_reiniciar.clicked.connect(self.win.reiniciar_lia)
        btn_apagar = QPushButton("APAGAR")
        btn_apagar.setObjectName("btn_danger")
        btn_apagar.setFixedHeight(40)
        btn_apagar.clicked.connect(self.win.apagar_lia)
        btn_row.addWidget(self.btn_toggle, 2)
        btn_row.addWidget(btn_reiniciar, 1)
        btn_row.addWidget(btn_apagar, 1)
        root.addLayout(btn_row)

        log_hdr = QHBoxLayout()
        log_hdr.addWidget(_section_label("Actividad del sistema"))
        log_hdr.addStretch()
        clr = QPushButton("LIMPIAR")
        clr.setObjectName("btn_ghost")
        clr.setFixedHeight(26)
        clr.setStyleSheet(
            f"font-size: 9px; letter-spacing: 1.5px; padding: 2px 10px; "
            f"color: {_MUTED};"
        )
        clr.clicked.connect(lambda: self.log_box.clear())
        log_hdr.addWidget(clr)
        root.addLayout(log_hdr)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("// sistema listo — esperando eventos…")
        self.log_box.setMinimumHeight(160)
        root.addWidget(self.log_box)

    def _toggle(self):
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

    def append_log(self, texto: str):
        hora = datetime.now().strftime("%H:%M:%S")
        if texto.startswith("🗣"):
            color = _CYAN_HI
        elif texto.startswith("✓"):
            color = _OK
        elif "[ERROR]" in texto:
            color = _ERR
        else:
            color = _TEXT_DIM
        self.log_box.append(
            f"<span style='color:{_MUTED}; font-family:{_MONO};'>{hora}</span>"
            f"&nbsp;&nbsp;<span style='color:{color};'>{texto}</span>"
        )
        sb = self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_status(self, estado: str):
        self.status_card.set_status(estado)
        if estado == "activa":
            self.btn_toggle.setText("PAUSAR")
        elif estado in ("pausada", "apagada"):
            self.btn_toggle.setText("REANUDAR")


# ══════════════════════════════════════════════════════════════════════════════
#  MODOS PAGE  (formerly TabModos)
# ══════════════════════════════════════════════════════════════════════════════

class DialogEditarModo(QDialog):
    def __init__(self, modo: dict, parent=None):
        super().__init__(parent)
        self.modo = dict(modo)
        self.setWindowTitle("Editar modo de aplauso")
        self.setMinimumWidth(480)
        self.setStyleSheet(STYLE_GLOBAL)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.addWidget(_section_label("Editar modo"))
        lay.addWidget(_sep())

        def _row(label, widget):
            r = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(150)
            lbl.setStyleSheet(f"color: {_TEXT_DIM}; background: transparent;")
            r.addWidget(lbl)
            r.addWidget(widget)
            lay.addLayout(r)

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
        self.inp_accion.addItems(["modo_estudio", "modo_programacion", "modo_juego"])
        idx2 = self.inp_accion.findText(modo.get("accion", "modo_estudio"))
        if idx2 >= 0:
            self.inp_accion.setCurrentIndex(idx2)
        _row("Acción:", self.inp_accion)

        apps_lbl = QLabel("Apps (una por línea):")
        apps_lbl.setStyleSheet(f"color: {_TEXT_DIM}; background: transparent;")
        lay.addWidget(apps_lbl)

        self.inp_apps = QTextEdit()
        self.inp_apps.setFixedHeight(90)
        self.inp_apps.setPlainText("\n".join(modo.get("apps_display", [])))
        lay.addWidget(self.inp_apps)

        self.inp_tipo.currentTextChanged.connect(
            lambda t: self.inp_accion.setEnabled(t == "builtin")
        )

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._guardar)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.Save).setObjectName("btn_primary")
        btns.button(QDialogButtonBox.Save).setText("GUARDAR")
        btns.button(QDialogButtonBox.Cancel).setText("CANCELAR")
        btns.button(QDialogButtonBox.Cancel).setObjectName("btn_ghost")
        lay.addWidget(btns)

    def _guardar(self):
        self.modo["aplausos"]     = self.inp_aplausos.value()
        self.modo["nombre"]       = self.inp_nombre.text().strip()
        self.modo["descripcion"]  = self.inp_desc.text().strip()
        self.modo["tipo"]         = self.inp_tipo.currentText()
        self.modo["accion"]       = self.inp_accion.currentText()
        apps = self.inp_apps.toPlainText().strip()
        self.modo["apps_display"] = [a.strip() for a in apps.split("\n") if a.strip()]
        self.accept()


class ModosPage(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        self.win = parent_window

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        hdr = QHBoxLayout()
        hdr.addWidget(_section_label("Modos de aplauso"))
        hdr.addStretch()
        btn_add = QPushButton("+ AGREGAR")
        btn_add.setObjectName("btn_success")
        btn_add.setFixedHeight(32)
        btn_add.clicked.connect(self._agregar)
        hdr.addWidget(btn_add)
        lay.addLayout(hdr)

        hint = QLabel("Doble clic sobre una fila para editar")
        hint.setStyleSheet(f"color: {_MUTED}; font-size: 11px; background: transparent;")
        lay.addWidget(hint)

        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["Aplausos", "Nombre", "Descripción", "Apps"])
        h = self.tabla.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.doubleClicked.connect(self._editar)
        lay.addWidget(self.tabla)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_edit = QPushButton("EDITAR")
        btn_edit.setObjectName("btn_ghost")
        btn_edit.setFixedHeight(36)
        btn_edit.clicked.connect(self._editar)
        btn_del = QPushButton("ELIMINAR")
        btn_del.setObjectName("btn_danger")
        btn_del.setFixedHeight(36)
        btn_del.clicked.connect(self._eliminar)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        self._cargar()

    def _cargar(self):
        modos = _leer_modos()
        self.tabla.setRowCount(0)
        for modo in modos:
            r = self.tabla.rowCount()
            self.tabla.insertRow(r)
            item_n = QTableWidgetItem(str(modo.get("aplausos", "")))
            item_n.setTextAlignment(Qt.AlignCenter)
            item_n.setForeground(QColor(_CYAN))
            self.tabla.setItem(r, 0, item_n)
            self.tabla.setItem(r, 1, QTableWidgetItem(modo.get("nombre", "")))
            self.tabla.setItem(r, 2, QTableWidgetItem(modo.get("descripcion", "")))
            self.tabla.setItem(r, 3, QTableWidgetItem(", ".join(modo.get("apps_display", []))))
            self.tabla.setRowHeight(r, 44)

    def _editar(self):
        rows = self.tabla.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        modos = _leer_modos()
        if idx >= len(modos):
            return
        dlg = DialogEditarModo(modos[idx], self)
        if dlg.exec() == QDialog.Accepted:
            modos[idx] = dlg.modo
            _guardar_modos(modos)
            self._cargar()

    def _agregar(self):
        nuevo = {"aplausos": 4, "nombre": "Nuevo Modo", "descripcion": "",
                 "tipo": "builtin", "accion": "modo_estudio", "apps_display": []}
        dlg = DialogEditarModo(nuevo, self)
        if dlg.exec() == QDialog.Accepted:
            modos = _leer_modos()
            modos.append(dlg.modo)
            _guardar_modos(modos)
            self._cargar()

    def _eliminar(self):
        rows = self.tabla.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        modos = _leer_modos()
        if idx >= len(modos):
            return
        resp = QMessageBox.question(
            self, "Confirmar",
            f"¿Eliminar el modo '{modos[idx].get('nombre', '')}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            modos.pop(idx)
            _guardar_modos(modos)
            self._cargar()


# ══════════════════════════════════════════════════════════════════════════════
#  RESUMEN PAGE  (formerly TabResumen)
# ══════════════════════════════════════════════════════════════════════════════

class ResumenPage(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        self.win = parent_window

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        lay.addWidget(_section_label("Resumen de actividad"))

        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.card_hoy   = self._metric("HOY", "0")
        self.card_total = self._metric("TOTAL", "0")
        self.card_modos = self._metric("MODOS HOY", "0")
        for c in (self.card_hoy, self.card_total, self.card_modos):
            cards.addWidget(c)
        lay.addLayout(cards)

        lay.addWidget(_section_label("Desglose"))

        self.detalle = QTextEdit()
        self.detalle.setReadOnly(True)
        self.detalle.setPlaceholderText("// sin actividad registrada…")
        lay.addWidget(self.detalle)

        btn_refresh = QPushButton("ACTUALIZAR")
        btn_refresh.setObjectName("btn_primary")
        btn_refresh.setFixedHeight(40)
        btn_refresh.clicked.connect(self.refrescar)
        lay.addWidget(btn_refresh)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refrescar)
        self._timer.start(30_000)
        QTimer.singleShot(900, self.refrescar)

    def _metric(self, titulo: str, valor: str) -> QWidget:
        card = QWidget()
        card.setStyleSheet(
            f"QWidget {{ background: {_BG_PANEL}; border: 1px solid {_BORDER}; "
            f"border-top: 2px solid {_CYAN}; border-radius: 8px; }}"
        )
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(4)
        t = QLabel(titulo)
        t.setStyleSheet(f"color: {_MUTED}; font-size: 9px; font-weight: 600; "
                        f"letter-spacing: 2.5px; background: transparent;")
        num = QLabel(valor)
        num.setStyleSheet(f"color: {_CYAN_HI}; font-family: {_MONO}; font-size: 32px; "
                          f"font-weight: 200; background: transparent; letter-spacing: 2px;")
        v.addWidget(t)
        v.addWidget(num)
        card.num_lbl = num
        return card

    def refrescar(self):
        if not self.win.lia or not hasattr(self.win.lia, "resumen"):
            return
        try:
            stats = self.win.lia.resumen.estadisticas_dict()
            self.card_hoy.num_lbl.setText(str(stats["total_hoy"]))
            self.card_total.num_lbl.setText(str(stats["total_global"]))
            modos = sum(v for k, v in stats["categorias"].items()
                        if k in ("estudio", "código", "juego"))
            self.card_modos.num_lbl.setText(str(modos))
            lineas = []
            for cat, n in sorted(stats["categorias"].items(), key=lambda x: -x[1]):
                bar = "█" * min(n, 20)
                lineas.append(f"{cat:<18}  {bar}  {n}")
            self.detalle.setPlainText("\n".join(lineas) if lineas else "// sin actividad")
        except Exception as ex:
            self.detalle.setPlainText(f"// error: {ex}")


# ══════════════════════════════════════════════════════════════════════════════
#  ENFOQUE PAGE  (formerly TabEnfoque)
# ══════════════════════════════════════════════════════════════════════════════

class EnfoquePage(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        self.win = parent_window
        self._mins_total = 25

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        lay.addWidget(_section_label("Modo Enfoque"))

        # Timer panel
        panel = QWidget()
        panel.setStyleSheet(
            f"QWidget {{ background: {_BG_PANEL}; border: 1px solid {_BORDER}; "
            f"border-top: 2px solid {_CYAN}; border-radius: 8px; }}"
        )
        tp = QVBoxLayout(panel)
        tp.setContentsMargins(32, 28, 32, 28)
        tp.setSpacing(10)

        self.lbl_estado = QLabel("INACTIVO")
        self.lbl_estado.setAlignment(Qt.AlignCenter)
        self.lbl_estado.setStyleSheet(
            f"color: {_MUTED}; font-size: 9px; font-weight: 600; "
            f"letter-spacing: 2.5px; background: transparent;"
        )
        tp.addWidget(self.lbl_estado)

        self.lbl_tiempo = QLabel("00:00")
        self.lbl_tiempo.setAlignment(Qt.AlignCenter)
        self.lbl_tiempo.setStyleSheet(
            f"color: {_CYAN_HI}; font-family: {_MONO}; font-size: 56px; "
            f"font-weight: 100; letter-spacing: 6px; background: transparent;"
        )
        tp.addWidget(self.lbl_tiempo)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        tp.addWidget(self.progress)

        lay.addWidget(panel)

        ctrl = QHBoxLayout()
        ctrl.setSpacing(10)
        lbl_min = QLabel("Minutos:")
        lbl_min.setStyleSheet(f"color: {_TEXT_DIM}; background: transparent;")
        self.spn_min = QSpinBox()
        self.spn_min.setRange(5, 240)
        self.spn_min.setValue(25)
        self.spn_min.setFixedWidth(90)
        self.btn_iniciar = QPushButton("INICIAR ENFOQUE")
        self.btn_iniciar.setObjectName("btn_primary")
        self.btn_iniciar.setFixedHeight(40)
        self.btn_iniciar.clicked.connect(self._iniciar)
        self.btn_detener = QPushButton("DETENER")
        self.btn_detener.setObjectName("btn_danger")
        self.btn_detener.setFixedHeight(40)
        self.btn_detener.clicked.connect(self._detener)
        ctrl.addWidget(lbl_min)
        ctrl.addWidget(self.spn_min)
        ctrl.addWidget(self.btn_iniciar)
        ctrl.addWidget(self.btn_detener)
        lay.addLayout(ctrl)

        info = QLabel(
            "El modo enfoque bloquea sitios distractores. "
            "Requiere permisos de administrador en Windows."
        )
        info.setStyleSheet(f"color: {_MUTED}; font-size: 11px; background: transparent;")
        info.setWordWrap(True)
        lay.addWidget(info)
        lay.addStretch()

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start()

    def _iniciar(self):
        if not self.win.lia:
            return
        self._mins_total = self.spn_min.value()
        self.win.lia.focus.activar(self._mins_total)

    def _detener(self):
        if not self.win.lia:
            return
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
                f"color: {_CYAN}; font-size: 9px; font-weight: 600; "
                f"letter-spacing: 2.5px; background: transparent;"
            )
            total = self._mins_total * 60
            pct = int(((total - seg) / total) * 100) if total else 0
            self.progress.setValue(min(100, max(0, pct)))
        else:
            self.lbl_tiempo.setText("00:00")
            self.lbl_estado.setText("INACTIVO")
            self.lbl_estado.setStyleSheet(
                f"color: {_MUTED}; font-size: 9px; font-weight: 600; "
                f"letter-spacing: 2.5px; background: transparent;"
            )
            self.progress.setValue(0)


# ══════════════════════════════════════════════════════════════════════════════
#  SETTINGS MODAL  (formerly TabConfiguracion, now floating dialog)
# ══════════════════════════════════════════════════════════════════════════════

class SettingsModal(QDialog):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.win = parent_window
        self.setWindowTitle("Ajustes — Lia")
        self.setMinimumSize(580, 620)
        self.setWindowFlags(
            Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(STYLE_GLOBAL)
        self._drag_pos = None
        self._setup_ui()

    def _setup_ui(self):
        # Glass container
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setObjectName("settings_container")
        container.setStyleSheet(
            f"QWidget#settings_container {{"
            f"  background: {_BG_PANEL};"
            f"  border: 1px solid {_BORDER_HI};"
            f"  border-radius: 16px;"
            f"}}"
        )
        outer.addWidget(container)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        container.setGraphicsEffect(shadow)

        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Title bar
        title_bar = QWidget()
        title_bar.setFixedHeight(52)
        title_bar.setStyleSheet(
            f"background: {_BG_BASE}; border-radius: 16px 16px 0 0; "
            f"border-bottom: 1px solid {_BORDER};"
        )
        tb_lay = QHBoxLayout(title_bar)
        tb_lay.setContentsMargins(22, 0, 16, 0)

        lbl_title = QLabel("AJUSTES")
        lbl_title.setStyleSheet(
            f"color: {_CYAN_HI}; font-size: 11px; font-weight: 600; "
            f"letter-spacing: 3px; background: transparent;"
        )
        tb_lay.addWidget(lbl_title)
        tb_lay.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; color: {_MUTED}; "
            f"font-size: 14px; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: rgba(248,113,113,0.15); color: {_ERR}; }}"
        )
        close_btn.clicked.connect(self.close)
        tb_lay.addWidget(close_btn)
        lay.addWidget(title_bar)

        # Scroll area content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        lay.addWidget(scroll, stretch=1)

        content = QWidget()
        content.setStyleSheet(f"background: transparent;")
        scroll.setWidget(content)

        cl = QVBoxLayout(content)
        cl.setContentsMargins(28, 22, 28, 22)
        cl.setSpacing(20)

        def _section(titulo):
            cl.addWidget(_section_label(titulo))
            cl.addWidget(_sep())

        def _fila(etiqueta, widget, desc=""):
            col = QVBoxLayout()
            row = QHBoxLayout()
            lbl = QLabel(etiqueta)
            lbl.setStyleSheet(f"color: {_TEXT_DIM}; background: transparent;")
            lbl.setFixedWidth(220)
            row.addWidget(lbl)
            row.addWidget(widget)
            col.addLayout(row)
            if desc:
                d = QLabel(desc)
                d.setStyleSheet(f"color: {_MUTED}; font-size: 11px; background: transparent; padding-left: 224px;")
                col.addWidget(d)
            cl.addLayout(col)

        # Voz
        _section("Voz y reconocimiento")
        self.cmb_voice = QComboBox()
        self.cmb_voice.addItems([
            "es-MX-DaliaNeural (mexicana)",
            "es-MX-JorgeNeural (mexicano, masculino)",
            "es-ES-ElviraNeural (española)",
            "es-ES-AlvaroNeural (español, masculino)",
            "es-AR-ElenaNeural (argentina)",
        ])
        _fila("Voz Edge TTS:", self.cmb_voice, "Requiere edge-tts y conexión a internet")

        self.cmb_rate = QComboBox()
        self.cmb_rate.addItems(["-20% (lento)", "-10%", "+0% (normal)", "+10%", "+20% (rápido)"])
        self.cmb_rate.setCurrentIndex(2)
        _fila("Velocidad de voz:", self.cmb_rate)

        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems(["es-MX", "es-ES", "es-AR", "es-CO"])
        _fila("Idioma de reconocimiento:", self.cmb_lang)

        self.chk_silencio = QCheckBox("Iniciar en modo silencioso")
        cl.addWidget(self.chk_silencio)

        # Aplausos
        _section("Detección de aplausos")

        self.spn_threshold = QSpinBox()
        self.spn_threshold.setRange(5, 60)
        self.spn_threshold.setValue(13)
        self.spn_threshold.setSuffix(" %")
        _fila("Sensibilidad (peak mínimo):", self.spn_threshold,
              "Aumenta si se detectan aplausos falsos; baja si no los detecta")

        self.spn_window = QSpinBox()
        self.spn_window.setRange(1, 5)
        self.spn_window.setValue(2)
        self.spn_window.setSuffix(" s")
        _fila("Ventana de secuencia:", self.spn_window)

        # Archivos
        _section("Archivos")

        self.inp_pendientes = QLineEdit()
        self.inp_pendientes.setText(
            os.path.join(os.path.expanduser("~"), "Documents", "Notas", "Pendientes.md")
        )
        row_path = QHBoxLayout()
        lbl_p = QLabel("Ruta Pendientes.md:")
        lbl_p.setStyleSheet(f"color: {_TEXT_DIM}; background: transparent;")
        lbl_p.setFixedWidth(220)
        btn_path = QPushButton("…")
        btn_path.setObjectName("btn_ghost")
        btn_path.setFixedSize(36, 36)
        btn_path.clicked.connect(self._buscar_pendientes)
        row_path.addWidget(lbl_p)
        row_path.addWidget(self.inp_pendientes)
        row_path.addWidget(btn_path)
        cl.addLayout(row_path)

        cl.addStretch()

        # Footer
        footer = QWidget()
        footer.setFixedHeight(62)
        footer.setStyleSheet(
            f"background: {_BG_BASE}; border-radius: 0 0 16px 16px; "
            f"border-top: 1px solid {_BORDER};"
        )
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(22, 12, 22, 12)
        fl.addStretch()
        cancel_btn = QPushButton("CANCELAR")
        cancel_btn.setObjectName("btn_ghost")
        cancel_btn.setFixedHeight(38)
        cancel_btn.clicked.connect(self.close)
        save_btn = QPushButton("GUARDAR AJUSTES")
        save_btn.setObjectName("btn_primary")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._guardar)
        fl.addWidget(cancel_btn)
        fl.addSpacing(8)
        fl.addWidget(save_btn)
        lay.addWidget(footer)

    def _buscar_pendientes(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Pendientes.md",
            os.path.expanduser("~"), "Markdown (*.md);;Todos (*.*)"
        )
        if path:
            self.inp_pendientes.setText(path)

    def _guardar(self):
        try:
            if self.win.lia and hasattr(self.win.lia, "voz"):
                voces = ["dalia", "jorge", "elvira", "alvaro", "elena"]
                v = voces[self.cmb_voice.currentIndex()]
                self.win.lia.voz.set_voice(v)
                tasas = ["-20%", "-10%", "+0%", "+10%", "+20%"]
                self.win.lia.voz.set_rate(tasas[self.cmb_rate.currentIndex()])
        except Exception:
            pass
        QMessageBox.information(
            self, "Configuración guardada",
            "Cambios aplicados.\nSensibilidad e idioma requieren reiniciar Lia.",
        )
        self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _event):
        self._drag_pos = None


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

class SidebarNavButton(QPushButton):
    """Navigation button with selection indicator."""

    def __init__(self, label: str, page_idx: int, parent=None):
        super().__init__(parent)
        self.page_idx   = page_idx
        self._selected  = False
        self.setText(label)
        self.setFixedHeight(42)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    def _update_style(self):
        if self._selected:
            self.setStyleSheet(
                f"QPushButton {{"
                f"  background: {_BG_SEL};"
                f"  color: {_CYAN_HI};"
                f"  border: none;"
                f"  border-left: 2px solid {_CYAN};"
                f"  border-radius: 0;"
                f"  padding: 10px 20px 10px 18px;"
                f"  text-align: left;"
                f"  font-size: 10px;"
                f"  font-weight: 600;"
                f"  letter-spacing: 2px;"
                f"}}"
            )
        else:
            self.setStyleSheet(
                f"QPushButton {{"
                f"  background: transparent;"
                f"  color: {_MUTED};"
                f"  border: none;"
                f"  border-left: 2px solid transparent;"
                f"  border-radius: 0;"
                f"  padding: 10px 20px 10px 18px;"
                f"  text-align: left;"
                f"  font-size: 10px;"
                f"  font-weight: 500;"
                f"  letter-spacing: 2px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background: {_BG_HOVER};"
                f"  color: {_TEXT_DIM};"
                f"  border-left: 2px solid {_BORDER_HI};"
                f"}}"
            )


class SidebarWidget(QWidget):
    """Left navigation sidebar."""

    page_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setObjectName("lia_sidebar")
        self.setStyleSheet(
            f"QWidget#lia_sidebar {{ background: {_BG_SIDEBAR}; "
            f"border-right: 1px solid {_BORDER}; }}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # — Brand —
        brand = QWidget()
        brand.setFixedHeight(56)
        brand.setStyleSheet(
            f"background: {_BG_BASE}; border-bottom: 1px solid {_BORDER};"
        )
        bl = QHBoxLayout(brand)
        bl.setContentsMargins(18, 0, 18, 0)
        bl.setSpacing(10)

        self._brand_dot = QLabel()
        self._brand_dot.setFixedSize(8, 8)
        self._brand_dot.setPixmap(_status_pix(_CYAN, 8))
        bl.addWidget(self._brand_dot, alignment=Qt.AlignVCenter)

        brand_name = QLabel("LIA")
        brand_name.setStyleSheet(
            f"color: {_CYAN_HI}; font-size: 13px; font-weight: 500; "
            f"letter-spacing: 3px; background: transparent;"
        )
        bl.addWidget(brand_name)
        bl.addStretch()

        ver_lbl = QLabel("5.0")
        ver_lbl.setStyleSheet(
            f"color: {_MUTED}; font-size: 9px; font-family: {_MONO}; "
            f"background: transparent;"
        )
        bl.addWidget(ver_lbl, alignment=Qt.AlignBottom)
        root.addWidget(brand)

        # — Nav section —
        nav_label = QWidget()
        nav_label.setFixedHeight(32)
        nl = QHBoxLayout(nav_label)
        nl.setContentsMargins(20, 0, 18, 0)
        lbl = QLabel("NAVEGACIÓN")
        lbl.setStyleSheet(
            f"color: {_MUTED}; font-size: 8px; font-weight: 600; "
            f"letter-spacing: 2px; background: transparent;"
        )
        nl.addWidget(lbl)
        root.addWidget(nav_label)

        NAV = [
            ("◈  CHAT",       0),
            ("◉  ESTADO",     1),
            ("⚡  MODOS",      2),
            ("▤  RESUMEN",    3),
            ("◎  ENFOQUE",    4),
        ]

        self._nav_btns: list[SidebarNavButton] = []
        for label, idx in NAV:
            btn = SidebarNavButton(label, idx)
            btn.clicked.connect(lambda _, i=idx: self._select(i))
            self._nav_btns.append(btn)
            root.addWidget(btn)

        self._nav_btns[0].set_selected(True)

        root.addStretch()
        root.addWidget(_sep())

        # — Status + Settings at bottom —
        bottom = QWidget()
        bottom.setFixedHeight(80)
        bl2 = QVBoxLayout(bottom)
        bl2.setContentsMargins(18, 10, 18, 10)
        bl2.setSpacing(6)

        status_row = QHBoxLayout()
        self._status_dot = QLabel()
        self._status_dot.setFixedSize(7, 7)
        self._status_dot.setPixmap(_status_pix(_OK, 7))
        self._status_txt = QLabel("ACTIVA")
        self._status_txt.setStyleSheet(
            f"color: {_OK}; font-size: 9px; font-weight: 600; "
            f"letter-spacing: 2px; background: transparent;"
        )
        status_row.addWidget(self._status_dot, alignment=Qt.AlignVCenter)
        status_row.addWidget(self._status_txt)
        status_row.addStretch()
        bl2.addLayout(status_row)

        settings_btn = QPushButton("✦  AJUSTES")
        settings_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUTED}; border: none; "
            f"border-radius: 6px; padding: 6px 8px; text-align: left; "
            f"font-size: 10px; letter-spacing: 1.5px; }}"
            f"QPushButton:hover {{ background: {_BG_HOVER}; color: {_TEXT_DIM}; }}"
        )
        settings_btn.clicked.connect(self._open_settings)
        bl2.addWidget(settings_btn)

        root.addWidget(bottom)

        # Brand pulse timer
        self._brand_state = True
        self._brand_timer = QTimer(self)
        self._brand_timer.setInterval(1200)
        self._brand_timer.timeout.connect(self._brand_pulse)
        self._brand_timer.start()

    def _select(self, idx: int):
        self._update_selection(idx)
        self.page_requested.emit(idx)

    def _update_selection(self, idx: int):
        for btn in self._nav_btns:
            btn.set_selected(btn.page_idx == idx)

    def _brand_pulse(self):
        self._brand_state = not self._brand_state
        c = _CYAN if self._brand_state else _CYAN_DIM
        self._brand_dot.setPixmap(_status_pix(c, 8))

    def set_status(self, estado: str):
        MAP = {
            "activa":    (_OK,   "ACTIVA"),
            "pausada":   (_WARN, "PAUSADA"),
            "apagada":   (_ERR,  "OFFLINE"),
            "iniciando": (_INFO, "INICIO…"),
        }
        color, txt = MAP.get(estado, (_MUTED, estado.upper()))
        self._status_dot.setPixmap(_status_pix(color, 7))
        self._status_txt.setText(txt)
        self._status_txt.setStyleSheet(
            f"color: {color}; font-size: 9px; font-weight: 600; "
            f"letter-spacing: 2px; background: transparent;"
        )

    def _open_settings(self):
        # Find parent LiaMainWindow and open settings
        w = self.parent()
        while w and not isinstance(w, LiaMainWindow):
            w = w.parent()
        if w:
            w._open_settings()


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════

class LiaMainWindow(QMainWindow):
    signal_log    = Signal(str)
    signal_status = Signal(str)

    def __init__(self, lia_instance=None):
        super().__init__()
        self.lia    = lia_instance
        self.worker = None

        self.setWindowTitle("Lia")
        self.setWindowIcon(_icon_dot(_CYAN))
        self.setMinimumSize(900, 640)
        self.resize(1060, 720)
        self.setStyleSheet(STYLE_GLOBAL)

        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(_BG_VOID))
        self.setPalette(pal)

        # ── Central widget ────────────────────────────────────────────────────
        central = QWidget()
        central.setObjectName("lia_central")
        central.setStyleSheet(f"QWidget#lia_central {{ background: {_BG_VOID}; }}")
        self.setCentralWidget(central)

        main_lay = QHBoxLayout(central)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self.sidebar = SidebarWidget()
        self.sidebar.page_requested.connect(self._show_page)
        main_lay.addWidget(self.sidebar)

        # ── Content area ──────────────────────────────────────────────────────
        content_area = QWidget()
        content_area.setObjectName("lia_content")
        content_area.setStyleSheet(f"QWidget#lia_content {{ background: {_BG_VOID}; }}")
        ca_lay = QVBoxLayout(content_area)
        ca_lay.setContentsMargins(0, 0, 0, 0)
        ca_lay.setSpacing(0)

        # Top header bar
        header = self._make_header()
        ca_lay.addWidget(header)

        # Pages
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        ca_lay.addWidget(self.stack)

        self.page_chat    = ChatPage(self)
        self.page_status  = StatusPage(self)
        self.page_modos   = ModosPage(self)
        self.page_resumen = ResumenPage(self)
        self.page_enfoque = EnfoquePage(self)

        for page in (self.page_chat, self.page_status,
                     self.page_modos, self.page_resumen, self.page_enfoque):
            self.stack.addWidget(page)

        main_lay.addWidget(content_area, stretch=1)

        # ── Backward compat aliases ───────────────────────────────────────────
        self.tab_estado  = self.page_status
        self.tab_modos   = self.page_modos
        self.tab_resumen = self.page_resumen
        self.tab_enfoque = self.page_enfoque

        # ── Signal wiring ─────────────────────────────────────────────────────
        self.signal_log.connect(self.page_chat.append_log)
        self.signal_log.connect(self.page_status.append_log)
        self.signal_status.connect(self._on_status)

        # ── System tray ───────────────────────────────────────────────────────
        self._setup_tray()

    def _make_header(self) -> QWidget:
        hdr = QWidget()
        hdr.setFixedHeight(44)
        hdr.setStyleSheet(
            f"background: {_BG_BASE}; border-bottom: 1px solid {_BORDER};"
        )
        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(20, 0, 16, 0)
        lay.setSpacing(0)

        self._header_title = QLabel("CHAT")
        self._header_title.setStyleSheet(
            f"color: {_TEXT_DIM}; font-size: 9px; font-weight: 600; "
            f"letter-spacing: 2.5px; background: transparent;"
        )
        lay.addWidget(self._header_title)
        lay.addStretch()

        # Window controls
        for label, slot in (("—", self.showMinimized), ("✕", self.hide)):
            btn = QPushButton(label)
            btn.setFixedSize(30, 30)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; "
                f"color: {_MUTED}; font-size: 13px; border-radius: 6px; }}"
                f"QPushButton:hover {{ background: {_BG_HOVER}; color: {_TEXT}; }}"
            )
            btn.clicked.connect(slot)
            lay.addWidget(btn)

        return hdr

    PAGE_TITLES = ["CHAT", "ESTADO", "MODOS", "RESUMEN", "ENFOQUE"]

    def _show_page(self, idx: int):
        self.stack.setCurrentIndex(idx)
        self._header_title.setText(self.PAGE_TITLES[idx])
        self.sidebar._update_selection(idx)   # no signal re-emit

    def _on_status(self, estado: str):
        self.page_status.set_status(estado)
        self.page_chat.set_status(estado)
        self.sidebar.set_status(estado)
        colores = {
            "activa":    _CYAN,
            "pausada":   _WARN,
            "apagada":   _ERR,
            "iniciando": _INFO,
        }
        self.tray.setIcon(_icon_dot(colores.get(estado, _MUTED)))

    def _open_settings(self):
        dlg = SettingsModal(self)
        dlg.exec()

    # ── Tray ──────────────────────────────────────────────────────────────────

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(_icon_dot(_CYAN))
        self.tray.setToolTip("Lia · Asistente Personal")

        menu = QMenu()
        for label, slot in (
            ("Abrir Lia",         self._mostrar_ventana),
            (None,                None),
            ("Pausar / Reanudar", self._toggle_tray),
            ("Reiniciar",         self.reiniciar_lia),
            (None,                None),
            ("Salir",             self.apagar_lia),
        ):
            if label is None:
                menu.addSeparator()
            else:
                act = QAction(label, self)
                act.triggered.connect(slot)
                menu.addAction(act)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: self._mostrar_ventana()
            if r in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick)
            else None
        )
        self.tray.show()

    def _mostrar_ventana(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _toggle_tray(self):
        if not self.lia:
            return
        if self.lia.is_active:
            self.lia.is_active = False
            self.lia.detector.set_active(False)
            self.signal_status.emit("pausada")
        else:
            self.lia.is_active = True
            self.lia.detector.set_active(True)
            self.signal_status.emit("activa")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def reiniciar_lia(self):
        if self.lia:
            self.lia._shutdown_flag.set()
        self.signal_status.emit("iniciando")
        self.signal_log.emit("// reiniciando…")
        QTimer.singleShot(1500, self._relanzar_lia)

    def _relanzar_lia(self):
        try:
            import importlib
            import mod_audio, mod_sistema, mod_sistema_extra, mod_memoria
            import mod_internet, mod_dev, mod_personalidad, mod_voz
            import mod_productividad, mod_focus, mod_resumen
            for m in [mod_audio, mod_sistema, mod_sistema_extra, mod_memoria,
                      mod_internet, mod_dev, mod_personalidad, mod_voz,
                      mod_productividad, mod_focus, mod_resumen]:
                importlib.reload(m)
            from Lia import LiaAssistant
            self.lia = LiaAssistant()
            self.lia._gui_window = self
            self.worker = LiaWorker(self.lia)
            self.worker.start()
            self.signal_status.emit("activa")
            self.signal_log.emit("// lia reiniciada correctamente")
        except Exception as ex:
            self.signal_log.emit(f"[ERROR] reinicio fallido: {ex}")

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
            "Lia",
            "Sigue activa en segundo plano.",
            QSystemTrayIcon.Information,
            2000,
        )

    def set_lia(self, lia_instance):
        self.lia = lia_instance

    def log(self, texto: str):
        self.signal_log.emit(texto)

    def set_status(self, estado: str):
        self.signal_status.emit(estado)


# ── JSON helpers ──────────────────────────────────────────────────────────────

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
