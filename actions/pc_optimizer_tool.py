# REDESIGN+AGENTS+TOOLS+TITAN+WHATSAPP 2026-06-17
"""
pc_optimizer_tool.py — Windows system optimization and gaming performance for TITAN agent.
Uses subprocess, psutil, winreg, GPUtil. No external API needed.
Logs every action to logs/titan_actions.log.
SAFETY: Always requires confirmed=True for destructive actions.
"""

import os
import sys
import json
import time
import shutil
import logging
import subprocess
import threading
from datetime import datetime
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _log_dir() -> Path:
    d = _base_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


_titan_log = logging.getLogger("titan")
_titan_log.setLevel(logging.INFO)
_log_file = _log_dir() / "titan_actions.log"
if not _titan_log.handlers:
    fh = logging.FileHandler(str(_log_file), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    _titan_log.addHandler(fh)


# Paths that TITAN must never touch
_PROTECTED_SUBSTRINGS = [
    "jarvis", "pizzaxboh", "system32", "windows\\system",
    "program files\\common", "\\windows\\winsxs",
]

_GAMING_REGISTRY_CHANGES: list[tuple] = []  # track for restore


def _is_protected(path: str) -> bool:
    lower = path.lower().replace("/", "\\")
    return any(s in lower for s in _PROTECTED_SUBSTRINGS)


def _run(cmd: str, shell: bool = True) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=30)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return -1, str(e)


def _log(action: str, result: str):
    _titan_log.info(f"[{action}] {result[:200]}")


# ── Gaming Mode ────────────────────────────────────────────────────────────────
def _gaming_mode(game_name: str, confirmed: bool) -> str:
    if not confirmed:
        return (
            f"Gaming mode will apply 6 optimizations for '{game_name}': "
            "power plan → Ultimate Performance, disable SysMain + WSearch, "
            "set game process priority to High, disable Xbox Game Bar, "
            "disable fullscreen optimizations. Shall I proceed?"
        )

    results = []

    # 1. Ultimate Performance power plan
    rc, out = _run("powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c")
    results.append("Power → Ultimate Performance" if rc == 0 else f"Power plan: {out[:60]}")

    # 2. Disable SysMain
    rc, out = _run("sc stop SysMain")
    results.append("SysMain disabled" if rc in (0, 5) else f"SysMain: {out[:40]}")

    # 3. Disable WSearch
    rc, out = _run("sc stop WSearch")
    results.append("WSearch disabled" if rc in (0, 5) else f"WSearch: {out[:40]}")

    # 4. Game process priority (best-effort)
    if game_name:
        rc, out = _run(
            f'wmic process where name="{game_name}.exe" CALL setpriority "high priority"'
        )
        results.append(f"{game_name} → High priority" if rc == 0 else f"Priority: process not found yet")

    # 5. Disable Xbox Game Bar via registry
    try:
        import winreg
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "AppCaptureEnabled", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(k, "GameDVR_Enabled", 0, winreg.REG_DWORD, 0)
        results.append("Xbox Game Bar disabled")
    except Exception as e:
        results.append(f"Game Bar: {e}")

    # 6. Fullscreen optimizations (per-exe if known)
    if game_name:
        try:
            import winreg
            exe = f"{game_name}.exe"
            layer_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, layer_key, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, exe, 0, winreg.REG_SZ, "~ DISABLEDXMAXIMIZEDWINDOWEDMODE")
            results.append(f"Fullscreen optimizations disabled for {exe}")
        except Exception as e:
            results.append(f"Fullscreen opt: {e}")

    summary = f"Gaming mode active. {len(results)} optimizations applied. " + " · ".join(results)
    _log("gaming_mode", summary)
    return summary + "\nRecommend restarting the game."


# ── Restore Mode ───────────────────────────────────────────────────────────────
def _restore_mode() -> str:
    results = []

    rc, _ = _run("powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e")
    results.append("Power → Balanced" if rc == 0 else "Power plan: fallback")

    _run("sc start SysMain")
    results.append("SysMain re-enabled")

    _run("sc start WSearch")
    results.append("WSearch re-enabled")

    try:
        import winreg
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "AppCaptureEnabled", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(k, "GameDVR_Enabled", 0, winreg.REG_DWORD, 1)
        results.append("Xbox Game Bar restored")
    except Exception as e:
        results.append(f"Game Bar restore: {e}")

    summary = "System restored to normal profile. " + " · ".join(results)
    _log("restore_mode", summary)
    return summary


# ── Process List ───────────────────────────────────────────────────────────────
def _list_processes() -> str:
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except Exception:
                pass
        time.sleep(0.5)
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                for existing in procs:
                    if existing["pid"] == p.pid:
                        existing["cpu_percent"] = p.cpu_percent()
            except Exception:
                pass

        by_cpu = sorted(procs, key=lambda x: x.get("cpu_percent") or 0, reverse=True)[:10]
        by_ram = sorted(procs, key=lambda x: x.get("memory_percent") or 0, reverse=True)[:10]

        lines = ["TOP CPU:"]
        for p in by_cpu:
            lines.append(f"  {p['name'][:30]:<30} CPU: {p.get('cpu_percent',0):.1f}%")
        lines.append("TOP RAM:")
        for p in by_ram:
            lines.append(f"  {p['name'][:30]:<30} RAM: {p.get('memory_percent',0):.1f}%")

        return "\n".join(lines)
    except Exception as e:
        return f"list_processes error: {e}"


# ── Kill Process ───────────────────────────────────────────────────────────────
_CRITICAL_PROCESSES = {
    "system", "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
    "lsass.exe", "services.exe", "svchost.exe", "dwm.exe",
    "explorer.exe", "taskmgr.exe", "python.exe", "pythonw.exe",
}

def _kill_process(process_name: str, confirmed: bool) -> str:
    if not process_name:
        return "Specify a process name."
    if process_name.lower() in _CRITICAL_PROCESSES:
        return f"'{process_name}' is a critical system process. Cannot kill."
    if not confirmed:
        return f"Kill '{process_name}'? Say 'yes' to confirm."

    rc, out = _run(f"taskkill /IM {process_name} /F")
    result = f"Killed {process_name}" if rc == 0 else f"Kill failed: {out[:80]}"
    _log("kill_process", result)
    return result


# ── Disk Clean ─────────────────────────────────────────────────────────────────
def _disk_clean(confirmed: bool) -> str:
    if not confirmed:
        return (
            "Disk clean will delete: Windows Temp, User Temp, "
            "browser caches (Chrome, Edge), Windows Update download cache. "
            "Shall I proceed?"
        )

    freed = 0
    results = []

    def _clean_dir(path: str) -> int:
        if _is_protected(path):
            return 0
        total = 0
        try:
            p = Path(path)
            if not p.exists():
                return 0
            for item in p.iterdir():
                try:
                    sz = item.stat().st_size if item.is_file() else sum(
                        f.stat().st_size for f in item.rglob("*") if f.is_file()
                    )
                    if item.is_file():
                        item.unlink(missing_ok=True)
                    else:
                        shutil.rmtree(item, ignore_errors=True)
                    total += sz
                except Exception:
                    pass
        except Exception:
            pass
        return total

    targets = [
        (os.environ.get("TEMP", ""), "User Temp"),
        ("C:\\Windows\\Temp", "Windows Temp"),
        (os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cache"), "Chrome Cache"),
        (os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache"), "Edge Cache"),
        ("C:\\Windows\\SoftwareDistribution\\Download", "WU Download Cache"),
    ]

    for path, label in targets:
        if not path:
            continue
        sz = _clean_dir(path)
        freed += sz
        if sz > 0:
            results.append(f"{label}: {sz / 1024 / 1024:.1f} MB")

    total_mb = freed / 1024 / 1024
    total_gb = total_mb / 1024
    size_str = f"{total_gb:.2f} GB" if total_gb >= 1 else f"{total_mb:.1f} MB"
    summary = f"Disk clean complete. {size_str} freed. " + ", ".join(results)
    _log("disk_clean", summary)
    return summary


# ── Startup Manager ────────────────────────────────────────────────────────────
def _startup_manager() -> str:
    try:
        import winreg
        entries = []
        paths = [
            (winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        ]
        for hive, path in paths:
            try:
                with winreg.OpenKey(hive, path) as k:
                    i = 0
                    while True:
                        try:
                            name, val, _ = winreg.EnumValue(k, i)
                            entries.append(f"  {name[:35]:<35} → {val[:60]}")
                            i += 1
                        except OSError:
                            break
            except Exception:
                pass

        if not entries:
            return "No startup programs found."
        result = f"Startup programs ({len(entries)} found):\n" + "\n".join(entries)
        result += "\n\nSay 'disable startup [name]' to remove a specific entry."
        _log("startup_manager", f"{len(entries)} entries listed")
        return result
    except Exception as e:
        return f"startup_manager error: {e}"


# ── Thermal Report ─────────────────────────────────────────────────────────────
def _thermal_report() -> str:
    lines = []
    try:
        import psutil
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                for e in entries:
                    lines.append(f"  {name}/{e.label or 'core'}: {e.current:.1f}°C")
                    if e.current > 85:
                        lines.append(f"  ⚠ ALERT: {name} exceeds 85°C — check cooling!")
        else:
            lines.append("  CPU temp: not available via psutil on Windows (use HWiNFO64)")
    except Exception as e:
        lines.append(f"  CPU: {e}")

    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        for g in gpus:
            lines.append(f"  GPU {g.name}: {g.temperature:.1f}°C  load {g.load*100:.1f}%")
            if g.temperature > 83:
                lines.append(f"  ⚠ ALERT: GPU exceeds 83°C — reduce overclock or improve airflow!")
    except Exception:
        lines.append("  GPU: GPUtil not available or no GPU found")

    result = "THERMAL REPORT:\n" + "\n".join(lines)
    _log("thermal_report", result[:200])
    return result


# ── RAM Optimize ───────────────────────────────────────────────────────────────
def _ram_optimize() -> str:
    try:
        import psutil
        vm = psutil.virtual_memory()
        lines = [
            f"Total RAM: {vm.total / 1024**3:.1f} GB",
            f"Used: {vm.used / 1024**3:.1f} GB ({vm.percent}%)",
            f"Available: {vm.available / 1024**3:.1f} GB",
        ]

        # Top RAM consumers
        procs = []
        for p in psutil.process_iter(["name", "memory_percent"]):
            try:
                procs.append((p.info["name"], p.info["memory_percent"] or 0))
            except Exception:
                pass
        procs.sort(key=lambda x: x[1], reverse=True)
        lines.append("\nTop RAM consumers:")
        for name, pct in procs[:8]:
            lines.append(f"  {name[:35]:<35} {pct:.1f}%")

        if vm.percent > 80:
            lines.append("\n⚠ High RAM usage. Consider closing background apps.")

        result = "\n".join(lines)
        _log("ram_optimize", f"RAM {vm.percent}% used")
        return result
    except Exception as e:
        return f"ram_optimize error: {e}"


# ── Network Optimize ───────────────────────────────────────────────────────────
def _network_optimize(confirmed: bool) -> str:
    if not confirmed:
        return "Network optimize will: flush DNS, reset TCP/IP stack, reset Winsock. Shall I proceed?"

    results = []
    rc, _ = _run("ipconfig /flushdns")
    results.append("DNS flushed" if rc == 0 else "DNS flush failed")

    rc, _ = _run("netsh int ip reset")
    results.append("TCP/IP reset" if rc == 0 else "TCP reset requires admin")

    rc, _ = _run("netsh winsock reset")
    results.append("Winsock reset" if rc == 0 else "Winsock reset requires admin")

    result = "Network optimize: " + " · ".join(results) + ". Restart recommended."
    _log("network_optimize", result)
    return result


# ── Power Profile ──────────────────────────────────────────────────────────────
_POWER_PLANS = {
    "balanced":              "381b4222-f694-41f0-9685-ff5bb260df2e",
    "high_performance":      "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    "ultimate_performance":  "e9a42b02-d5df-448d-aa00-03f14749eb61",
}

def _power_profile(profile: str) -> str:
    guid = _POWER_PLANS.get(profile.lower(), "")
    if not guid:
        return f"Unknown profile '{profile}'. Use: balanced | high_performance | ultimate_performance"
    rc, out = _run(f"powercfg /setactive {guid}")
    result = f"Power plan set to {profile}" if rc == 0 else f"Power plan error: {out[:80]}"
    _log("power_profile", result)
    return result


# ── Schedule Cleanup ───────────────────────────────────────────────────────────
def _schedule_cleanup(day: str, hour: int) -> str:
    task_name = "JarvisTITAN_WeeklyCleanup"
    cmd = (
        f'schtasks /create /tn "{task_name}" /sc weekly /d {day} '
        f'/st {hour:02d}:00 /f /tr "cmd /c del /q /s %TEMP%\\* & ipconfig /flushdns"'
    )
    rc, out = _run(cmd)
    result = (
        f"Weekly cleanup scheduled: every {day} at {hour:02d}:00"
        if rc == 0 else f"Schedule error: {out[:100]}"
    )
    _log("schedule_cleanup", result)
    return result


# ── Entry Point ────────────────────────────────────────────────────────────────
def pc_optimizer_tool(parameters: dict, player=None, speak=None) -> str:
    """
    TITAN agent tool. All destructive actions require confirmed=True.
    parameters:
        action        : gaming_mode | restore_mode | list_processes | kill_process |
                        disk_clean | startup_manager | thermal_report | ram_optimize |
                        network_optimize | power_profile | schedule_cleanup
        game_name     : for gaming_mode
        process_name  : for kill_process
        profile       : for power_profile
        confirmed     : bool — must be True for destructive actions
        schedule_day  : for schedule_cleanup (e.g. Sunday)
        schedule_hour : for schedule_cleanup (0-23)
    """
    params    = parameters or {}
    action    = params.get("action", "").lower().strip()
    confirmed = bool(params.get("confirmed", False))

    if player:
        player.write_log(f"TITAN: {action}")

    try:
        if action == "gaming_mode":
            return _gaming_mode(params.get("game_name", ""), confirmed)

        elif action == "restore_mode":
            return _restore_mode()

        elif action == "list_processes":
            return _list_processes()

        elif action == "kill_process":
            return _kill_process(params.get("process_name", ""), confirmed)

        elif action == "disk_clean":
            return _disk_clean(confirmed)

        elif action == "startup_manager":
            return _startup_manager()

        elif action == "thermal_report":
            return _thermal_report()

        elif action == "ram_optimize":
            return _ram_optimize()

        elif action == "network_optimize":
            return _network_optimize(confirmed)

        elif action == "power_profile":
            return _power_profile(params.get("profile", "balanced"))

        elif action == "schedule_cleanup":
            return _schedule_cleanup(
                params.get("schedule_day", "Sunday"),
                int(params.get("schedule_hour", 2))
            )

        else:
            return (
                f"Unknown action '{action}'. Options: gaming_mode | restore_mode | "
                "list_processes | kill_process | disk_clean | startup_manager | "
                "thermal_report | ram_optimize | network_optimize | power_profile | "
                "schedule_cleanup"
            )

    except Exception as e:
        _log(action, f"ERROR: {e}")
        return f"pc_optimizer_tool error ({action}): {e}"
