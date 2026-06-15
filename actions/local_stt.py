"""
local_stt.py
─────────────────────────────────────────────────────────────────────────────
Local speech-to-text fallback for when the Gemini Live connection is down
(quota exhausted, network issue, etc).

Uses faster-whisper (CTranslate2-based Whisper) running fully offline on CPU.
This is NOT a replacement for the real-time Gemini Live voice loop — it's an
emergency fallback so basic voice commands still work when Gemini is
unavailable.

How it's used:
  - main.py's reconnect loop, after N consecutive failed reconnect attempts,
    can drop into "degraded mode" using this module.
  - In degraded mode: records a short clip on command (push-to-talk via UI),
    transcribes locally, routes the text through OpenRouter (or_client) for
    a response, and speaks it back using local TTS (pyttsx3).

Model size:
  "base" (~150MB) offers a good speed/accuracy tradeoff for command-style
  speech. "small" is more accurate but slower on CPU.
"""

import queue
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

MODEL_SIZE      = "base"   # tiny | base | small | medium
SAMPLE_RATE     = 16000
SILENCE_THRESH  = 0.01      # RMS amplitude below this = silence
SILENCE_DURATION = 1.2      # seconds of silence before stopping recording
MAX_RECORD_SECS = 15


class LocalSTT:
    """Lazy-loads faster-whisper model on first use to avoid startup cost
    when Gemini Live is working fine (the common case)."""

    def __init__(self):
        self._model = None
        self._lock  = threading.Lock()

    def _ensure_model(self):
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            from faster_whisper import WhisperModel
            print(f"[LocalSTT] Loading Whisper '{MODEL_SIZE}' model (CPU)...")
            self._model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
            print("[LocalSTT] Model loaded.")

    def record_until_silence(self) -> np.ndarray:
        """Records audio from the default mic until silence is detected
        or MAX_RECORD_SECS is reached. Returns float32 mono samples."""
        q: queue.Queue = queue.Queue()

        def callback(indata, frames, time_info, status):
            q.put(indata.copy())

        frames = []
        silence_start = None
        start = time.time()

        with sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32",
            blocksize=1024, callback=callback,
        ):
            while True:
                try:
                    chunk = q.get(timeout=0.5)
                except queue.Empty:
                    continue

                frames.append(chunk)
                rms = float(np.sqrt(np.mean(chunk ** 2)))

                if rms < SILENCE_THRESH:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > SILENCE_DURATION and len(frames) > 5:
                        break
                else:
                    silence_start = None

                if time.time() - start > MAX_RECORD_SECS:
                    break

        if not frames:
            return np.array([], dtype=np.float32)

        return np.concatenate(frames, axis=0).flatten()

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        self._ensure_model()
        segments, _ = self._model.transcribe(audio, language=None, beam_size=1)
        return " ".join(seg.text.strip() for seg in segments).strip()

    def listen_and_transcribe(self) -> str:
        """Convenience: record until silence, then transcribe."""
        audio = self.record_until_silence()
        return self.transcribe(audio)


# ── Local TTS (offline response, used in degraded mode) ────────────────────

class LocalTTS:
    """Wraps pyttsx3 for fully offline text-to-speech, used only when
    Gemini Live audio output is unavailable."""

    def __init__(self):
        self._engine = None

    def _ensure_engine(self):
        if self._engine is not None:
            return
        import pyttsx3
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", 175)

    def speak(self, text: str):
        if not text:
            return
        self._ensure_engine()
        self._engine.say(text)
        self._engine.runAndWait()


# ── Degraded-mode conversational loop ───────────────────────────────────────

def degraded_mode_respond(user_text: str) -> str:
    """
    Routes a transcribed command through OpenRouter for a response when
    Gemini Live is unavailable. Uses the same model pool as or_client.

    Note: this does NOT have tool-calling — it's a text-only fallback for
    simple Q&A and quick advice while Gemini reconnects.
    """
    try:
        from or_client import client
        return client.chat(
            user_text,
            system=(
                "You are JARVIS running in DEGRADED MODE (primary voice AI is "
                "temporarily unavailable, this is a local offline fallback). "
                "Be extremely concise — 1-2 sentences. You cannot control the "
                "computer or call tools right now, only answer questions or "
                "give quick advice. If the user asks you to do an action, tell "
                "them you'll perform it once the main system reconnects."
            ),
            max_tokens=150,
        )
    except Exception as e:
        return f"Degraded mode also unavailable: {e}"


_stt = LocalSTT()
_tts = LocalTTS()


def run_degraded_turn() -> tuple[str, str]:
    """One full turn in degraded mode: listen, transcribe, respond, speak.
    Returns (user_text, response_text) for logging."""
    user_text = _stt.listen_and_transcribe()
    if not user_text:
        return "", ""

    response = degraded_mode_respond(user_text)
    _tts.speak(response)
    return user_text, response
