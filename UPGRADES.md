# MARK XXXIX-OR — Upgrade Patch Notes

## What Changed

### 1. `core/prompt.txt` — Business Context Injection
JARVIS now knows who you are and what you run:
- Pizza X (supplier comms, recipe management, ops)
- Discord bots (Deal or No Deal, 2,000-member card community)
- Lovable web apps
- TCG investing (Pokémon + sports cards)
- Personal context (Modiin, Israel; powerlifting; 3 daughters; Sun Conure)

Ambiguous commands now route to the correct business context automatically.

### 2. `memory/memory_manager.py` — Expanded Memory
- `MEMORY_MAX_CHARS` raised from 2,200 → 6,000 characters
- Added `business_context` as a new memory category alongside identity, preferences, projects, etc.
- Prevents aggressive trimming of multi-project context mid-session

### 3. `agent/executor.py` — Code Execution Security Gate
- `_run_generated_code()` now requires explicit verbal confirmation before running
- JARVIS announces what code it will run and waits for "confirmed"
- Prevents silent arbitrary code execution on your machine

### 4. `agent/planner.py` — Expanded Planning Capacity
- Step limit raised from 5 → 8 steps
- Planner now aware that executor injects web_search results into subsequent file_controller writes
- Enables richer multi-source research → save workflows

### 5. `or_client.py` — Tiered Model Fallback Chain
- TEXT_MODELS reorganized into 3 tiers:
  - Tier 1: DeepSeek R1, Qwen3-235B, Nemotron-Super-120B, Llama-3.3-70B
  - Tier 2: Qwen3-80B, Gemma-4, Hermes-3-405B
  - Tier 3: All original lightweight fallbacks preserved
- Best available models attempted first, full fallback chain maintained

### 6. `requirements.txt` — Fixed Encoding + Added Missing Dep
- Was UTF-16 encoded (broke `pip install -r requirements.txt` on all systems)
- Now clean UTF-8
- Added missing `PyQt6` dependency (required by ui.py, absent from original)

## What Was NOT Changed
- `main.py` — core Gemini Live voice loop untouched
- `ui.py` — UI unchanged
- All `actions/` modules — untouched
- `or_client.py` client logic — only model list updated

## How to Deploy
Replace the original `Mark-XXXIX-OR-main` folder with `Mark-XXXIX-OR-UPGRADED`.
Run `pip install -r requirements.txt` again to pick up PyQt6.
Then run `python main.py` as normal.

### 7. Voice Profile Switching (NEW)
- `config/voice_profile.json` stores your selected voice + descriptions of all 8 options
- New `set_voice_profile` tool: say "switch to Kore" / "use a different voice" / "sound more energetic"
- JARVIS confirms in the current voice, then auto-reconnects (~0.5s) with the new voice active
- Available voices: Puck (energetic), Charon (deep/calm — default), Kore (firm/professional),
  Fenrir (expressive), Aoede (breezy), Leda (youthful), Orus (authoritative), Zephyr (bright)
- Persists across restarts — no need to reconfigure each session

### 8. Google Calendar + Gmail Integration (NEW)
- New `actions/calendar_email.py` module using official Google APIs (OAuth2)
- New `calendar_email` tool: list_events, create_event, delete_event, list_unread, search_email, send_email
- One-time setup required — see `SETUP_CALENDAR_EMAIL.md`
- Example: "What's on my calendar this week?", "Schedule a supplier call tomorrow at 2pm",
  "Do I have unread emails?", "Send an email to..."
- Gracefully degrades to a setup-instructions message if credentials aren't configured yet

### 9. CardLadder + Collectr Portfolio Tracker (NEW)
- New `actions/portfolio_tracker.py` — checks your sports card portfolio (CardLadder)
  and sealed Pokemon/TCG portfolio (Collectr)
- Uses a PERSISTENT Chrome profile (`%LOCALAPPDATA%\\JarvisChromeProfile`) separate from
  your daily browser — log in ONCE manually, JARVIS reuses the session afterward
- Example: "Check my CardLadder portfolio", "What's my Collectr value?", "Check both portfolios"
- If not logged in, JARVIS opens the login page and tells you to sign in once

### 10. Local STT/TTS Degraded Mode (NEW)
- New `actions/local_stt.py` — offline fallback using faster-whisper (local STT) + pyttsx3 (local TTS)
- If Gemini Live fails to reconnect 3 times in a row, JARVIS enters DEGRADED MODE:
  - Records via local mic, transcribes offline with Whisper
  - Routes the question through OpenRouter (no tool access in this mode)
  - Speaks the answer via offline TTS
  - Keeps retrying Gemini Live in the background every ~5s
- Whisper model lazy-loads only when degraded mode actually triggers (zero cost otherwise)

### 11. Security & Config
- Added `.gitignore` to protect `config/api_keys.json`, `config/google_credentials.json`,
  `config/google_token.json`, and runtime memory/profile data
- Added `config/api_keys.json.example` as a template

## Updated Dependencies
Added to requirements.txt:
- google-api-python-client, google-auth-httplib2, google-auth-oauthlib (Calendar/Gmail)
- faster-whisper, pyttsx3 (degraded mode)

### 12. Visual Refinements
- Reduced grid-dot density and opacity for less visual noise
- Calmer pulse-ring/particle rate when idle (not speaking)
- Gradient backgrounds on left/right panels for depth
- Rounded corners increased (4px → 6px) across info panels, status badges, log, input
- Activity log font bumped to 10pt with improved line-height/padding
- Fixed stale "PROTOCOL XXXVIII" badge → "PROTOCOL XXXIX-OR"
- Replaced "FatihMakes Industries / STARK INDUSTRIES" branding with neutral
  "MARK XXXIX-OR · PERSONAL ASSISTANT" + live "ONLINE" status indicator
- Side panels now resize within a sensible range (left: 130-170px, right: 280-380px)
  instead of fixed width, HUD canvas gets more space on wider windows

### 13. Personalization — Dor Bareket
- All references to the original creator (FatihMakes, MARK XXV) removed from
  readme.md, or_client.py, agent/planner.py, agent/error_handler.py,
  actions/open_app.py, setup.py
- Window title, header subtitle, and footer now reflect "Dor Bareket's
  Personal Assistant"
- System prompt explicitly identifies the owner as Dor Bareket; JARVIS may
  address him as "sir" (classic style) or "Dor"
- memory/long_term.json pre-seeded with identity (name, location, businesses)
  so JARVIS knows you from first boot — gitignored thereafter since it
  accumulates personal data during use
- readme.md license/credits section rewritten to reflect personal ownership,
  removed YouTube/Instagram links and clone URL pointing to original creator
