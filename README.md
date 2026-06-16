# 🤖 MARK XXXIX-OR (39)
### Dor Bareket's Personal AI Assistant

A real-time voice AI inspired by Iron Man's J.A.R.V.I.S — it hears you, sees your screen, and controls your computer. Built for Windows. Local execution. Zero subscriptions.

---

## ✨ Overview

MARK XXXIX-OR bridges the gap between human intent and computer action. Through natural voice dialogue, it analyzes your screen, processes documents, tracks your portfolios, controls your browser, and executes complex workflows — all wrapped in a custom Iron Man-style HUD interface.

It's not just an assistant — it's an extension of your digital life.

---

## 🚀 Capabilities

### Core Features
| Feature | Description |
|---|---|
| 🎙️ Real-time Voice | Ultra-low latency conversation powered by Gemini Live API |
| 🖥️ Computer Control | Mouse, keyboard, hotkeys, window focus, screenshots |
| 🧩 Autonomous Tasks | Multi-step planning and execution via tool-calling |
| 👁️ Visual Awareness | Real-time screen and webcam capture sent to Gemini |
| 🧠 Persistent Memory | Remembers your identity, projects, and preferences across sessions |
| 📈 Portfolio Tracking | Live CardLadder (sports cards) and Collectr (TCG) portfolio values |
| 📅 Calendar & Email | Google Calendar and Gmail integration via OAuth |
| 🌐 Web Search | DuckDuckGo search with LLM-summarized results |
| 🎬 YouTube | Transcript fetching and video summarization |
| 🛫 Flight Finder | Real-time flight search via browser automation |
| 🔔 Reminders | Local reminder scheduling and delivery |
| 💬 Messaging | Automated Discord and other messaging actions |

---

## 🎨 HUD Interface

The UI is built in PyQt6 and designed to look and feel like Tony Stark's interface:

- **Iron Man Arc Reactor Core** — a pulsing radial glow behind the face photo that breathes with Jarvis's state (dim when listening, bright when speaking)
- **7-Layer Concentric Ring System** — outer decorative rings, three main spinning arc rings, and two inner rings — each at different speeds and opacities
- **Circular Arc Gauges** — CPU, MEM, GPU, NET, and TMP displayed as glowing 270° progress rings with color shifts as load increases (cyan → orange → red)
- **Action Overlays** — when Jarvis executes a tool (screenshot, web search, browser control, etc.), a matching Iron Man-style visual animation appears on the HUD canvas
- **Hexagonal Dot Grid Background** — proper hex-offset dot grid replacing the plain square grid
- **Reconnect Button** — manual `↺` button to force a new Gemini session if Jarvis stops responding
- **Auto-Watchdog** — automatically reconnects after 90 seconds of silence

---

## 🆕 Recent Upgrades

- 🔁 **Session Reliability** — removed unsupported `session_resumption` config that caused 1008 WebSocket disconnects; added 90s auto-watchdog and manual reconnect button
- 🌐 **OpenRouter Resilience** — dead models (404/400) are blacklisted for the session on first failure; confirmed-working models promoted to the top of the fallback chain
- 📸 **Screenshot Fix** — replaced `Win+Shift+S` hotkey (which opened Snipping Tool UI) with `pyautogui.screenshot()` for reliable direct saves to Desktop
- 🖥️ **Browser Automation Recovery** — portfolio tracker now auto-recovers when the Chrome window is manually closed, re-opening a fresh context instead of crashing
- 🚀 **Silent Launch** — `start_jarvis_silent.vbs` launches Jarvis with no console window; supports Windows Startup folder for auto-launch on boot
- 🔤 **Readability** — switched from Courier New to Consolas throughout, increased all font sizes

---

## ⚡ Quick Start

```bash
git clone https://github.com/Angelodor123/Jarvis-.git
cd Jarvis-
pip install -r requirements.txt
playwright install
python main.py
```

To launch silently (no console window), double-click `start_jarvis_silent.vbs`.  
See `LAUNCHING.md` for desktop shortcut, taskbar pin, and auto-start on boot setup.

> ⚠️ **Note:** Some OS-specific packages may not be in `requirements.txt`. If you hit a `ModuleNotFoundError`, run `pip install <module_name>`.

---

## 📋 Requirements

| Requirement | Details |
|---|---|
| **OS** | Windows 10/11 (primary), macOS/Linux partial support |
| **Python** | 3.11, 3.12, or 3.13 |
| **Microphone** | Required for voice interaction |
| **Gemini API Key** | Free — [aistudio.google.com](https://aistudio.google.com) |
| **OpenRouter API Key** | Free — [openrouter.ai](https://openrouter.ai) |
| **Chrome** | Required for browser automation (portfolio, flights) |

---

## ⚠️ License

Personal use. This is Dor Bareket's private JARVIS-style assistant —
configured for Pizza X operations, Discord/community automation, Lovable projects, and TCG portfolio management.

---

## 👤 Owner

**Dor Bareket**  
Built for daily use across Pizza X, TCG investing (CardLadder + Collectr) and general life automation 💪
```

Copy-paste that into your `README.md`. Once you save it, let me know and I'll commit + push it.
