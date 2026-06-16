# REDESIGN+AGENTS+TOOLS 2026-06-16
"""
hud.py — Full sci-fi command dashboard HUD for J.A.R.V.I.S.
Replaces ui.py as the main UI layer. Imported by main.py.
"""

from __future__ import annotations

import json
import math
import os
import platform
import random
import sys
import threading
import time
import uuid
from pathlib import Path

import psutil
import requests as _requests

from PyQt6.QtCore import (
    QPointF, QRectF, Qt, QTimer, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QPainter, QPainterPath,
    QPen, QRadialGradient, QKeySequence, QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPushButton, QSizePolicy,
    QTextEdit, QVBoxLayout, QWidget,
)

_OS = platform.system()


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR = _base_dir()


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h)
    c.setAlpha(a)
    return c


# ── Color palette ──────────────────────────────────────────────────────────────
BG          = "#050d1a"
DOT_COL     = "#0a1f3a"
PANEL_BG    = "#070f1e"
BORDER_COL  = "#0a2a4a"
PRI         = "#0066ff"
PRI_BRIGHT  = "#00aaff"
PRI_DIM     = "#003388"
TEXT_DIM    = "#4a7a9b"
TEXT_MED    = "#6ab0cc"
TEXT_WHITE  = "#d8f8ff"
GREEN       = "#00ff88"
GREEN_D     = "#00aa55"
ORANGE      = "#ff6600"
AMBER       = "#ffa018"

# Agent colors
AGENT_COLORS = {
    "NEXUS":  "#ffffff",
    "SCOUT":  "#00aaff",
    "ORACLE": "#aa44ff",
    "BROKER": "#00ff88",
    "CHEF":   "#ff8800",
    "FORGE":  "#ff4444",
    "VECTOR": "#ff44aa",
}

# ── Shared button stylesheet ───────────────────────────────────────────────────
BTN_STYLE = f"""
    QPushButton {{
        background: #0a1f3a;
        border: 1px solid {PRI};
        color: {PRI_BRIGHT};
        font-family: 'Courier New', 'Consolas', monospace;
        font-size: 10pt;
        border-radius: 4px;
        padding: 3px 8px;
    }}
    QPushButton:hover {{ background: #0d2a4a; border-color: {PRI_BRIGHT}; }}
    QPushButton:pressed {{ background: {PRI}; color: #ffffff; }}
"""


# ══════════════════════════════════════════════════════════════════════════════
# GPS HELPER (runs in background thread)
# ══════════════════════════════════════════════════════════════════════════════
_gps_text   = "LAT 31.9077°N · LON 35.0076°E · Modi'in"
_gps_lock   = threading.Lock()


def _fetch_gps():
    global _gps_text
    try:
        r = _requests.get("http://ip-api.com/json/", timeout=3)
        data = r.json()
        lat  = data.get("lat", 31.9077)
        lon  = data.get("lon", 35.0076)
        city = data.get("city", "Modi'in")
        with _gps_lock:
            _gps_text = f"LAT {lat:.4f}°N · LON {lon:.4f}°E · {city}"
    except Exception:
        pass


def _gps_refresher():
    _fetch_gps()
    while True:
        time.sleep(1800)  # refresh every 30 min
        _fetch_gps()


threading.Thread(target=_gps_refresher, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# ORB CANVAS — central animated particle orb
# ══════════════════════════════════════════════════════════════════════════════
class OrbCanvas(QWidget):
    ORB_STATES = {
        "idle":       PRI,
        "listening":  PRI_BRIGHT,
        "processing": GREEN,
        "speaking":   ORANGE,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(280, 280)

        self._state      = "idle"
        self._color      = PRI
        self._tick       = 0.0
        self._ring_angle = [0.0, 45.0, 90.0]

        n = 700
        self._particles: list[list[float]] = []
        for _ in range(n):
            angle = random.uniform(0, 2 * math.pi)
            dist  = random.uniform(0, 0.85)
            self._particles.append([
                angle,                      # 0: angle from center
                dist,                       # 1: normalized distance (0-1)
                random.uniform(-0.004, 0.004),  # 2: angular velocity
                random.uniform(-0.003, 0.003),  # 3: radial velocity
                random.uniform(0.5, 1.0),   # 4: brightness
            ])

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(16)

    def set_orb_state(self, state: str):
        self._state = state.lower()
        self._color = self.ORB_STATES.get(self._state, PRI)

    def _step(self):
        self._tick += 0.016
        state = self._state
        for pt in self._particles:
            ang_v = pt[2]
            rad_v = pt[3]

            if state == "listening":
                # tighten toward center
                pt[1] = max(0.0, pt[1] - 0.002)
                pt[1] = pt[1] * 0.997 + 0.0
            elif state == "processing":
                ang_v *= 2.2
                pt[1] = min(0.9, pt[1] + abs(rad_v) * 0.5)
            elif state == "speaking":
                # pulse outward with oscillation
                pulse = 0.003 * math.sin(self._tick * 4 + pt[0])
                pt[1] = max(0.0, min(1.0, pt[1] + pulse))
            else:
                # idle drift
                pt[1] = max(0.05, min(0.9, pt[1] + rad_v * 0.4))
                if pt[1] >= 0.9 or pt[1] <= 0.05:
                    pt[3] = -pt[3]

            pt[0] = (pt[0] + ang_v) % (2 * math.pi)

        # spin rings
        speeds = [0.3, -0.18, 0.12]
        if state == "processing":
            speeds = [s * 3 for s in speeds]
        elif state == "speaking":
            speeds = [s * 1.8 for s in speeds]

        for i, s in enumerate(speeds):
            self._ring_angle[i] = (self._ring_angle[i] + s) % 360

        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        orb_r = min(W, H) * 0.36

        # Background
        p.fillRect(0, 0, W, H, qcol(BG))

        col = QColor(self._color)

        # -- Draw 3 concentric dashed rings with ticks + directional arrows --
        ring_radii = [orb_r * 1.08, orb_r * 1.28, orb_r * 1.52]
        for idx, rr in enumerate(ring_radii):
            ring_a = 140 - idx * 30
            pen = QPen(qcol(self._color, ring_a), 0.8, Qt.PenStyle.DashLine)
            pen.setDashPattern([6, 6])
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), rr, rr)

            # Tick marks (24 ticks per ring)
            n_ticks = 24
            p.setPen(QPen(qcol(self._color, ring_a), 1.0))
            for i in range(n_ticks):
                a = math.radians(i * 360 / n_ticks + self._ring_angle[idx])
                tick_len = 6 if i % 6 == 0 else 3
                x0 = cx + (rr - tick_len) * math.cos(a)
                y0 = cy + (rr - tick_len) * math.sin(a)
                x1 = cx + rr * math.cos(a)
                y1 = cy + rr * math.sin(a)
                p.drawLine(QPointF(x0, y0), QPointF(x1, y1))

            # N/S/E/W arrow markers on outermost ring only
            if idx == 2:
                p.setFont(QFont("Courier New", 7, QFont.Weight.Bold))
                p.setPen(QPen(qcol(self._color, 200), 1))
                offset = rr + 14
                dirs = [("N", 0, -1), ("E", 1, 0), ("S", 0, 1), ("W", -1, 0)]
                for label, dx, dy in dirs:
                    p.drawText(
                        QRectF(cx + dx * offset - 8, cy + dy * offset - 6, 16, 12),
                        Qt.AlignmentFlag.AlignCenter, label
                    )

        # -- Glow bloom around orb --
        glow = QRadialGradient(QPointF(cx, cy), orb_r * 1.4)
        glow.setColorAt(0.0, qcol(self._color, 35))
        glow.setColorAt(0.5, qcol(self._color, 12))
        glow.setColorAt(1.0, qcol(self._color, 0))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), orb_r * 1.4, orb_r * 1.4)

        # -- Draw particles --
        for pt in self._particles:
            dist = pt[1] * orb_r
            x = cx + dist * math.cos(pt[0])
            y = cy + dist * math.sin(pt[0])
            brightness = pt[4]
            particle_a = int(200 * brightness * (0.6 + 0.4 * dist / orb_r))
            radius = 1.0 + brightness * 0.8
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(self._color, min(255, particle_a))))
            p.drawEllipse(QPointF(x, y), radius, radius)

        # -- Bright orb core --
        core_glow = QRadialGradient(QPointF(cx, cy), orb_r * 0.25)
        core_glow.setColorAt(0.0, qcol("#ffffff", 180))
        core_glow.setColorAt(0.4, qcol(self._color, 120))
        core_glow.setColorAt(1.0, qcol(self._color, 0))
        p.setBrush(QBrush(core_glow))
        p.drawEllipse(QPointF(cx, cy), orb_r * 0.25, orb_r * 0.25)

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# STATUS PILL — dynamic pill indicator
# ══════════════════════════════════════════════════════════════════════════════
class StatusPill(QWidget):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._label  = label
        self._active = False
        self.setFixedHeight(22)
        self.setMinimumWidth(90)

    def set_active(self, v: bool):
        if self._active != v:
            self._active = v
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        col = GREEN if self._active else "#3a5a6a"

        # Pill background
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, W, H), 4, 4)
        p.fillPath(path, qcol("#0a1a2a", 220))

        # Left colored border strip
        strip = QPainterPath()
        strip.addRoundedRect(QRectF(0, 0, 3, H), 2, 2)
        p.fillPath(strip, qcol(col, 255))

        # Label (includes the ● prefix)
        p.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        p.setPen(QPen(qcol(col, 255), 1))
        p.drawText(QRectF(8, 0, W - 10, H), Qt.AlignmentFlag.AlignVCenter, self._label)
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# TOP BAR
# ══════════════════════════════════════════════════════════════════════════════
class TopBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(62)
        self.setStyleSheet(f"background: {PANEL_BG}; border-bottom: 1px solid {BORDER_COL};")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 4, 12, 4)
        lay.setSpacing(10)

        # ── Left: title + pills ────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(2)
        left.setContentsMargins(0, 0, 0, 0)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_lbl = QLabel("J.A.R.V.I.S.")
        title_lbl.setFont(QFont("Courier New", 16, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {PRI_BRIGHT}; background: transparent;")
        sub_lbl = QLabel("JUST A RATHER VERY INTELLIGENT SYSTEM")
        sub_lbl.setFont(QFont("Courier New", 10))
        sub_lbl.setStyleSheet(f"color: {TEXT_MED}; background: transparent;")
        title_row.addWidget(title_lbl)
        title_row.addWidget(sub_lbl)
        title_row.addStretch()
        left.addLayout(title_row)

        pills_row = QHBoxLayout()
        pills_row.setSpacing(5)
        self._pill_online    = StatusPill("● ONLINE")
        self._pill_queue     = StatusPill("● QUEUE")
        self._pill_connected = StatusPill("● CONNECTED")
        self._pill_autoidle  = StatusPill("● AUTO-IDLE")
        for pill in (self._pill_online, self._pill_queue, self._pill_connected, self._pill_autoidle):
            pills_row.addWidget(pill)
        pills_row.addStretch()
        left.addLayout(pills_row)

        lay.addLayout(left, stretch=1)

        # ── Right: clock + SID + GPS ───────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(2)
        right.setContentsMargins(0, 0, 0, 0)
        right.setAlignment(Qt.AlignmentFlag.AlignRight)

        self._clock_lbl = QLabel("00:00:00.00")
        self._clock_lbl.setFont(QFont("Courier New", 18, QFont.Weight.Bold))
        self._clock_lbl.setStyleSheet(f"color: {TEXT_WHITE}; background: transparent;")
        self._clock_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        self._sid_lbl = QLabel("SID · --------")
        self._sid_lbl.setFont(QFont("Courier New", 9))
        self._sid_lbl.setStyleSheet(f"color: {TEXT_MED}; background: transparent;")
        self._sid_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        self._gps_lbl = QLabel(_gps_text)
        self._gps_lbl.setFont(QFont("Courier New", 8))
        self._gps_lbl.setStyleSheet(f"color: {TEXT_MED}; background: transparent;")
        self._gps_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        right.addWidget(self._clock_lbl)
        right.addWidget(self._sid_lbl)
        right.addWidget(self._gps_lbl)
        lay.addLayout(right)

        # ── Clock timer ───────────────────────────────────────────────────
        self._clock_tmr = QTimer(self)
        self._clock_tmr.timeout.connect(self._update_clock)
        self._clock_tmr.start(50)

        # ── Pill poll timer ───────────────────────────────────────────────
        self._pill_states: dict[str, bool] = {"ONLINE": False, "AUTO-IDLE": False}
        self._pill_tmr = QTimer(self)
        self._pill_tmr.timeout.connect(self._poll_pills)
        self._pill_tmr.start(2000)

        # ── GPS refresh timer ─────────────────────────────────────────────
        self._gps_tmr = QTimer(self)
        self._gps_tmr.timeout.connect(self._refresh_gps)
        self._gps_tmr.start(10000)

    def _update_clock(self):
        t = time.time()
        s = time.localtime(t)
        ms = int((t % 1) * 100)
        self._clock_lbl.setText(f"{s.tm_hour:02d}:{s.tm_min:02d}:{s.tm_sec:02d}.{ms:02d}")

    def _refresh_gps(self):
        with _gps_lock:
            self._gps_lbl.setText(_gps_text)

    def _poll_pills(self):
        # QUEUE: check agent task queue
        try:
            from agent.task_queue import get_queue
            q = get_queue()
            q_active = hasattr(q, '_queue') and len(getattr(q, '_queue', [])) > 0
        except Exception:
            q_active = False
        self._pill_queue.set_active(q_active)

        # CONNECTED: check if OAuth token file exists
        token_path = BASE_DIR / "config" / "token.json"
        self._pill_connected.set_active(token_path.exists())

        # ONLINE and AUTO-IDLE are set externally via set_pill_state()
        self._pill_online.set_active(self._pill_states.get("ONLINE", False))
        self._pill_autoidle.set_active(self._pill_states.get("AUTO-IDLE", False))

    def set_pill_state(self, name: str, active: bool):
        self._pill_states[name] = active
        self._poll_pills()

    def set_session_id(self, sid: str):
        self._sid_lbl.setText(f"SID · {sid}")


# ══════════════════════════════════════════════════════════════════════════════
# LEFT PANEL — system vitals + telemetry
# ══════════════════════════════════════════════════════════════════════════════
class LeftPanel(QWidget):
    def __init__(self, jarvis_start: float, parent=None):
        super().__init__(parent)
        self._start = jarvis_start
        self.setMinimumWidth(140)
        self.setMaximumWidth(190)
        self.setStyleSheet(
            f"background: {PANEL_BG}; border-right: 1px solid {BORDER_COL};"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)

        def _hdr(txt):
            l = QLabel(txt)
            l.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
            l.setStyleSheet(f"color: {PRI_BRIGHT}; background: transparent; "
                            f"border-bottom: 1px solid {BORDER_COL}; padding-bottom: 3px;")
            return l

        lay.addWidget(_hdr("SYSTEM VITALS"))
        lay.addSpacing(4)

        self._vital_labels: dict[str, QLabel] = {}
        for name in ("CPU", "RAM", "GPU", "DISK", "UPTIME"):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            lbl_name = QLabel(name)
            lbl_name.setFont(QFont("Courier New", 10))
            lbl_name.setStyleSheet(f"color: {TEXT_MED}; background: transparent;")
            lbl_val = QLabel("--")
            lbl_val.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
            lbl_val.setStyleSheet(f"color: {PRI_BRIGHT}; background: transparent;")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(lbl_name)
            row.addWidget(lbl_val)
            lay.addLayout(row)
            self._vital_labels[name] = lbl_val

            # separator
            sep = QWidget()
            sep.setFixedHeight(1)
            sep.setStyleSheet(f"background: {BORDER_COL};")
            lay.addWidget(sep)

        lay.addSpacing(6)
        lay.addWidget(_hdr("TELEMETRY"))

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Courier New", 9))
        self._log.setStyleSheet(f"""
            QTextEdit {{
                background: {BG}; color: #55cc88;
                border: 1px solid {BORDER_COL}; border-radius: 2px;
                padding: 4px;
            }}
        """)
        lay.addWidget(self._log, stretch=1)

        # ── Vitals update timer ───────────────────────────────────────────
        self._prev_net = psutil.net_io_counters()
        self._prev_net_t = time.time()

        self._vitals_tmr = QTimer(self)
        self._vitals_tmr.timeout.connect(self._update_vitals)
        self._vitals_tmr.start(2000)
        self._update_vitals()

        # ── Log signal (thread-safe) ──────────────────────────────────────
        self._log_buf: list[str] = []
        self._log_tmr = QTimer(self)
        self._log_tmr.timeout.connect(self._flush_log)
        self._log_tmr.start(100)

    def _update_vitals(self):
        cpu  = psutil.cpu_percent(interval=None)
        mem  = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent if _OS != "Windows" else psutil.disk_usage("C:\\").percent

        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            gpu = f"{gpus[0].load * 100:.0f}%" if gpus else "N/A"
        except Exception:
            gpu = "N/A"

        elapsed = int(time.time() - self._start)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        uptime = f"{h}h {m}m"

        self._vital_labels["CPU"].setText(f"{cpu:.0f}%")
        self._vital_labels["RAM"].setText(f"{mem:.0f}%")
        self._vital_labels["GPU"].setText(gpu)
        self._vital_labels["DISK"].setText(f"{disk:.0f}%")
        self._vital_labels["UPTIME"].setText(uptime)

        # Color CPU/RAM by load
        for name, val in (("CPU", cpu), ("RAM", mem)):
            if isinstance(val, float) and val > 85:
                c = "#ff3d1a"
            elif isinstance(val, float) and val > 65:
                c = AMBER
            else:
                c = PRI_BRIGHT
            self._vital_labels[name].setStyleSheet(f"color: {c}; background: transparent;")

    def append_log(self, text: str):
        self._log_buf.append(text)

    def _flush_log(self):
        if not self._log_buf:
            return
        for line in self._log_buf:
            self._log.append(line)
        self._log_buf.clear()
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())


# ══════════════════════════════════════════════════════════════════════════════
# RIGHT PANEL — radar + diagnostics
# ══════════════════════════════════════════════════════════════════════════════
class RadarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self._angle = 0.0
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._tick)
        self._tmr.start(50)

    def _tick(self):
        self._angle = (self._angle + 2.0) % 360
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        r = min(W, H) / 2 - 4

        p.fillRect(0, 0, W, H, qcol(BG))

        # Rings
        for i in range(3):
            rr = r * (i + 1) / 3
            p.setPen(QPen(qcol(PRI, 60), 0.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), rr, rr)

        # Cross
        p.setPen(QPen(qcol(PRI, 50), 0.5))
        p.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
        p.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))

        # Sweep
        sweep_rad = math.radians(self._angle)
        sx = cx + r * math.cos(sweep_rad)
        sy = cy + r * math.sin(sweep_rad)
        p.setPen(QPen(qcol(PRI, 180), 1.2))
        p.drawLine(QPointF(cx, cy), QPointF(sx, sy))

        # Sweep glow trail
        for i in range(20):
            a_off = math.radians(self._angle - i * 4)
            fade  = int(80 * (1 - i / 20))
            ex = cx + r * math.cos(a_off)
            ey = cy + r * math.sin(a_off)
            p.setPen(QPen(qcol(PRI, fade), 0.8))
            p.drawLine(QPointF(cx, cy), QPointF(ex, ey))

        # Border circle
        p.setPen(QPen(qcol(PRI, 100), 0.8))
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.end()


class RightPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(160)
        self.setMaximumWidth(220)
        self.setStyleSheet(
            f"background: {PANEL_BG}; border-left: 1px solid {BORDER_COL};"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)

        def _hdr(txt):
            l = QLabel(txt)
            l.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
            l.setStyleSheet(f"color: {PRI}; background: transparent; "
                            f"border-bottom: 1px solid {BORDER_COL}; padding-bottom: 2px;")
            return l

        lay.addWidget(_hdr("RADAR"))
        self._radar = RadarWidget()
        lay.addWidget(self._radar)

        lay.addSpacing(4)
        lay.addWidget(_hdr("STATUS"))

        # Compact pill dots mirroring top bar
        self._dot_pills: dict[str, QLabel] = {}
        dot_names = [("ONLINE", GREEN), ("QUEUE", PRI_BRIGHT), ("CONNECTED", "#aa44ff"), ("AUTO-IDLE", AMBER)]
        for name, col in dot_names:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            dot = QLabel("●")
            dot.setFont(QFont("Courier New", 11))
            dot.setStyleSheet(f"color: #2a3a4a; background: transparent;")
            lbl = QLabel(name)
            lbl.setFont(QFont("Courier New", 9))
            lbl.setStyleSheet(f"color: {TEXT_MED}; background: transparent;")
            row.addWidget(dot)
            row.addWidget(lbl)
            row.addStretch()
            lay.addLayout(row)
            self._dot_pills[name] = dot

        lay.addSpacing(4)
        lay.addWidget(_hdr("DIAGNOSTICS"))

        self._diag = QTextEdit()
        self._diag.setReadOnly(True)
        self._diag.setFont(QFont("Courier New", 9))
        self._diag.setStyleSheet(f"""
            QTextEdit {{
                background: {BG}; color: #55cc88;
                border: 1px solid {BORDER_COL}; border-radius: 2px;
                padding: 4px;
            }}
        """)
        lay.addWidget(self._diag, stretch=1)

        self._diag_buf: list[str] = []
        self._diag_tmr = QTimer(self)
        self._diag_tmr.timeout.connect(self._flush_diag)
        self._diag_tmr.start(100)

    def set_dot(self, name: str, active: bool):
        dot = self._dot_pills.get(name)
        if dot:
            col_map = {"ONLINE": GREEN, "QUEUE": PRI_BRIGHT, "CONNECTED": "#aa44ff", "AUTO-IDLE": AMBER}
            c = col_map.get(name, PRI_BRIGHT) if active else "#2a3a4a"
            dot.setStyleSheet(f"color: {c}; background: transparent;")

    def append_diag(self, text: str):
        self._diag_buf.append(text)

    def _flush_diag(self):
        if not self._diag_buf:
            return
        for line in self._diag_buf:
            self._diag.append(line)
        self._diag_buf.clear()
        sb = self._diag.verticalScrollBar()
        sb.setValue(sb.maximum())


# ══════════════════════════════════════════════════════════════════════════════
# AGENT CARD — bottom-center active agent display
# ══════════════════════════════════════════════════════════════════════════════
class AgentCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(70)
        self._agent_name   = "NEXUS"
        self._agent_status = "ORCHESTRATING · ALL SYSTEMS NOMINAL"
        self._agent_color  = AGENT_COLORS.get("NEXUS", TEXT_WHITE)
        self._speaking     = False
        self._pulse        = 0.0

        self._border_col = self._agent_color

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(10)

        # Left: label + name + status
        left_lay = QVBoxLayout()
        left_lay.setSpacing(2)
        left_lay.setContentsMargins(0, 0, 0, 0)

        self._micro_lbl = QLabel("ACTIVE AGENT")
        self._micro_lbl.setFont(QFont("Courier New", 9))
        self._micro_lbl.setStyleSheet(f"color: {TEXT_MED}; background: transparent;")

        self._name_lbl = QLabel("NEXUS")
        self._name_lbl.setFont(QFont("Courier New", 20, QFont.Weight.Bold))
        self._name_lbl.setStyleSheet(f"color: {self._agent_color}; background: transparent;")

        self._status_lbl = QLabel(self._agent_status)
        self._status_lbl.setFont(QFont("Courier New", 10))
        self._status_lbl.setStyleSheet(f"color: {TEXT_MED}; background: transparent;")

        left_lay.addWidget(self._micro_lbl)
        left_lay.addWidget(self._name_lbl)
        left_lay.addWidget(self._status_lbl)
        lay.addLayout(left_lay, stretch=1)

        # Right: ON AIR indicator
        right_lay = QVBoxLayout()
        right_lay.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._onair_lbl = QLabel("● ON · AIR")
        self._onair_lbl.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._onair_lbl.setStyleSheet(f"color: #2a3a4a; background: transparent;")
        right_lay.addWidget(self._onair_lbl)
        lay.addLayout(right_lay)

        # Pulse timer for ON AIR
        self._pulse_tmr = QTimer(self)
        self._pulse_tmr.timeout.connect(self._pulse_step)
        self._pulse_tmr.start(80)

    def _pulse_step(self):
        if self._speaking:
            self._pulse = (self._pulse + 0.15) % (2 * math.pi)
            a = int(150 + 105 * math.sin(self._pulse))
            col = ORANGE
            self._onair_lbl.setStyleSheet(f"color: rgba({_hex_to_rgba(col, a)}); background: transparent;")
        else:
            self._onair_lbl.setStyleSheet(f"color: #2a3a4a; background: transparent;")

    def set_active_agent(self, name: str, status: str):
        self._agent_name   = name.upper()
        self._agent_status = status
        self._agent_color  = AGENT_COLORS.get(self._agent_name, TEXT_WHITE)
        self._border_col   = self._agent_color
        self._name_lbl.setText(self._agent_name)
        self._name_lbl.setStyleSheet(f"color: {self._agent_color}; background: transparent;")
        self._status_lbl.setText(status)
        self.update()

    def update_agent_status(self, status: str):
        self._agent_status = status
        self._status_lbl.setText(status)

    def set_speaking(self, v: bool):
        self._speaking = v

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, W, H), 8, 8)
        p.fillPath(path, qcol("#0a1f3a", 230))
        pen = QPen(qcol(self._border_col, 180), 1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()


def _hex_to_rgba(hex_col: str, alpha: int) -> str:
    c = QColor(hex_col)
    return f"{c.red()}, {c.green()}, {c.blue()}, {alpha}"


# ══════════════════════════════════════════════════════════════════════════════
# CROSSHAIR — bottom-left targeting reticle
# ══════════════════════════════════════════════════════════════════════════════
class CrosshairWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 80)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(0, 0, 80, 80, qcol(BG))

        cx, cy = 40.0, 40.0
        r = 14.0
        gap = 6.0
        arm = 22.0
        bk = 8.0  # bracket size

        p.setPen(QPen(qcol(PRI, 180), 0.8))

        # Center circle
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Cross arms (with gap)
        p.drawLine(QPointF(cx - r - gap, cy), QPointF(cx - r - gap - arm, cy))
        p.drawLine(QPointF(cx + r + gap, cy), QPointF(cx + r + gap + arm, cy))
        p.drawLine(QPointF(cx, cy - r - gap), QPointF(cx, cy - r - gap - arm))
        p.drawLine(QPointF(cx, cy + r + gap), QPointF(cx, cy + r + gap + arm))

        # Corner brackets (TL, TR, BL, BR)
        corners = [(4, 4), (76, 4), (4, 76), (76, 76)]
        dirs    = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
        for (ox, oy), (dx, dy) in zip(corners, dirs):
            p.drawLine(QPointF(ox, oy), QPointF(ox + dx * bk, oy))
            p.drawLine(QPointF(ox, oy), QPointF(ox, oy + dy * bk))

        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# NETWORK WIDGET — bottom-right upload/download
# ══════════════════════════════════════════════════════════════════════════════
class NetworkWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(140)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        hdr = QLabel("NETWORK")
        hdr.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {PRI_BRIGHT}; background: transparent; "
                          f"border-bottom: 1px solid {BORDER_COL}; padding-bottom: 2px;")
        lay.addWidget(hdr)

        self._up_lbl = QLabel("UP · 0.0 MB/s")
        self._dn_lbl = QLabel("DN · 0.0 MB/s")
        for l in (self._up_lbl, self._dn_lbl):
            l.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
            l.setStyleSheet(f"color: {PRI_BRIGHT}; background: transparent;")
            lay.addWidget(l)

        self._prev = psutil.net_io_counters()
        self._prev_t = time.time()

        self._net_tmr = QTimer(self)
        self._net_tmr.timeout.connect(self._update_net)
        self._net_tmr.start(1000)

    def _update_net(self):
        curr = psutil.net_io_counters()
        now  = time.time()
        dt   = max(now - self._prev_t, 0.001)
        upload   = (curr.bytes_sent - self._prev.bytes_sent) / 1024 / 1024 / dt
        download = (curr.bytes_recv - self._prev.bytes_recv) / 1024 / 1024 / dt
        self._prev   = curr
        self._prev_t = now
        self._up_lbl.setText(f"UP · {upload:.1f} MB/s")
        self._dn_lbl.setText(f"DN · {download:.1f} MB/s")


# ══════════════════════════════════════════════════════════════════════════════
# DOT GRID BACKGROUND WIDGET
# ══════════════════════════════════════════════════════════════════════════════
class DotGrid(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

    def paintEvent(self, _):
        p = QPainter(self)
        spacing = 30
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(qcol(DOT_COL, 130)))
        W, H = self.width(), self.height()
        for x in range(0, W, spacing):
            for y in range(0, H, spacing):
                p.drawEllipse(QPointF(x, y), 1.0, 1.0)
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class HudWindow(QMainWindow):
    _log_sig      = pyqtSignal(str)
    _state_sig    = pyqtSignal(str)
    _reconnect_sig = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("J.A.R.V.I.S. — MARK XXXIX-OR")
        self.setMinimumSize(900, 600)
        self.setStyleSheet(f"QMainWindow {{ background: {BG}; }}")

        self._muted       = False
        self._start_time  = time.time()
        self._ready       = self._check_config()
        self.on_text_command = None
        self.on_reconnect    = None

        # Central widget + grid layout
        central = QWidget()
        central.setStyleSheet(f"background: {BG};")
        self.setCentralWidget(central)

        grid = QGridLayout(central)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        # Row 0: top bar (spans all cols)
        self.top_bar = TopBar()
        grid.addWidget(self.top_bar, 0, 0, 1, 3)

        # Row 1: left panel | orb | right panel
        self.left_panel = LeftPanel(self._start_time)
        grid.addWidget(self.left_panel, 1, 0)

        self.orb = OrbCanvas()
        grid.addWidget(self.orb, 1, 1)

        self.right_panel = RightPanel()
        grid.addWidget(self.right_panel, 1, 2)

        # Row 2: crosshair | agent card | network
        self.crosshair = CrosshairWidget()
        grid.addWidget(self.crosshair, 2, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)

        self.agent_card = AgentCard()
        grid.addWidget(self.agent_card, 2, 1)

        self.net_widget = NetworkWidget()
        grid.addWidget(self.net_widget, 2, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        # Row 3: controls strip
        ctrl = self._build_controls()
        grid.addWidget(ctrl, 3, 0, 1, 3)

        grid.setRowStretch(1, 1)
        grid.setColumnStretch(1, 1)

        # Dot grid overlay (positioned after layout)
        self._dot_grid = DotGrid(central)
        self._dot_grid.setGeometry(0, 0, 9999, 9999)
        self._dot_grid.lower()

        # Signals
        self._log_sig.connect(self._on_log)
        self._state_sig.connect(self._apply_state)
        self._reconnect_sig.connect(self._on_reconnect_clicked)

        # Setup overlay if needed
        if not self._ready:
            QTimer.singleShot(200, self._show_setup)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_dot_grid"):
            self._dot_grid.setGeometry(0, 0, self.width(), self.height())

    def _check_config(self) -> bool:
        path = BASE_DIR / "config" / "api_keys.json"
        if not path.exists():
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return bool(data.get("gemini_api_key", "").strip() or data.get("api_key", "").strip())
        except Exception:
            return False

    def _build_controls(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(34)
        w.setStyleSheet(f"background: {PANEL_BG}; border-top: 1px solid {BORDER_COL};")

        lay = QHBoxLayout(w)
        lay.setContentsMargins(10, 4, 10, 4)
        lay.setSpacing(8)

        # Command input
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a command or question…")
        self._input.setFont(QFont("Courier New", 11))
        self._input.setFixedHeight(24)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {BG}; color: {TEXT_WHITE};
                border: 1px solid {BORDER_COL}; border-radius: 4px; padding: 2px 6px;
            }}
            QLineEdit:focus {{ border-color: {PRI}; }}
        """)
        self._input.returnPressed.connect(self._send)

        send_btn = QPushButton("▸ SEND")
        send_btn.setFixedHeight(24)
        send_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        send_btn.setStyleSheet(BTN_STYLE)
        send_btn.clicked.connect(self._send)

        self._mute_btn = QPushButton("🎙 MIC ACTIVE")
        self._mute_btn.setFixedHeight(24)
        self._mute_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        self._mute_btn.setStyleSheet(BTN_STYLE)
        self._mute_btn.clicked.connect(self._toggle_mute)

        reconnect_btn = QPushButton("↺ RECONNECT")
        reconnect_btn.setFixedHeight(24)
        reconnect_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        reconnect_btn.setStyleSheet(BTN_STYLE)
        reconnect_btn.clicked.connect(self._on_reconnect_clicked)

        fs_btn = QPushButton("⛶ FULLSCREEN")
        fs_btn.setFixedHeight(24)
        fs_btn.setFont(QFont("Courier New", 8, QFont.Weight.Bold))
        fs_btn.setStyleSheet(BTN_STYLE)
        fs_btn.clicked.connect(self._toggle_fullscreen)

        lay.addWidget(self._input, stretch=1)
        lay.addWidget(send_btn)
        lay.addWidget(self._mute_btn)
        lay.addWidget(reconnect_btn)
        lay.addWidget(fs_btn)

        # Keyboard shortcuts
        QShortcut(QKeySequence("F4"),  self).activated.connect(self._toggle_mute)
        QShortcut(QKeySequence("F11"), self).activated.connect(self._toggle_fullscreen)

        return w

    def _send(self):
        txt = self._input.text().strip()
        if txt and self.on_text_command:
            self._input.clear()
            self.on_text_command(txt)

    def _toggle_mute(self):
        self._muted = not self._muted
        if self._muted:
            self._mute_btn.setText("🔇 MIC MUTED")
            self._apply_state("MUTED")
        else:
            self._mute_btn.setText("🎙 MIC ACTIVE")
            self._apply_state("LISTENING")

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _on_reconnect_clicked(self):
        if self.on_reconnect:
            self.on_reconnect()

    def _on_log(self, text: str):
        self.left_panel.append_log(text)
        self.right_panel.append_diag(text)

    def _apply_state(self, state: str):
        state_map = {
            "LISTENING":  "listening",
            "SPEAKING":   "speaking",
            "THINKING":   "processing",
            "MUTED":      "idle",
            "INITIALISING": "idle",
        }
        orb_state = state_map.get(state.upper(), "idle")
        self.orb.set_orb_state(orb_state)

        # Update top bar pills
        self.top_bar.set_pill_state("ONLINE", state.upper() not in ("MUTED", "INITIALISING"))
        self.top_bar.set_pill_state("AUTO-IDLE", state.upper() == "LISTENING")
        self.right_panel.set_dot("ONLINE", state.upper() not in ("MUTED", "INITIALISING"))

    def _show_setup(self):
        try:
            from ui import SetupOverlay
            ov = SetupOverlay(self.centralWidget())
            ov.done.connect(self._on_setup_done)
            cw = self.centralWidget()
            ow, oh = 460, 430
            ov.setGeometry(
                (cw.width() - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )
            ov.show()
            self._overlay = ov
        except Exception as e:
            print(f"[HUD] Setup overlay error: {e}")
            self._ready = True

    def _on_setup_done(self, key: str, or_key: str, os_name: str):
        conf_dir = BASE_DIR / "config"
        conf_dir.mkdir(exist_ok=True)
        data = {}
        p = conf_dir / "api_keys.json"
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        if key:
            data["gemini_api_key"] = key
        if or_key:
            data["openrouter_api_key"] = or_key
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        if hasattr(self, "_overlay") and self._overlay:
            self._overlay.hide()
        self._ready = True


# ══════════════════════════════════════════════════════════════════════════════
# JARVIS UI — thin facade matching main.py's expected interface
# ══════════════════════════════════════════════════════════════════════════════
class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app
    def mainloop(self):
        self._app.exec()
    def protocol(self, *_):
        pass


class JarvisUI:
    def __init__(self, face_path: str, size=None):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._win = HudWindow()
        self._win.show()
        self.root = _RootShim(self._app)

    # ── Existing interface (unchanged) ──────────────────────────────────────
    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return None  # file upload not in new HUD; preserved for API compat

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    @property
    def on_reconnect(self):
        return self._win.on_reconnect

    @on_reconnect.setter
    def on_reconnect(self, cb):
        self._win.on_reconnect = cb

    def show_action(self, name: str):
        self._win.agent_card.update_agent_status(f"EXECUTING · {name.upper().replace('_', ' ')}")

    def set_state(self, state: str):
        self._win._state_sig.emit(state)

    def write_log(self, text: str):
        self._win._log_sig.emit(text)

    def wait_for_api_key(self):
        while not self._win._ready:
            time.sleep(0.1)

    def start_speaking(self):
        self.set_state("SPEAKING")
        self._win.agent_card.set_speaking(True)

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")
        self._win.agent_card.set_speaking(False)

    # ── New interface for agent system ──────────────────────────────────────
    def set_active_agent(self, name: str, status: str):
        self._win.agent_card.set_active_agent(name, status)

    def update_agent_status(self, status: str):
        self._win.agent_card.update_agent_status(status)

    def set_orb_state(self, state: str):
        self._win.orb.set_orb_state(state)

    def set_session_id(self, sid: str):
        self._win.top_bar.set_session_id(sid)

    def set_pill_state(self, name: str, active: bool):
        self._win.top_bar.set_pill_state(name, active)
        self._win.right_panel.set_dot(name, active)
