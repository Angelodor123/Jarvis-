from __future__ import annotations

import json
import math
import os
import platform
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

from PyQt6.QtCore import (
    QEasingCurve, QMimeData, QObject, QPointF, QRectF, QSize, Qt,
    QTimer, QUrl, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QDragEnterEvent, QDropEvent, QFont, QFontDatabase,
    QKeySequence, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QRadialGradient, QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QTextEdit,
    QVBoxLayout, QWidget, QProgressBar,
)

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

_DEFAULT_W, _DEFAULT_H = 980, 700
_MIN_W,     _MIN_H     = 820, 580
_LEFT_W  = 148
_RIGHT_W = 340

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


class C:
    BG        = "#00060a"
    PANEL     = "#010d14"
    PANEL2    = "#010f18"
    BORDER    = "#0d3347"
    BORDER_B  = "#1a5c7a"
    BORDER_A  = "#0f4060"
    PRI       = "#00d4ff"
    PRI_DIM   = "#007a99"
    PRI_GHO   = "#001f2e"
    ACC       = "#ff6b00"
    ACC2      = "#ffcc00"
    GREEN     = "#00ff88"
    GREEN_D   = "#00aa55"
    RED       = "#ff3355"
    MUTED_C   = "#ff3366"
    TEXT      = "#8ffcff"
    TEXT_DIM  = "#3a8a9a"
    TEXT_MED  = "#5ab8cc"
    WHITE     = "#d8f8ff"
    DARK      = "#000d14"
    BAR_BG    = "#011520"


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h); c.setAlpha(a); return c

class _SysMetrics:
    def __init__(self):
        self.cpu  = 0.0
        self.mem  = 0.0
        self.net  = 0.0   
        self.gpu  = -1.0  
        self.tmp  = -1.0  
        self._lock = threading.Lock()
        self._last_net = psutil.net_io_counters()
        self._last_net_t = time.time()
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while self._running:
            try:
                self._update()
            except Exception:
                pass
            time.sleep(1.5)

    def _update(self):
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent

        nc  = psutil.net_io_counters()
        now = time.time()
        dt  = now - self._last_net_t
        if dt > 0:
            sent = (nc.bytes_sent - self._last_net.bytes_sent) / dt
            recv = (nc.bytes_recv - self._last_net.bytes_recv) / dt
            net  = (sent + recv) / (1024 * 1024)
        else:
            net = 0.0
        self._last_net   = nc
        self._last_net_t = now

        gpu = self._get_gpu()

        tmp = self._get_temp()

        with self._lock:
            self.cpu = cpu
            self.mem = mem
            self.net = net
            self.gpu = gpu
            self.tmp = tmp

    def _get_gpu(self) -> float:
        # NVIDIA
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2
            )
            if r.returncode == 0:
                vals = [float(v.strip()) for v in r.stdout.strip().split("\n") if v.strip()]
                if vals:
                    return sum(vals) / len(vals)
        except Exception:
            pass

        # AMD (Linux)
        if _OS == "Linux":
            try:
                r = subprocess.run(
                    ["rocm-smi", "--showuse", "--csv"],
                    capture_output=True, text=True, timeout=2
                )
                if r.returncode == 0:
                    for line in r.stdout.strip().split("\n"):
                        parts = line.split(",")
                        if len(parts) >= 2:
                            try:
                                return float(parts[1].strip().replace("%", ""))
                            except ValueError:
                                pass
            except Exception:
                pass

            # Intel GPU (Linux)
            try:
                r = subprocess.run(
                    ["intel_gpu_top", "-J", "-s", "500"],
                    capture_output=True, text=True, timeout=1
                )
                if r.returncode == 0 and "Render/3D" in r.stdout:
                    import re
                    m = re.search(r'"busy":\s*([\d.]+)', r.stdout)
                    if m:
                        return float(m.group(1))
            except Exception:
                pass

        # macOS — powermetrics (GPU Engine)
        if _OS == "Darwin":
            try:
                r = subprocess.run(
                    ["sudo", "-n", "powermetrics", "-n", "1", "-i", "500",
                     "--samplers", "gpu_power"],
                    capture_output=True, text=True, timeout=2
                )
                if r.returncode == 0 and "GPU" in r.stdout:
                    import re
                    m = re.search(r'GPU\s+Active:\s+([\d.]+)%', r.stdout)
                    if m:
                        return float(m.group(1))
            except Exception:
                pass

        return -1.0

    def _get_temp(self) -> float:
        try:
            temps = psutil.sensors_temperatures()
            candidates = ["coretemp", "k10temp", "cpu_thermal", "acpitz",
                          "cpu-thermal", "zenpower", "it8688"]
            for name in candidates:
                if name in temps:
                    entries = temps[name]
                    if entries:
                        return entries[0].current
            for entries in temps.values():
                if entries:
                    return entries[0].current
        except Exception:
            pass
        if _OS == "Darwin":
            try:
                r = subprocess.run(
                    ["osx-cpu-temp"], capture_output=True, text=True, timeout=2
                )
                if r.returncode == 0:
                    import re
                    m = re.search(r"([\d.]+)", r.stdout)
                    if m:
                        return float(m.group(1))
            except Exception:
                pass

        if _OS == "Windows":
            try:
                r = subprocess.run(
                    ["powershell", "-Command",
                     "(Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace root/wmi).CurrentTemperature"],
                    capture_output=True, text=True, timeout=3
                )
                if r.returncode == 0 and r.stdout.strip():
                    raw = float(r.stdout.strip().split("\n")[0])
                    return (raw / 10.0) - 273.15
            except Exception:
                pass

        return -1.0

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "cpu": self.cpu,
                "mem": self.mem,
                "net": self.net,
                "gpu": self.gpu,
                "tmp": self.tmp,
            }


_metrics = _SysMetrics()

class HudCanvas(QWidget):
    def __init__(self, face_path: str, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.muted    = False
        self.speaking = False
        self.state    = "INITIALISING"

        self._tick       = 0
        self._scale      = 1.0
        self._tgt_scale  = 1.0
        self._halo       = 55.0
        self._tgt_halo   = 55.0
        self._last_t     = time.time()
        self._scan       = 0.0
        self._scan2      = 180.0
        self._rings      = [0.0, 120.0, 240.0, 60.0, 180.0, 300.0, 90.0]
        self._pulses: list[float] = [0.0, 50.0, 100.0]
        self._blink      = True
        self._blink_tick = 0
        self._particles: list[list[float]] = []
        self._face_px: QPixmap | None = None
        self._load_face(face_path)

        self._action_type:       str | None = None
        self._action_label:      str        = ""
        self._action_alpha:      float      = 0.0
        self._action_tick:       int        = 0
        self._action_fade:       str        = "idle"
        self._action_hold_ticks: int        = 0

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(16)

    def _load_face(self, path: str):
        try:
            from PIL import Image, ImageDraw
            import io
            img = Image.open(path).convert("RGBA")
            sz  = min(img.size)
            img = img.resize((sz, sz), Image.LANCZOS)
            mk  = Image.new("L", (sz, sz), 0)
            ImageDraw.Draw(mk).ellipse((2, 2, sz - 2, sz - 2), fill=255)
            img.putalpha(mk)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            px = QPixmap(); px.loadFromData(buf.getvalue())
            self._face_px = px
        except Exception:
            self._face_px = None

    _ACTION_LABELS: dict = {
        "web_search":        "WEB SEARCH",
        "screen_process":    "VISUAL SCAN",
        "weather_report":    "ATMOSPHERE SCAN",
        "open_app":          "LAUNCHING APPLICATION",
        "file_controller":   "FILE SYSTEM ACCESS",
        "file_processor":    "PROCESSING FILE",
        "youtube_video":     "MEDIA CONTROL",
        "send_message":      "TRANSMITTING",
        "reminder":          "SCHEDULING",
        "computer_settings": "SYSTEM CONTROL",
        "computer_control":  "SYSTEM CONTROL",
        "code_helper":       "CODE ANALYSIS",
        "dev_agent":         "DEV AGENT ACTIVE",
        "agent_task":        "TASK AGENT",
        "browser_control":   "BROWSER INTERFACE",
        "flight_finder":     "FLIGHT SCAN",
        "portfolio_tracker": "PORTFOLIO ANALYSIS",
        "calendar_email":    "COMM SYSTEM",
        "game_updater":      "GAME SYSTEM",
        "shutdown_jarvis":   "INITIATING SHUTDOWN",
        "desktop_control":   "DESKTOP CONTROL",
    }

    def show_action(self, action_name: str):
        self._action_type       = action_name
        self._action_alpha      = 0.0
        self._action_tick       = 0
        self._action_fade       = "in"
        self._action_hold_ticks = 0
        self._action_label      = self._ACTION_LABELS.get(
            action_name, action_name.upper().replace("_", " ")
        )

    def _step(self):
        self._tick += 1
        now = time.time()
        if now - self._last_t > (0.12 if self.speaking else 0.5):
            if self.speaking:
                self._tgt_scale = random.uniform(1.06, 1.14)
                self._tgt_halo  = random.uniform(145, 190)
            elif self.muted:
                self._tgt_scale = random.uniform(0.998, 1.002)
                self._tgt_halo  = random.uniform(15, 28)
            else:
                self._tgt_scale = random.uniform(1.001, 1.008)
                self._tgt_halo  = random.uniform(48, 68)
            self._last_t = now

        sp = 0.38 if self.speaking else 0.15
        self._scale += (self._tgt_scale - self._scale) * sp
        self._halo  += (self._tgt_halo  - self._halo)  * sp

        speeds = [1.3, -0.9, 2.0, -1.6, 0.65, -0.45, 1.85] if self.speaking else [0.55, -0.35, 0.9, -0.65, 0.26, -0.18, 0.72]
        for i, spd in enumerate(speeds):
            self._rings[i] = (self._rings[i] + spd) % 360

        self._scan  = (self._scan  + (3.0 if self.speaking else 1.3)) % 360
        self._scan2 = (self._scan2 + (-2.0 if self.speaking else -0.75)) % 360

        fw  = min(self.width(), self.height())
        lim = fw * 0.74
        spd = 4.2 if self.speaking else 1.6
        self._pulses = [r + spd for r in self._pulses if r + spd < lim]
        max_pulses = 3 if self.speaking else 2
        if len(self._pulses) < max_pulses and random.random() < (0.07 if self.speaking else 0.015):
            self._pulses.append(0.0)

        if self.speaking and random.random() < 0.28:
            cx, cy = self.width() / 2, self.height() / 2
            ang = random.uniform(0, 2 * math.pi)
            r_s = fw * 0.28
            self._particles.append([
                cx + math.cos(ang) * r_s, cy + math.sin(ang) * r_s,
                math.cos(ang) * random.uniform(0.9, 2.4),
                math.sin(ang) * random.uniform(0.9, 2.4) - 0.4, 1.0,
            ])
        self._particles = [
            [p[0]+p[2], p[1]+p[3], p[2]*0.97, p[3]*0.97, p[4]-0.028]
            for p in self._particles if p[4] > 0
        ]

        self._blink_tick += 1
        if self._blink_tick >= 38:
            self._blink = not self._blink
            self._blink_tick = 0

        if self._action_type:
            self._action_tick += 1
            if self._action_fade == "in":
                self._action_alpha = min(1.0, self._action_alpha + 0.05)
                if self._action_alpha >= 1.0:
                    self._action_fade = "hold"
            elif self._action_fade == "hold":
                self._action_hold_ticks += 1
                if self._action_hold_ticks > 240:
                    self._action_fade = "out"
            elif self._action_fade == "out":
                self._action_alpha = max(0.0, self._action_alpha - 0.04)
                if self._action_alpha <= 0.0:
                    self._action_type  = None
                    self._action_label = ""
                    self._action_fade  = "idle"

        self.update()

    # ── overlay drawing ────────────────────────────────────────────────────────

    def _draw_overlay(self, p: QPainter, cx, cy, fw):
        if not self._action_type or self._action_alpha <= 0:
            return
        al = self._action_alpha
        tk = self._action_tick

        def qa(base: int) -> int:
            return max(0, min(255, int(base * al)))

        act = self._action_type
        if   act == "web_search":                             self._ov_web(p, cx, cy, fw, tk, qa)
        elif act == "screen_process":                         self._ov_scan(p, cx, cy, fw, tk, qa)
        elif act == "weather_report":                         self._ov_weather(p, cx, cy, fw, tk, qa)
        elif act in ("computer_settings","computer_control"): self._ov_system(p, cx, cy, fw, tk, qa)
        elif act in ("code_helper","dev_agent"):              self._ov_code(p, cx, cy, fw, tk, qa)
        elif act in ("file_controller","file_processor"):     self._ov_file(p, cx, cy, fw, tk, qa)
        elif act == "open_app":                               self._ov_hexgrid(p, cx, cy, fw, tk, qa)
        elif act == "send_message":                           self._ov_signal(p, cx, cy, fw, tk, qa)
        elif act == "youtube_video":                          self._ov_media(p, cx, cy, fw, tk, qa)
        elif act == "browser_control":                        self._ov_globe(p, cx, cy, fw, tk, qa)
        elif act == "reminder":                               self._ov_clock(p, cx, cy, fw, tk, qa)
        elif act == "agent_task":                             self._ov_agent(p, cx, cy, fw, tk, qa)
        elif act == "shutdown_jarvis":                        self._ov_shutdown(p, cx, cy, fw, tk, qa)
        elif act == "flight_finder":                          self._ov_flight(p, cx, cy, fw, tk, qa)
        else:                                                 self._ov_generic(p, cx, cy, fw, tk, qa)

        self._ov_label(p, cx, cy, fw, qa)

    def _ov_label(self, p, cx, cy, fw, qa):
        if not self._action_label:
            return
        lbl_y = cy - fw * 0.44
        lw, lh = fw * 0.65, 24
        p.setBrush(QBrush(qcol(C.BG, qa(200))))
        p.setPen(QPen(qcol(C.PRI, qa(160)), 1))
        p.drawRoundedRect(QRectF(cx - lw/2, lbl_y - lh/2, lw, lh), 4, 4)
        sym = "◈" if (self._action_tick // 18) % 2 == 0 else "◇"
        p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.PRI, qa(230)), 1))
        p.drawText(QRectF(cx - lw/2, lbl_y - lh/2, lw, lh),
                   Qt.AlignmentFlag.AlignCenter,
                   f"{sym}  {self._action_label}")

    def _ov_web(self, p, cx, cy, fw, tk, qa):
        N, node_r = 7, fw * 0.29
        for i in range(N):
            angle = math.radians(tk * 0.28 + i * 360 / N)
            nx = cx + node_r * math.cos(angle)
            ny = cy + node_r * math.sin(angle)
            p.setPen(QPen(qcol(C.PRI, qa(38)), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawLine(QPointF(cx, cy), QPointF(nx, ny))
            t = (tk * 0.018 + i / N) % 1.0
            px2 = cx + (nx - cx) * t; py2 = cy + (ny - cy) * t
            p.setBrush(QBrush(qcol(C.PRI, qa(210)))); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(px2, py2), 2.5, 2.5)
            ba = int(170 + 60 * math.sin(tk * 0.14 + i))
            p.setBrush(QBrush(qcol(C.PRI, qa(ba))))
            p.setPen(QPen(qcol(C.WHITE, qa(180)), 1))
            p.drawEllipse(QPointF(nx, ny), 5, 5)
        hub = fw * 0.042
        p.setBrush(QBrush(qcol(C.PRI_GHO, qa(200)))); p.setPen(QPen(qcol(C.PRI, qa(230)), 2))
        p.drawEllipse(QPointF(cx, cy), hub, hub)
        rr = fw * 0.065
        p.setPen(QPen(qcol(C.ACC2, qa(160)), 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx-rr, cy-rr, rr*2, rr*2), int(tk*5*16), int(200*16))

    def _ov_scan(self, p, cx, cy, fw, tk, qa):
        vw, vh, bl = fw*0.54, fw*0.44, 20
        corners = [(cx-vw/2,cy-vh/2,1,1),(cx+vw/2,cy-vh/2,-1,1),
                   (cx-vw/2,cy+vh/2,1,-1),(cx+vw/2,cy+vh/2,-1,-1)]
        p.setPen(QPen(qcol(C.GREEN, qa(220)), 2))
        for bx, by, dx, dy in corners:
            p.drawLine(QPointF(bx, by), QPointF(bx+dx*bl, by))
            p.drawLine(QPointF(bx, by), QPointF(bx, by+dy*bl))
        scan_y = cy - vh/2 + (tk * 2.2) % vh
        g = QLinearGradient(cx-vw/2, scan_y, cx+vw/2, scan_y)
        g.setColorAt(0.0, qcol(C.GREEN, 0)); g.setColorAt(0.3, qcol(C.GREEN, qa(190)))
        g.setColorAt(0.7, qcol(C.GREEN, qa(190))); g.setColorAt(1.0, qcol(C.GREEN, 0))
        p.setPen(QPen(QBrush(g), 1.5))
        p.drawLine(QPointF(cx-vw/2, scan_y), QPointF(cx+vw/2, scan_y))
        for i in range(1, 7):
            p.setPen(QPen(qcol(C.GREEN, qa(max(0, 55-i*10))), 1))
            p.drawLine(QPointF(cx-vw/2, scan_y+i), QPointF(cx+vw/2, scan_y+i))
        ch = fw * 0.06
        p.setPen(QPen(qcol(C.GREEN, qa(190)), 1))
        p.drawLine(QPointF(cx-ch, cy), QPointF(cx-ch/3, cy))
        p.drawLine(QPointF(cx+ch/3, cy), QPointF(cx+ch, cy))
        p.drawLine(QPointF(cx, cy-ch), QPointF(cx, cy-ch/3))
        p.drawLine(QPointF(cx, cy+ch/3), QPointF(cx, cy+ch))
        cr = fw * 0.024
        p.setPen(QPen(qcol(C.GREEN, qa(190)), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), cr, cr)

    def _ov_weather(self, p, cx, cy, fw, tk, qa):
        rings = [(fw*0.21,fw*0.11,0,C.PRI,140),(fw*0.30,fw*0.16,18,C.ACC2,105),(fw*0.39,fw*0.21,-12,C.PRI,68)]
        for rx, ry, ang, col, ba in rings:
            p.save(); p.translate(cx, cy); p.rotate(ang + tk * 0.22)
            p.setPen(QPen(qcol(col, qa(ba)), 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(-rx, -ry, rx*2, ry*2))
            da = math.radians(tk * 1.6)
            p.setBrush(QBrush(qcol(col, qa(220)))); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(rx*math.cos(da), ry*math.sin(da)), 3.5, 3.5)
            p.restore()
        sr = fw * 0.038
        p.setPen(QPen(qcol(C.ACC2, qa(210)), 1.5)); p.setBrush(QBrush(qcol(C.ACC2, qa(55))))
        p.drawEllipse(QPointF(cx, cy), sr, sr)
        for i in range(8):
            ra = math.radians(i*45 + tk*0.55); r1, r2 = sr*1.45, sr*1.95
            p.setPen(QPen(qcol(C.ACC2, qa(170)), 1.5))
            p.drawLine(QPointF(cx+r1*math.cos(ra),cy+r1*math.sin(ra)),
                       QPointF(cx+r2*math.cos(ra),cy+r2*math.sin(ra)))

    def _ov_system(self, p, cx, cy, fw, tk, qa):
        for i in range(4):
            sz = fw*(0.07+i*0.075+(tk*0.55%(fw*0.075))/fw)
            a  = qa(int(145*(1-i/4)))
            p.save(); p.translate(cx, cy); p.rotate(tk*0.42+i*18)
            p.setPen(QPen(qcol(C.ACC, a), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(-sz, -sz, sz*2, sz*2)); p.restore()
        tr = fw * 0.058
        p.setPen(QPen(qcol(C.ACC, qa(210)), 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), tr, tr)
        ch, gap = fw*0.13, tr*1.28
        p.setPen(QPen(qcol(C.ACC, qa(165)), 1))
        for pts in [(cx-ch,cy,cx-gap,cy),(cx+gap,cy,cx+ch,cy),(cx,cy-ch,cx,cy-gap),(cx,cy+gap,cx,cy+ch)]:
            p.drawLine(QPointF(pts[0],pts[1]), QPointF(pts[2],pts[3]))
        bsz = fw * 0.075
        for bx, by in [(cx-fw*0.26,cy-fw*0.19),(cx+fw*0.18,cy+fw*0.14)]:
            p.setPen(QPen(qcol(C.ACC, qa(115)), 1)); p.setBrush(QBrush(qcol("#080400", qa(180))))
            p.drawRect(QRectF(bx, by, bsz, bsz*0.45))
            fw2 = int(bsz*(0.25+0.45*math.sin(tk*0.12)))
            p.setBrush(QBrush(qcol(C.ACC, qa(150)))); p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(QRectF(bx+1, by+1, fw2, bsz*0.45-2))

    def _ov_code(self, p, cx, cy, fw, tk, qa):
        cols = 11; col_w = fw*0.76/cols; x0 = cx-fw*0.38
        chars = "01アABCDEF01234<>{}[]#$@%!?"
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        for c in range(cols):
            x = x0+c*col_w; rng_c = random.Random(c*137+(tk//7))
            head_y = cy-fw*0.36+(tk*1.9+c*29)%(fw*0.72)
            p.setPen(QPen(qcol(C.WHITE, qa(225)), 1))
            p.drawText(QPointF(x, head_y), rng_c.choice(chars))
            for t in range(1, 7):
                ty = head_y-t*11
                if ty < cy-fw*0.38: continue
                p.setPen(QPen(qcol(C.GREEN, qa(int(155*(1-t/7)))), 1))
                p.drawText(QPointF(x, ty), random.Random(c*137+(tk//7)+t).choice(chars))
        p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        cur = "█" if (tk//22)%2==0 else " "
        p.setPen(QPen(qcol(C.GREEN, qa(195)), 1))
        p.drawText(QRectF(cx-45, cy+fw*0.33, 90, 20), Qt.AlignmentFlag.AlignCenter, f"> {cur}")

    def _ov_file(self, p, cx, cy, fw, tk, qa):
        sx, dx2 = cx-fw*0.3, cx+fw*0.3
        p.setPen(QPen(qcol(C.PRI, qa(38)), 2))
        p.drawLine(QPointF(sx, cy), QPointF(dx2, cy))
        for i in range(4):
            t = (tk*0.014+i*0.25)%1.0; px2 = sx+(dx2-sx)*t
            bw, bh = fw*0.058, fw*0.026
            ba = int(185*(1-abs(t-0.5)*1.6+0.4))
            p.setBrush(QBrush(qcol(C.PRI, qa(max(0,ba)))))
            p.setPen(QPen(qcol(C.WHITE, qa(115)), 1))
            p.drawRect(QRectF(px2-bw/2, cy-bh/2, bw, bh))
        iw, ih = fw*0.075, fw*0.058
        p.setPen(QPen(qcol(C.PRI, qa(185)), 1.5)); p.setBrush(QBrush(qcol(C.PRI_GHO, qa(95))))
        p.drawRect(QRectF(sx-iw/2, cy-ih/2, iw, ih))
        p.drawRect(QRectF(sx-iw/2, cy-ih/2-ih*0.28, iw*0.48, ih*0.28))
        for si in range(3):
            p.setPen(QPen(qcol(C.ACC2, qa(165-si*30)), 1)); p.setBrush(QBrush(qcol(C.PRI_GHO, qa(55))))
            p.drawRect(QRectF(dx2-iw/2-si*3, cy-ih/2-si*3, iw, ih))
        bar_y, bar_w = cy+fw*0.13, fw*0.5; prog = (tk*0.0075)%1.0
        p.setPen(QPen(qcol(C.BORDER, qa(115)), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(cx-bar_w/2, bar_y, bar_w, 4))
        p.setBrush(QBrush(qcol(C.PRI, qa(185)))); p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(QRectF(cx-bar_w/2, bar_y, bar_w*prog, 4))

    def _ov_hexgrid(self, p, cx, cy, fw, tk, qa):
        hr = fw*0.058; wave = (tk*0.038)%4.2
        def draw_hex(hx, hy, col, alpha):
            path = QPainterPath()
            for i in range(6):
                a = math.radians(60*i-30)
                pt = QPointF(hx+hr*0.9*math.cos(a), hy+hr*0.9*math.sin(a))
                path.moveTo(pt) if i==0 else path.lineTo(pt)
            path.closeSubpath()
            p.setPen(QPen(qcol(col, qa(alpha)), 1)); p.setBrush(QBrush(qcol(col, qa(max(0,alpha-110)))))
            p.drawPath(path)
        for ring in range(5):
            ra = max(0, int(195-abs(wave-ring*1.05)*130))
            if ring == 0: draw_hex(cx, cy, C.PRI, ra)
            else:
                for i in range(6):
                    ba = math.radians(i*60)
                    hx2 = cx+hr*1.732*ring*math.cos(ba); hy2 = cy+hr*1.732*ring*math.sin(ba)
                    if abs(hx2-cx)>fw*0.42 or abs(hy2-cy)>fw*0.42: continue
                    draw_hex(hx2, hy2, C.PRI, max(0, ra//(ring)))

    def _ov_signal(self, p, cx, cy, fw, tk, qa):
        ox = cx-fw*0.08
        for i in range(6):
            wr = fw*(0.05+i*0.065+(tk*0.011)%0.065); a = qa(int(205*(1-i/6)))
            p.setPen(QPen(qcol(C.PRI, a), max(1, 2-i//3))); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(ox-wr, cy-wr, wr*2, wr*2), -55*16, 110*16)
        p.setBrush(QBrush(qcol(C.PRI, qa(225)))); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(ox, cy), 5, 5)
        for i in range(3):
            t = (tk*0.019+i*0.33)%1.0; ba = math.radians(-55+110*t)
            br = fw*(0.09+i*0.065)
            p.setBrush(QBrush(qcol(C.ACC2, qa(205)))); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(ox+br*math.cos(ba), cy+br*math.sin(ba)), 3, 3)

    def _ov_media(self, p, cx, cy, fw, tk, qa):
        tr = fw*0.062
        path = QPainterPath()
        for i,(rx,ry) in enumerate([(-tr*0.55,-tr),(tr,0),(-tr*0.55,tr)]):
            path.moveTo(cx+rx,cy+ry) if i==0 else path.lineTo(cx+rx,cy+ry)
        path.closeSubpath()
        p.setBrush(QBrush(qcol(C.ACC, qa(185)))); p.setPen(QPen(qcol(C.ACC, qa(225)), 2))
        p.drawPath(path)
        bw = fw*0.014
        for side in (-1, 1):
            x0 = cx+side*(tr*1.65)
            for i in range(5):
                bh = fw*random.Random(tk//5+i+side*77).uniform(0.028,0.13)
                bx2 = x0-side*i*(bw+2) if side==-1 else x0+side*i*(bw+2)
                p.setBrush(QBrush(qcol(C.PRI if i%2==0 else C.PRI_DIM, qa(165)))); p.setPen(Qt.PenStyle.NoPen)
                p.drawRect(QRectF(bx2, cy-bh/2, bw, bh))
        rr = fw*(0.12+0.038*math.sin(tk*0.09))
        p.setPen(QPen(qcol(C.ACC, qa(105)), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), rr, rr)

    def _ov_globe(self, p, cx, cy, fw, tk, qa):
        gr = fw*0.21
        p.setPen(QPen(qcol(C.PRI, qa(165)), 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), gr, gr)
        for lat in range(-3, 4):
            yo = lat*gr/3.4
            if abs(yo) >= gr: continue
            hw = math.sqrt(gr**2-yo**2); a = qa(max(28, 115-abs(lat)*18))
            p.setPen(QPen(qcol(C.PRI, a), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(cx-hw, cy+yo-hw*0.28, hw*2, hw*0.56), 0, 180*16)
        for lon in range(5):
            p.save(); p.translate(cx, cy); p.rotate(lon*36+tk*0.38)
            p.setPen(QPen(qcol(C.PRI, qa(62)), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(-gr*0.14, -gr, gr*0.28, gr*2)); p.restore()
        sa = math.radians(tk*1.55)
        p.setBrush(QBrush(qcol(C.ACC2, qa(225)))); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx+gr*1.14*math.cos(sa), cy+gr*0.48*math.sin(sa)), 4, 4)

    def _ov_clock(self, p, cx, cy, fw, tk, qa):
        cr = fw*0.19
        p.setPen(QPen(qcol(C.PRI, qa(185)), 1.5)); p.setBrush(QBrush(qcol(C.PRI_GHO, qa(55))))
        p.drawEllipse(QPointF(cx, cy), cr, cr)
        for i in range(12):
            a = math.radians(i*30-90); r1 = cr*(0.80 if i%3==0 else 0.87); r2 = cr*0.96
            p.setPen(QPen(qcol(C.PRI, qa(185 if i%3==0 else 95)), 1.5 if i%3==0 else 1))
            p.drawLine(QPointF(cx+r1*math.cos(a),cy+r1*math.sin(a)), QPointF(cx+r2*math.cos(a),cy+r2*math.sin(a)))
        ma = math.radians(tk*0.82-90); ha = math.radians(tk*0.068-90)
        p.setPen(QPen(qcol(C.WHITE, qa(205)), 2.5))
        p.drawLine(QPointF(cx,cy), QPointF(cx+cr*0.52*math.cos(ha),cy+cr*0.52*math.sin(ha)))
        p.setPen(QPen(qcol(C.PRI, qa(205)), 1.5))
        p.drawLine(QPointF(cx,cy), QPointF(cx+cr*0.76*math.cos(ma),cy+cr*0.76*math.sin(ma)))
        p.setBrush(QBrush(qcol(C.ACC, qa(225)))); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), 3.5, 3.5)

    def _ov_agent(self, p, cx, cy, fw, tk, qa):
        nodes = [(cx,cy),(cx-fw*0.22,cy-fw*0.12),(cx+fw*0.22,cy-fw*0.12),
                 (cx-fw*0.22,cy+fw*0.12),(cx+fw*0.22,cy+fw*0.12)]
        for i,(nx,ny) in enumerate(nodes[1:],1):
            p.setPen(QPen(qcol(C.PRI, qa(48)), 1))
            p.drawLine(QPointF(nodes[0][0],nodes[0][1]), QPointF(nx,ny))
            t2 = (tk*0.017+i*0.2)%1.0; px2=nodes[0][0]+(nx-nodes[0][0])*t2; py2=nodes[0][1]+(ny-nodes[0][1])*t2
            p.setBrush(QBrush(qcol(C.ACC2, qa(225)))); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(px2,py2), 3, 3)
        for i,(nx,ny) in enumerate(nodes):
            is_c = i==0; r2 = fw*0.033 if is_c else fw*0.021
            pa = int(175+60*math.sin(tk*0.11+i*1.2)); col = C.ACC2 if is_c else C.PRI
            p.setBrush(QBrush(qcol(col, qa(pa)))); p.setPen(QPen(qcol(C.WHITE, qa(185)), 1))
            p.drawEllipse(QPointF(nx,ny), r2, r2)
            if not is_c:
                p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(qcol(col, qa(75)), 1))
                p.drawEllipse(QPointF(nx,ny), r2*1.85, r2*1.85)

    def _ov_shutdown(self, p, cx, cy, fw, tk, qa):
        sr = fw*0.088
        p.setPen(QPen(qcol(C.RED, qa(225)), 3)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx-sr,cy-sr,sr*2,sr*2), int((90+38)*16), int((360-76)*16))
        p.drawLine(QPointF(cx,cy-sr*0.38), QPointF(cx,cy-sr*1.18))
        collapse = min(1.0, tk*0.007)
        for i in range(5):
            br = fw*(0.40-i*0.045)*(1.0-collapse*0.35)
            p.setPen(QPen(qcol(C.RED, qa(int(145*(1-i/5)*(1-collapse)))), 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx,cy), br, br)
        if (tk//14)%2==0:
            p.setFont(QFont("Consolas", 9, QFont.Weight.Bold)); p.setPen(QPen(qcol(C.RED, qa(225)), 1))
            p.drawText(QRectF(cx-65,cy+sr*1.65,130,20), Qt.AlignmentFlag.AlignCenter, "SHUTTING DOWN")

    def _ov_flight(self, p, cx, cy, fw, tk, qa):
        p1 = QPointF(cx-fw*0.3, cy+fw*0.11); p2 = QPointF(cx+fw*0.3, cy+fw*0.11)
        arc = QPointF(cx, cy-fw*0.21)
        path = QPainterPath(p1); path.quadTo(arc, p2)
        p.setPen(QPen(qcol(C.PRI, qa(115)), 1, Qt.PenStyle.DashLine)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        t = (tk*0.009)%1.0
        bx2=(1-t)**2*p1.x()+2*(1-t)*t*arc.x()+t**2*p2.x()
        by2=(1-t)**2*p1.y()+2*(1-t)*t*arc.y()+t**2*p2.y()
        p.setBrush(QBrush(qcol(C.ACC2, qa(225)))); p.setPen(QPen(qcol(C.WHITE, qa(205)), 1))
        p.drawEllipse(QPointF(bx2,by2), 5, 5)
        for pt, col in [(p1,C.GREEN),(p2,C.PRI)]:
            p.setPen(QPen(qcol(col, qa(185)), 1.5)); p.setBrush(QBrush(qcol(col, qa(75))))
            p.drawEllipse(pt, 5, 5)
            pr2 = 8+(tk*0.55%8)
            p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(qcol(col, qa(int(95*(1-(pr2-8)/8)))), 1))
            p.drawEllipse(pt, pr2, pr2)

    def _ov_generic(self, p, cx, cy, fw, tk, qa):
        for ring in range(3):
            r = fw*(0.11+ring*0.09); segs = 6+ring*2
            for i in range(segs):
                a1 = math.radians(tk*(0.52-ring*0.14)+i*360/segs)
                a2 = math.radians(tk*(0.52-ring*0.14)+(i+0.68)*360/segs)
                p.setPen(QPen(qcol([C.PRI,C.ACC2,C.GREEN][ring], qa(145-ring*38)), 2-ring*0.45))
                p.drawLine(QPointF(cx+r*math.cos(a1),cy+r*math.sin(a1)),
                           QPointF(cx+r*math.cos(a2),cy+r*math.sin(a2)))

    # ── end overlay drawing ────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), qcol(C.BG))

        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        fw = min(W, H)

        # hex dot grid background
        hs = 38
        p.setPen(QPen(qcol(C.PRI_GHO, 95), 1.5))
        row = 0
        y_dot = 0
        while y_dot <= H:
            x_off = hs // 2 if row % 2 else 0
            x_dot = x_off
            while x_dot <= W:
                p.drawPoint(int(x_dot), int(y_dot))
                x_dot += hs
            y_dot += int(hs * 0.866)
            row += 1

        r_face = fw * 0.31

        # halo glow
        for i in range(10):
            r   = r_face * (1.8 - i * 0.08)
            frc = 1.0 - i / 10
            a   = max(0, min(255, int(self._halo * 0.085 * frc)))
            col = qcol(C.MUTED_C if self.muted else C.PRI, a)
            p.setPen(QPen(col, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # pulse rings
        for pr in self._pulses:
            a   = max(0, int(230 * (1.0 - pr / (fw * 0.74))))
            col = qcol(C.MUTED_C if self.muted else C.PRI, a)
            p.setPen(QPen(col, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(cx - pr, cy - pr, pr * 2, pr * 2))

        # spinning arc rings (7 layers: 2 outer decorative, 3 main, 2 inner)
        _ring_cfg = [
            (0.58, 1,  42, 185),   # outermost — sparse
            (0.53, 1,  68, 118),   # outer
            (0.48, 3, 115,  78),   # main 0
            (0.40, 2,  78,  55),   # main 1
            (0.32, 1,  56,  40),   # main 2
            (0.24, 1,  35,  52),   # inner
            (0.15, 1,  22,  35),   # innermost
        ]
        for idx, (r_frac, w_r, arc_l, gap) in enumerate(_ring_cfg):
            ring_r = fw * r_frac
            base   = self._rings[idx]
            if idx < 2:
                a_val = max(0, min(255, int(self._halo * (0.38 - idx * 0.08))))
            elif idx >= 5:
                a_val = max(0, min(255, int(self._halo * (0.52 - (idx-5) * 0.14))))
            else:
                a_val = max(0, min(255, int(self._halo * (1.0 - (idx-2) * 0.22))))
            col    = qcol(C.MUTED_C if self.muted else C.PRI, a_val)
            p.setPen(QPen(col, w_r)); p.setBrush(Qt.BrushStyle.NoBrush)
            angle = base
            rect  = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)
            while angle < base + 360:
                p.drawArc(rect, int(angle * 16), int(arc_l * 16))
                angle += arc_l + gap

        # scanners
        sr = fw * 0.50
        sa = min(255, int(self._halo * 1.5))
        ex = 75 if self.speaking else 44
        p.setPen(QPen(qcol(C.MUTED_C if self.muted else C.PRI, sa), 2.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        srect = QRectF(cx - sr, cy - sr, sr * 2, sr * 2)
        p.drawArc(srect, int(self._scan * 16), int(ex * 16))
        p.setPen(QPen(qcol(C.ACC, sa // 2), 1.5))
        p.drawArc(srect, int(self._scan2 * 16), int(ex * 16))

        # tick marks
        t_out, t_in = fw * 0.497, fw * 0.474
        p.setPen(QPen(qcol(C.PRI, 140), 1))
        for deg in range(0, 360, 10):
            rad = math.radians(deg)
            inn = t_in if deg % 30 == 0 else t_in + 6
            p.drawLine(
                QPointF(cx + t_out * math.cos(rad), cy - t_out * math.sin(rad)),
                QPointF(cx + inn  * math.cos(rad), cy - inn  * math.sin(rad)),
            )

        # crosshair
        ch_r, gap_h = fw * 0.51, fw * 0.16
        p.setPen(QPen(qcol(C.PRI, int(self._halo * 0.5)), 1))
        p.drawLine(QPointF(cx - ch_r, cy), QPointF(cx - gap_h, cy))
        p.drawLine(QPointF(cx + gap_h, cy), QPointF(cx + ch_r, cy))
        p.drawLine(QPointF(cx, cy - ch_r), QPointF(cx, cy - gap_h))
        p.drawLine(QPointF(cx, cy + gap_h), QPointF(cx, cy + ch_r))

        # corner brackets
        bl = 24
        bc = qcol(C.PRI, 210)
        hl, hr = cx - fw // 2, cx + fw // 2
        ht, hb = cy - fw // 2, cy + fw // 2
        p.setPen(QPen(bc, 2))
        for bx, by, dx, dy in [(hl,ht,1,1),(hr,ht,-1,1),(hl,hb,1,-1),(hr,hb,-1,-1)]:
            p.drawLine(QPointF(bx, by), QPointF(bx + dx * bl, by))
            p.drawLine(QPointF(bx, by), QPointF(bx, by + dy * bl))

        # arc reactor core glow (beneath face)
        for i in range(10, 0, -1):
            rg = r_face * 0.54 * i / 10
            intensity = self._halo / 172.0
            a = max(0, min(255, int(42 * intensity * (i / 10) ** 0.65)))
            col = C.MUTED_C if self.muted else C.PRI
            p.setBrush(QBrush(qcol(col, a))); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), rg, rg)
        # Rotating hex spokes around core
        hex_a = max(0, min(255, int(self._halo * 0.52)))
        col = C.MUTED_C if self.muted else C.PRI
        for i in range(6):
            ha = math.radians(i * 60 + self._rings[4] * 0.9)
            p.setPen(QPen(qcol(col, hex_a), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawLine(
                QPointF(cx + r_face*0.17*math.cos(ha), cy + r_face*0.17*math.sin(ha)),
                QPointF(cx + r_face*0.30*math.cos(ha), cy + r_face*0.30*math.sin(ha)),
            )
        # Bright center core dot
        core_r = r_face * 0.066
        core_a = min(255, int(self._halo * 1.9))
        for ci in range(5, 0, -1):
            ga = max(0, min(255, int(core_a * (1 - ci/6) * 0.42)))
            p.setBrush(QBrush(qcol(col, ga))); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), core_r * ci, core_r * ci)
        p.setBrush(QBrush(qcol(C.WHITE, min(255, int(core_a * 0.82)))))
        p.drawEllipse(QPointF(cx, cy), core_r * 0.45, core_r * 0.45)

        # face
        if self._face_px:
            fsz    = int(fw * 0.62 * self._scale)
            scaled = self._face_px.scaled(
                fsz, fsz,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            p.drawPixmap(int(cx - fsz / 2), int(cy - fsz / 2), scaled)
        else:
            orb_r = int(fw * 0.27 * self._scale)
            oc    = (200, 0, 50) if self.muted else (0, 60, 110)
            for i in range(8, 0, -1):
                r2  = int(orb_r * i / 8)
                frc = i / 8
                a   = max(0, min(255, int(self._halo * 1.1 * frc)))
                p.setBrush(QBrush(QColor(int(oc[0]*frc), int(oc[1]*frc), int(oc[2]*frc), a)))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(cx - r2, cy - r2, r2 * 2, r2 * 2))
            p.setPen(QPen(qcol(C.PRI, min(255, int(self._halo * 2))), 1))
            p.setFont(QFont("Consolas", 15, QFont.Weight.Bold))
            p.drawText(QRectF(cx - 90, cy - 16, 180, 32),
                       Qt.AlignmentFlag.AlignCenter, "J.A.R.V.I.S")

        # action overlay
        self._draw_overlay(p, cx, cy, fw)

        # particles
        for pt in self._particles:
            a = max(0, min(255, int(pt[4] * 255)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(C.PRI, a)))
            p.drawEllipse(QPointF(pt[0], pt[1]), 2.5, 2.5)

        # status text
        sy = cy + fw * 0.40
        if self.muted:
            txt, col = "⊘  MUTED",     qcol(C.MUTED_C)
        elif self.speaking:
            txt, col = "●  SPEAKING",  qcol(C.ACC)
        elif self.state == "THINKING":
            sym = "◈" if self._blink else "◇"
            txt, col = f"{sym}  THINKING",   qcol(C.ACC2)
        elif self.state == "PROCESSING":
            sym = "▷" if self._blink else "▶"
            txt, col = f"{sym}  PROCESSING", qcol(C.ACC2)
        elif self.state == "LISTENING":
            sym = "●" if self._blink else "○"
            txt, col = f"{sym}  LISTENING",  qcol(C.GREEN)
        else:
            sym = "●" if self._blink else "○"
            txt, col = f"{sym}  {self.state}", qcol(C.PRI)

        p.setPen(QPen(col, 1))
        p.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        p.drawText(QRectF(0, sy, W, 28), Qt.AlignmentFlag.AlignCenter, txt)

        # waveform
        wy = sy + 30
        N, bw = 36, 8
        wx0 = (W - N * bw) / 2
        for i in range(N):
            if self.muted:
                hgt, cl = 2, qcol(C.MUTED_C)
            elif self.speaking:
                hgt = random.randint(3, 20)
                cl  = qcol(C.PRI) if hgt > 12 else qcol(C.PRI_DIM)
            else:
                hgt = int(3 + 2 * math.sin(self._tick * 0.09 + i * 0.6))
                cl  = qcol(C.BORDER_B)
            p.fillRect(QRectF(wx0 + i * bw, wy + 20 - hgt, bw - 1, hgt), cl)

class MetricBar(QWidget):

    def __init__(self, label: str, color: str = C.PRI, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0       # 0–100
        self._text  = "--"
        self.setFixedHeight(38)
        self.setMinimumWidth(80)

    def set_value(self, pct: float, text: str):
        self._value = max(0.0, min(100.0, pct))
        self._text  = text
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        p.setBrush(QBrush(qcol(C.PANEL2)))
        p.setPen(QPen(qcol(C.BORDER_A), 1))
        p.drawRoundedRect(QRectF(1, 1, W - 2, H - 2), 4, 4)

        bar_h   = 4
        bar_y   = H - bar_h - 5
        bar_w   = W - 12
        bar_x   = 6
        fill_w  = int(bar_w * self._value / 100)

        p.setBrush(QBrush(qcol(C.BAR_BG)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2, 2)

        if self._value > 85:
            bar_col = qcol(C.RED)
        elif self._value > 65:
            bar_col = qcol(C.ACC)
        else:
            bar_col = qcol(self._color)

        if fill_w > 0:
            p.setBrush(QBrush(bar_col))
            p.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 2, 2)

        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(8, 5, 50, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._label)

        p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        p.setPen(QPen(bar_col if self._text != "--" else qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(0, 4, W - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._text)

class ArcGauge(QWidget):

    def __init__(self, label: str, color: str = C.PRI, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0
        self._text  = "--"
        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_value(self, pct: float, text: str):
        self._value = max(0.0, min(100.0, pct))
        self._text  = text
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2 - 2
        r  = min(W, H - 4) / 2 - 5
        ar = r - 5

        arc_col = C.RED if self._value > 85 else C.ACC if self._value > 65 else self._color

        # Outer glow aura
        p.setPen(QPen(qcol(self._color, 22), 9)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r + 1, r + 1)

        # Background fill
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(qcol(C.PANEL2, 215)))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Track arc (270°, gap at bottom)
        p.setPen(QPen(qcol(C.BAR_BG, 255), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx-ar, cy-ar, ar*2, ar*2), 225*16, -270*16)

        # Value arc
        span = int(-270 * self._value / 100) * 16
        if span:
            p.setPen(QPen(qcol(arc_col, 240), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawArc(QRectF(cx-ar, cy-ar, ar*2, ar*2), 225*16, span)
            # Glow dot at arc tip
            end_rad = math.radians(225 - 270 * self._value / 100)
            gx = cx + ar * math.cos(end_rad)
            gy = cy - ar * math.sin(end_rad)
            for gi in range(4, 0, -1):
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(qcol(arc_col, 50 * gi)))
                p.drawEllipse(QPointF(gx, gy), gi * 2.4, gi * 2.4)

        # Border ring
        p.setPen(QPen(qcol(C.BORDER_A, 110), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Value text
        p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        p.setPen(QPen(qcol(arc_col if self._text != "--" else C.TEXT_DIM, 235), 1))
        p.drawText(QRectF(0, cy - 9, W, 16), Qt.AlignmentFlag.AlignCenter, self._text)

        # Label text below value
        p.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.TEXT_DIM, 160), 1))
        p.drawText(QRectF(0, cy + 5, W, 11), Qt.AlignmentFlag.AlignCenter, self._label)


class LogWidget(QTextEdit):
    _sig = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 11))
        self.setStyleSheet(f"""
            QTextEdit {{
                background: {C.PANEL};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 6px;
                padding: 12px;
                selection-background-color: {C.PRI_GHO};
            }}
            QScrollBar:vertical {{
                background: {C.BG};
                width: 8px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_B};
                border-radius: 4px;
                min-height: 20px;
            }}
        """)
        self._queue: list[str] = []
        self._typing  = False
        self._text    = ""
        self._pos     = 0
        self._tag     = "sys"
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._sig.connect(self._enqueue)

    def append_log(self, text: str):
        self._sig.emit(text)

    def _enqueue(self, text: str):
        self._queue.append(text)
        if not self._typing:
            self._next()

    def _next(self):
        if not self._queue:
            self._typing = False
            return
        self._typing = True
        self._text   = self._queue.pop(0)
        self._pos    = 0
        tl = self._text.lower()
        if   tl.startswith("you:"):    self._tag = "you"
        elif tl.startswith("jarvis:"): self._tag = "ai"
        elif tl.startswith("file:"):   self._tag = "file"
        elif "err" in tl:              self._tag = "err"
        else:                          self._tag = "sys"
        self._tmr.start(6)

    def _step(self):
        if self._pos < len(self._text):
            ch  = self._text[self._pos]
            cur = self.textCursor()
            fmt = cur.charFormat()
            col = {
                "you":  qcol(C.WHITE),
                "ai":   qcol(C.PRI),
                "err":  qcol(C.RED),
                "file": qcol(C.GREEN),
                "sys":  qcol(C.ACC2),
            }.get(self._tag, qcol(C.TEXT))
            fmt.setForeground(QBrush(col))
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText(ch, fmt)
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            self._pos += 1
        else:
            self._tmr.stop()
            cur = self.textCursor()
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText("\n")
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            QTimer.singleShot(20, self._next)

_FILE_ICONS = {
    "image":   ("🖼", "#00d4ff"), "video":   ("🎬", "#ff6b00"),
    "audio":   ("🎵", "#cc44ff"), "pdf":     ("📄", "#ff4444"),
    "word":    ("📝", "#4488ff"), "excel":   ("📊", "#44bb44"),
    "code":    ("💻", "#ffcc00"), "archive": ("📦", "#ff8844"),
    "pptx":    ("📊", "#ff6622"), "text":    ("📃", "#aaaaaa"),
    "data":    ("🔧", "#88ddff"), "unknown": ("📎", "#888888"),
}
_EXT_TO_CAT = {
    **dict.fromkeys(["jpg","jpeg","png","gif","webp","bmp","tiff","svg","ico"], "image"),
    **dict.fromkeys(["mp4","avi","mov","mkv","wmv","flv","webm","m4v"],         "video"),
    **dict.fromkeys(["mp3","wav","ogg","m4a","aac","flac","wma","opus"],        "audio"),
    **dict.fromkeys(["pdf"],                                                     "pdf"),
    **dict.fromkeys(["doc","docx"],                                              "word"),
    **dict.fromkeys(["xls","xlsx","ods"],                                        "excel"),
    **dict.fromkeys(["ppt","pptx"],                                              "pptx"),
    **dict.fromkeys(["py","js","ts","jsx","tsx","html","css","java","c","cpp",
                     "cs","go","rs","rb","php","swift","kt","sh","sql","lua"],   "code"),
    **dict.fromkeys(["zip","rar","tar","gz","7z","bz2","xz"],                   "archive"),
    **dict.fromkeys(["txt","md","rst","log"],                                    "text"),
    **dict.fromkeys(["csv","tsv","json","xml"],                                  "data"),
}

def _file_category(path: Path) -> str:
    return _EXT_TO_CAT.get(path.suffix.lower().lstrip("."), "unknown")

def _fmt_size(size: int) -> str:
    if   size < 1024:    return f"{size} B"
    elif size < 1024**2: return f"{size/1024:.1f} KB"
    elif size < 1024**3: return f"{size/1024**2:.1f} MB"
    else:                return f"{size/1024**3:.1f} GB"


class FileDropZone(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(100)
        self._current_file: str | None = None
        self._hovering  = False
        self._drag_over = False
        self._dash_offset = 0.0
        self._anim_tmr = QTimer(self)
        self._anim_tmr.timeout.connect(self._animate)
        self._anim_tmr.start(40)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._canvas = _DropCanvas(self)
        layout.addWidget(self._canvas)

    def _animate(self):
        self._dash_offset = (self._dash_offset + 0.8) % 20
        self._canvas.update()

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._drag_over = True; self._canvas.update()

    def dragLeaveEvent(self, e):
        self._drag_over = False; self._canvas.update()

    def dropEvent(self, e: QDropEvent):
        self._drag_over = False
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).is_file():
                self._set_file(path)
        self._canvas.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._browse()

    def enterEvent(self, e):
        self._hovering = True; self._canvas.update()

    def leaveEvent(self, e):
        self._hovering = False; self._canvas.update()

    def current_file(self) -> str | None:
        return self._current_file

    def clear_file(self):
        self._current_file = None; self._canvas.update()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a file for JARVIS", str(Path.home()),
            "All Files (*.*);;"
            "Images (*.jpg *.jpeg *.png *.gif *.webp *.bmp *.svg);;"
            "Documents (*.pdf *.docx *.txt *.md *.pptx);;"
            "Data (*.csv *.xlsx *.json *.xml);;"
            "Code (*.py *.js *.ts *.html *.css *.java *.cpp *.go);;"
            "Audio (*.mp3 *.wav *.ogg *.m4a *.aac *.flac);;"
            "Video (*.mp4 *.avi *.mov *.mkv *.wmv *.webm);;"
            "Archives (*.zip *.rar *.tar *.gz *.7z)",
        )
        if path:
            self._set_file(path)

    def _set_file(self, path: str):
        self._current_file = path
        self._canvas.update()
        self.file_selected.emit(path)


class _DropCanvas(QWidget):
    def __init__(self, zone: FileDropZone):
        super().__init__(zone)
        self._z = zone

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        z    = self._z
        W, H = self.width(), self.height()
        pad  = 6
        rect = QRectF(pad, pad, W - pad * 2, H - pad * 2)

        bg_col = qcol("#001a24" if z._drag_over else ("#001218" if z._hovering else C.PANEL))
        p.setBrush(QBrush(bg_col)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, 6, 6)

        if z._current_file:   border_col = qcol(C.GREEN, 200)
        elif z._drag_over:    border_col = qcol(C.PRI, 230)
        elif z._hovering:     border_col = qcol(C.BORDER_B, 200)
        else:                 border_col = qcol(C.BORDER, 160)

        pen = QPen(border_col, 1.5, Qt.PenStyle.DashLine)
        pen.setDashOffset(z._dash_offset)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 6, 6)

        if z._current_file:   self._paint_file(p, W, H)
        elif z._drag_over:    self._paint_drag_over(p, W, H)
        else:                 self._paint_idle(p, W, H, z._hovering)

    def _paint_idle(self, p, W, H, hover):
        cx, cy = W / 2, H / 2
        col = qcol(C.PRI_DIM if not hover else C.PRI)
        p.setPen(QPen(col, 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(cx, cy - 14), QPointF(cx, cy + 4))
        p.drawLine(QPointF(cx - 8, cy - 6), QPointF(cx, cy - 14))
        p.drawLine(QPointF(cx + 8, cy - 6), QPointF(cx, cy - 14))
        p.drawLine(QPointF(cx - 14, cy + 4), QPointF(cx + 14, cy + 4))
        p.setFont(QFont("Consolas", 9))
        p.setPen(QPen(qcol(C.PRI_DIM if not hover else C.TEXT), 1))
        p.drawText(QRectF(0, cy + 8, W, 16), Qt.AlignmentFlag.AlignCenter,
                   "Drop file here  or  Click to Browse")
        p.setFont(QFont("Consolas", 8))
        p.setPen(QPen(qcol("#1a4a5a"), 1))
        p.drawText(QRectF(0, cy + 24, W, 14), Qt.AlignmentFlag.AlignCenter,
                   "Images · Video · Audio · PDF · Docs · Code · Data")

    def _paint_drag_over(self, p, W, H):
        cx, cy = W / 2, H / 2
        p.setFont(QFont("Consolas", 20))
        p.setPen(QPen(qcol(C.PRI), 1))
        p.drawText(QRectF(0, cy - 24, W, 32), Qt.AlignmentFlag.AlignCenter, "⬇")
        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.PRI), 1))
        p.drawText(QRectF(0, cy + 12, W, 16), Qt.AlignmentFlag.AlignCenter, "Release to load")

    def _paint_file(self, p, W, H):
        path = Path(self._z._current_file)
        cat  = _file_category(path)
        icon, icon_col = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size_str = _fmt_size(path.stat().st_size)
        ext_str  = path.suffix.upper().lstrip(".") or "FILE"

        block_x, block_w = 10, 60
        p.setFont(QFont("Segoe UI Emoji", 22) if _OS == "Windows" else QFont("Arial", 22))
        p.setPen(QPen(qcol(icon_col), 1))
        p.drawText(QRectF(block_x, 0, block_w, H), Qt.AlignmentFlag.AlignCenter, icon)

        tx = block_x + block_w + 6
        tw = W - tx - 38

        p.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.WHITE), 1))
        name = path.name if len(path.name) <= 34 else path.name[:31] + "..."
        p.drawText(QRectF(tx, H * 0.18, tw, 16),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

        p.setFont(QFont("Consolas", 7))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(tx, H * 0.18 + 18, tw, 14),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f"{ext_str}  ·  {size_str}")

        p.setFont(QFont("Consolas", 6))
        p.setPen(QPen(qcol("#1e5c6a"), 1))
        par = str(path.parent)
        if len(par) > 42: par = "…" + par[-41:]
        p.drawText(QRectF(tx, H * 0.18 + 34, tw, 12),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, par)

        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.RED, 180), 1))
        p.drawText(QRectF(W - 34, 0, 28, H), Qt.AlignmentFlag.AlignCenter, "✕")

    def mousePressEvent(self, e):
        z = self._z
        if z._current_file and e.pos().x() > self.width() - 34:
            z.clear_file()
        else:
            z.mousePressEvent(e)


class SetupOverlay(QWidget):
    done = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            SetupOverlay {{
                background: rgba(0, 6, 10, 245);
                border: 1px solid {C.BORDER_B};
                border-radius: 6px;
            }}
        """)

        detected = {"darwin": "mac", "windows": "windows"}.get(
            _OS.lower(), "linux"
        )
        self._sel_os = detected

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 22, 30, 22)
        layout.setSpacing(8)

        def _lbl(txt, font_size=10, bold=False, color=C.PRI,
                 align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont("Consolas", font_size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        layout.addWidget(_lbl("◈  INITIALISATION REQUIRED", 13, True))
        layout.addWidget(_lbl("Configure J.A.R.V.I.S. before first boot.", 9, color=C.PRI_DIM))
        layout.addSpacing(6)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep)
        layout.addSpacing(4)

        layout.addWidget(_lbl("GEMINI API KEY", 8, color=C.TEXT_DIM,
                               align=Qt.AlignmentFlag.AlignLeft))
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("AIza…")
        self._key_input.setFont(QFont("Consolas", 10))
        self._key_input.setFixedHeight(32)
        self._key_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d12; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        layout.addWidget(self._key_input)
        layout.addSpacing(8)

        layout.addWidget(_lbl("OPENROUTER API KEY", 8, color=C.TEXT_DIM,
                       align=Qt.AlignmentFlag.AlignLeft))
        self._or_input = QLineEdit()
        self._or_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._or_input.setPlaceholderText("sk-or-…")
        self._or_input.setFont(QFont("Consolas", 10))
        self._or_input.setFixedHeight(32)
        self._or_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d12; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.ACC2}; }}
        """)
        layout.addWidget(self._or_input)

        layout.addSpacing(12)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep2)
        layout.addSpacing(4)

        layout.addWidget(_lbl("OPERATING SYSTEM", 8, color=C.TEXT_DIM,
                               align=Qt.AlignmentFlag.AlignLeft))
        det_name = {"windows": "Windows", "mac": "macOS", "linux": "Linux"}[detected]
        layout.addWidget(_lbl(f"Auto-detected: {det_name}", 8, color=C.ACC2,
                               align=Qt.AlignmentFlag.AlignLeft))

        os_row = QHBoxLayout(); os_row.setSpacing(6)
        self._os_btns: dict[str, QPushButton] = {}
        for key, label in [("windows","⊞  Windows"),("mac","  macOS"),("linux","🐧  Linux")]:
            btn = QPushButton(label)
            btn.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._sel(k))
            os_row.addWidget(btn)
            self._os_btns[key] = btn
        layout.addLayout(os_row)
        self._sel(detected)
        layout.addSpacing(12)

        init_btn = QPushButton("▸  INITIALISE SYSTEMS")
        init_btn.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        init_btn.setFixedHeight(36)
        init_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        init_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO}; border: 1px solid {C.PRI};
            }}
        """)
        init_btn.clicked.connect(self._submit)
        layout.addWidget(init_btn)

    def _sel(self, key: str):
        self._sel_os = key
        pal = {"windows":(C.PRI,"#001a22"),"mac":(C.ACC2,"#1a1400"),"linux":(C.GREEN,"#001a0d")}
        for k, btn in self._os_btns.items():
            if k == key:
                fg, bg = pal[k]
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {fg}; color: {bg};
                        border: none; border-radius: 3px; font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: #000d12; color: {C.TEXT_DIM};
                        border: 1px solid {C.BORDER}; border-radius: 3px;
                    }}
                    QPushButton:hover {{ color: {C.TEXT}; border: 1px solid {C.BORDER_B}; }}
                """)

    def _submit(self):
        key = self._key_input.text().strip()
        or_key = self._or_input.text().strip()
        if not key:
            self._key_input.setStyleSheet(
                self._key_input.styleSheet() +
                f" QLineEdit {{ border: 1px solid {C.RED}; }}"
            )
            return
        if not or_key:
            self._or_input.setStyleSheet(
                self._or_input.styleSheet() +
                f" QLineEdit {{ border: 1px solid {C.RED}; }}"
            )
            return
        self.done.emit(key, or_key, self._sel_os)


class MainWindow(QMainWindow):
    _log_sig      = pyqtSignal(str)
    _state_sig    = pyqtSignal(str)
    _reconnect_sig = pyqtSignal()

    def __init__(self, face_path: str):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S — MARK XXXIX-OR — Dor Bareket")
        self.setMinimumSize(_MIN_W, _MIN_H)
        self.resize(_DEFAULT_W, _DEFAULT_H)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - _DEFAULT_W) // 2,
            (screen.height() - _DEFAULT_H) // 2,
        )

        self.on_text_command  = None
        self.on_reconnect     = None
        self._muted           = False
        self._current_file: str | None = None

        central = QWidget()
        central.setStyleSheet(f"background: {C.BG};")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._left_panel = self._build_left_panel()
        self._left_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        body.addWidget(self._left_panel, stretch=0)

        self.hud = HudCanvas(face_path)
        self.hud.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        body.addWidget(self.hud, stretch=6)

        self._right_panel = self._build_right_panel()
        self._right_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        body.addWidget(self._right_panel, stretch=0)

        root.addLayout(body, stretch=1)
        root.addWidget(self._build_footer())

        self._clock_tmr = QTimer(self)
        self._clock_tmr.timeout.connect(self._tick_clock)
        self._clock_tmr.start(1000)
        self._tick_clock()

        # Metrik güncelleme timer'ı
        self._metric_tmr = QTimer(self)
        self._metric_tmr.timeout.connect(self._update_metrics)
        self._metric_tmr.start(2000)
        self._update_metrics()

        self._log_sig.connect(self._log.append_log)
        self._state_sig.connect(self._apply_state)
        self._reconnect_sig.connect(self._on_reconnect_clicked)

        self._overlay: SetupOverlay | None = None
        self._ready = self._check_config()
        if not self._ready:
            self._show_setup()

        sc_mute = QShortcut(QKeySequence("F4"), self)
        sc_mute.activated.connect(self._toggle_mute)
        sc_full = QShortcut(QKeySequence("F11"), self)
        sc_full.activated.connect(self._toggle_fullscreen)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._overlay and self._overlay.isVisible():
            ow, oh = 460, 390
            cw = self.centralWidget()
            self._overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )

    def _update_metrics(self):
        snap = _metrics.snapshot()

        # CPU
        cpu = snap["cpu"]
        self._gauge_cpu.set_value(cpu, f"{cpu:.0f}%")

        # MEM
        mem = snap["mem"]
        self._gauge_mem.set_value(mem, f"{mem:.0f}%")

        # NET
        net = snap["net"]
        if net < 1.0:
            net_str = f"{net*1024:.0f}KB/s"
        else:
            net_str = f"{net:.1f}MB/s"
        net_pct = min(100, net * 10)  # 10 MB/s = %100
        self._gauge_net.set_value(net_pct, net_str)

        # GPU
        gpu = snap["gpu"]
        if gpu >= 0:
            self._gauge_gpu.set_value(gpu, f"{gpu:.0f}%")
        else:
            self._gauge_gpu.set_value(0, "N/A")

        # TMP
        tmp = snap["tmp"]
        if tmp >= 0:
            tmp_pct = min(100, (tmp / 100) * 100)
            self._gauge_tmp.set_value(tmp_pct, f"{tmp:.0f}°C")
        else:
            self._gauge_tmp.set_value(0, "N/A")

        try:
            boot_t  = psutil.boot_time()
            elapsed = time.time() - boot_t
            h = int(elapsed // 3600)
            m = int((elapsed % 3600) // 60)
            self._uptime_lbl.setText(f"UP  {h:02d}:{m:02d}")
        except Exception:
            self._uptime_lbl.setText("UP  --:--")

        try:
            proc_count = len(psutil.pids())
            self._proc_lbl.setText(f"PROC  {proc_count}")
        except Exception:
            self._proc_lbl.setText("PROC  --")


    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(54)
        w.setStyleSheet(f"background: {C.DARK}; border-bottom: 1px solid {C.BORDER_B};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)

        def _badge(txt, color=C.TEXT_MED):
            l = QLabel(txt)
            l.setFont(QFont("Consolas", 9))
            l.setStyleSheet(f"color: {color}; background: transparent;")
            return l

        lay.addWidget(_badge("MARK XXXIX-OR", C.PRI_DIM))
        lay.addStretch()

        mid = QVBoxLayout(); mid.setSpacing(1)
        title = QLabel("J.A.R.V.I.S")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Consolas", 17, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        mid.addWidget(title)
        sub = QLabel("Dor Bareket's Personal Assistant")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setFont(QFont("Consolas", 9))
        sub.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent;")
        mid.addWidget(sub)
        lay.addLayout(mid)
        lay.addStretch()

        right_col = QVBoxLayout(); right_col.setSpacing(2)
        self._clock_lbl = QLabel("00:00:00")
        self._clock_lbl.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self._clock_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        self._clock_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._clock_lbl)
        self._date_lbl = QLabel("")
        self._date_lbl.setFont(QFont("Consolas", 7))
        self._date_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._date_lbl)
        lay.addLayout(right_col)
        return w

    def _tick_clock(self):
        self._clock_lbl.setText(time.strftime("%H:%M:%S"))
        self._date_lbl.setText(time.strftime("%a %d %b %Y"))

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        w.setMinimumWidth(150)
        w.setMaximumWidth(195)
        w.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 {C.DARK}, stop:1 {C.PANEL}); "
            f"border-right: 1px solid {C.BORDER};"
        )
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 10, 8, 10)
        lay.setSpacing(6)

        hdr = QLabel("◈ SYS MONITOR")
        hdr.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; "
                          f"border-bottom: 1px solid {C.BORDER}; padding-bottom: 4px;")
        lay.addWidget(hdr)
        lay.addSpacing(2)

        self._gauge_cpu = ArcGauge("CPU", C.PRI)
        self._gauge_mem = ArcGauge("MEM", C.ACC2)
        self._gauge_net = ArcGauge("NET", C.GREEN)
        self._gauge_gpu = ArcGauge("GPU", C.ACC)
        self._gauge_tmp = ArcGauge("TMP", "#ff6688")

        gauge_grid = QGridLayout()
        gauge_grid.setSpacing(3)
        gauge_grid.setContentsMargins(0, 0, 0, 0)
        gauge_grid.addWidget(self._gauge_cpu, 0, 0)
        gauge_grid.addWidget(self._gauge_mem, 0, 1)
        gauge_grid.addWidget(self._gauge_gpu, 1, 0)
        gauge_grid.addWidget(self._gauge_net, 1, 1)
        gauge_grid.addWidget(self._gauge_tmp, 2, 0, 1, 2)
        lay.addLayout(gauge_grid)

        lay.addSpacing(4)

        info_panel = QWidget()
        info_panel.setStyleSheet(
            f"background: {C.PANEL2}; border: 1px solid {C.BORDER}; border-radius: 6px;"
        )
        ip_lay = QVBoxLayout(info_panel)
        ip_lay.setContentsMargins(6, 5, 6, 5)
        ip_lay.setSpacing(3)

        self._uptime_lbl = QLabel("UP  --:--")
        self._uptime_lbl.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self._uptime_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent; border: none;")
        ip_lay.addWidget(self._uptime_lbl)

        self._proc_lbl = QLabel("PROC  --")
        self._proc_lbl.setFont(QFont("Consolas", 9))
        self._proc_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        ip_lay.addWidget(self._proc_lbl)

        os_name = {"Windows": "WIN", "Darwin": "macOS", "Linux": "LINUX"}.get(_OS, _OS.upper())
        os_lbl = QLabel(f"OS  {os_name}")
        os_lbl.setFont(QFont("Consolas", 9))
        os_lbl.setStyleSheet(f"color: {C.ACC2}; background: transparent; border: none;")
        ip_lay.addWidget(os_lbl)

        lay.addWidget(info_panel)
        lay.addStretch()

        for txt, col in [
            ("AI CORE\nACTIVE",     C.GREEN),
            ("SEC\nCLEARED",        C.PRI),
            ("PROTOCOL\nXXXIX-OR",  C.TEXT_DIM),
        ]:
            lbl = QLabel(txt)
            lbl.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"color: {col}; background: {C.PANEL2};"
                f"border: 1px solid {C.BORDER_A}; border-radius: 6px; padding: 5px;"
            )
            lay.addWidget(lbl)

        return w
    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        w.setMinimumWidth(280)
        w.setMaximumWidth(380)
        w.setStyleSheet(
            f"background: qlineargradient(x1:1, y1:0, x2:0, y2:0, "
            f"stop:0 {C.DARK}, stop:1 {C.PANEL}); "
            f"border-left: 1px solid {C.BORDER};"
        )
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        def _sec(txt):
            l = QLabel(f"▸ {txt}")
            l.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            l.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
            return l

        lay.addWidget(_sec("ACTIVITY LOG"))
        self._log = LogWidget()
        lay.addWidget(self._log, stretch=1)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        lay.addWidget(sep)

        lay.addWidget(_sec("FILE UPLOAD"))
        self._drop_zone = FileDropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)
        lay.addWidget(self._drop_zone)

        self._file_hint = QLabel("No file loaded — drop or click above to upload")
        self._file_hint.setFont(QFont("Consolas", 9))
        self._file_hint.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        self._file_hint.setWordWrap(True)
        lay.addWidget(self._file_hint)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        lay.addWidget(sep2)

        lay.addWidget(_sec("COMMAND INPUT"))
        lay.addLayout(self._build_input_row())

        btn_row = QHBoxLayout(); btn_row.setSpacing(5)

        self._mute_btn = QPushButton("🎙  MICROPHONE ACTIVE")
        self._mute_btn.setFixedHeight(30)
        self._mute_btn.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self._mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mute_btn.clicked.connect(self._toggle_mute)
        self._style_mute_btn()
        btn_row.addWidget(self._mute_btn, stretch=3)

        self._reconnect_btn = QPushButton("↺")
        self._reconnect_btn.setFixedSize(30, 30)
        self._reconnect_btn.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        self._reconnect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reconnect_btn.setToolTip("Force reconnect to Gemini")
        self._reconnect_btn.setStyleSheet(f"""
            QPushButton {{
                background: #0a1a0a; color: {C.PRI};
                border: 1px solid {C.BORDER_B}; border-radius: 3px;
            }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; color: {C.PRI}; }}
            QPushButton:pressed {{ background: {C.PRI_GHO}; }}
        """)
        self._reconnect_btn.clicked.connect(self._on_reconnect_clicked)
        btn_row.addWidget(self._reconnect_btn, stretch=0)

        lay.addLayout(btn_row)

        fs_btn = QPushButton("⛶  FULLSCREEN  [F11]")
        fs_btn.setFixedHeight(26)
        fs_btn.setFont(QFont("Consolas", 7))
        fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fs_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px;
            }}
            QPushButton:hover {{
                color: {C.PRI}; border: 1px solid {C.BORDER_B};
            }}
        """)
        fs_btn.clicked.connect(self._toggle_fullscreen)
        lay.addWidget(fs_btn)

        return w

    def _build_input_row(self) -> QHBoxLayout:
        row = QHBoxLayout(); row.setSpacing(5)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a command or question…")
        self._input.setFont(QFont("Consolas", 10))
        self._input.setFixedHeight(30)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d14; color: {C.WHITE};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 3px 7px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        self._input.returnPressed.connect(self._send)
        row.addWidget(self._input)

        send = QPushButton("▸")
        send.setFixedSize(30, 30)
        send.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL}; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)
        send.clicked.connect(self._send)
        row.addWidget(send)
        return row

    def _build_footer(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(22)
        w.setStyleSheet(f"background: {C.DARK}; border-top: 1px solid {C.BORDER};")
        lay = QHBoxLayout(w); lay.setContentsMargins(14, 0, 14, 0)

        def _fl(txt, color=C.TEXT_MED):
            l = QLabel(txt); l.setFont(QFont("Consolas", 8))
            l.setStyleSheet(f"color: {color}; background: transparent;")
            return l

        lay.addWidget(_fl("[F4] Mute  ·  [F11] Fullscreen"))
        lay.addStretch()
        lay.addWidget(_fl("MARK XXXIX-OR  ·  PERSONAL ASSISTANT"))
        lay.addStretch()
        lay.addWidget(_fl("ONLINE", C.GREEN_D))
        return w

    def _on_file_selected(self, path: str):
        self._current_file = path
        p    = Path(path)
        cat  = _file_category(p)
        icon, _ = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size = _fmt_size(p.stat().st_size)
        self._file_hint.setText(f"{icon}  {p.name}  ·  {size}  ·  Tell JARVIS what to do with it")
        self._log.append_log(f"FILE: {p.name} ({size}) loaded")
        if self.on_text_command:
            msg = (
                f"[FILE_UPLOADED] path={path} | name={p.name} | "
                f"type={p.suffix.lstrip('.')} | size={size} | "
                f"Briefly tell the user you can see the file '{p.name}' "
                f"({size}) has been uploaded and ask what they'd like to do with it."
            )
            threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        self._style_mute_btn()
        if self._muted:
            self._apply_state("MUTED")
            self._log.append_log("SYS: Microphone muted.")
        else:
            self._apply_state("LISTENING")
            self._log.append_log("SYS: Microphone active.")

    def _style_mute_btn(self):
        if self._muted:
            self._mute_btn.setText("🔇  MICROPHONE MUTED")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #140006; color: {C.MUTED_C};
                    border: 1px solid {C.MUTED_C}; border-radius: 3px;
                }}
            """)
        else:
            self._mute_btn.setText("🎙  MICROPHONE ACTIVE")
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #00140a; color: {C.GREEN};
                    border: 1px solid {C.GREEN}; border-radius: 3px;
                }}
                QPushButton:hover {{ background: #001f10; }}
            """)

    def _on_reconnect_clicked(self):
        self._log.append_log("SYS: Reconnecting…")
        self._apply_state("THINKING")
        self._reconnect_btn.setEnabled(False)
        QTimer.singleShot(3000, lambda: self._reconnect_btn.setEnabled(True))
        if self.on_reconnect:
            threading.Thread(target=self.on_reconnect, daemon=True).start()

    def _send(self):
        txt = self._input.text().strip()
        if not txt: return
        self._input.clear()
        self._log.append_log(f"You: {txt}")
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(txt,), daemon=True).start()

    def _apply_state(self, state: str):
        self.hud.state    = state
        self.hud.speaking = (state == "SPEAKING")

    def _check_config(self) -> bool:
        if not API_FILE.exists(): return False
        try:
            d = json.loads(API_FILE.read_text(encoding="utf-8"))
            return (bool(d.get("gemini_api_key")) and
                    bool(d.get("openrouter_api_key")) and
                    bool(d.get("os_system")))
        except Exception:
            return False

    def _show_setup(self):
        ov = SetupOverlay(self.centralWidget())
        cw = self.centralWidget()
        ow, oh = 460, 430
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.done.connect(self._on_setup_done)
        ov.show()
        self._overlay = ov

    # Change signature:
    def _on_setup_done(self, key: str, or_key: str, os_name: str):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        API_FILE.write_text(
            json.dumps({
                "gemini_api_key":    key,
                "openrouter_api_key": or_key,
                "os_system":         os_name,
            }, indent=4),
            encoding="utf-8",
        )
        self._ready = True
        if self._overlay:
            self._overlay.hide()
            self._overlay = None
        self._apply_state("LISTENING")
        self._log.append_log(f"SYS: Initialised. OS={os_name.upper()}. JARVIS online.")

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
        self._win = MainWindow(face_path)
        self._win.show()
        self.root = _RootShim(self._app)

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return self._win._drop_zone.current_file()

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

    def trigger_reconnect(self):
        self._win._reconnect_sig.emit()

    def show_action(self, name: str):
        self._win.hud.show_action(name)

    def set_state(self, state: str):
        self._win._state_sig.emit(state)

    def write_log(self, text: str):
        self._win._log_sig.emit(text)

    def wait_for_api_key(self):
        while not self._win._ready:
            time.sleep(0.1)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")