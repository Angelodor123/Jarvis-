# REDESIGN+AGENTS+TOOLS+TITAN+WHATSAPP 2026-06-17
"""
send_message.py — Universal messaging with WhatsApp Hebrew translation + approval flow.
Platforms: WhatsApp | Instagram | Telegram | any Windows app.
Hebrew flow: detect contact in hebrew_contacts.json OR user said "translate/Hebrew"
→ translate via Gemini → speak translation → wait for voice approval → send.
"""

import json
import sys
import time
import pyautogui
from pathlib import Path

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.08


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _load_hebrew_contacts() -> list[str]:
    path = _base_dir() / "config" / "hebrew_contacts.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [c.lower().strip() for c in data.get("contacts", [])]
    except Exception:
        return []


def _add_hebrew_contact(name: str) -> str:
    path = _base_dir() / "config" / "hebrew_contacts.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"contacts": []}
        contacts = data.get("contacts", [])
        if name.strip() not in contacts:
            contacts.append(name.strip())
            data["contacts"] = contacts
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"Added {name} to Hebrew contacts."
    except Exception as e:
        return f"Could not update Hebrew contacts: {e}"


def _translate_to_hebrew(text: str, api_key: str) -> str:
    """Call Gemini to translate text to Hebrew."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = (
            "Translate this WhatsApp message to Hebrew. "
            "Use natural, conversational tone. No formal language. No transliteration. "
            "Return only the translated text, nothing else.\n"
            f"Message: {text}"
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"[Translation error: {e}]"


def _load_api_key() -> str:
    path = _base_dir() / "config" / "api_keys.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for k in ("gemini_api_key", "google_api_key", "api_key"):
            v = data.get(k, "").strip()
            if v:
                return v
    except Exception:
        pass
    return ""


def _open_app(app_name: str) -> bool:
    try:
        pyautogui.press("win")
        time.sleep(0.4)
        pyautogui.write(app_name, interval=0.04)
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(2.0)
        return True
    except Exception as e:
        print(f"[SendMessage] Could not open {app_name}: {e}")
        return False


def _send_whatsapp(receiver: str, message: str) -> str:
    try:
        if not _open_app("WhatsApp"):
            return "Could not open WhatsApp."
        time.sleep(1.5)
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.4)
        pyautogui.hotkey("ctrl", "a")
        pyautogui.write(receiver, interval=0.04)
        time.sleep(1.0)
        pyautogui.press("enter")
        time.sleep(0.8)
        pyautogui.write(message, interval=0.03)
        time.sleep(0.2)
        pyautogui.press("enter")
        return f"Message sent to {receiver} via WhatsApp."
    except Exception as e:
        return f"WhatsApp error: {e}"


def _send_instagram(receiver: str, message: str) -> str:
    try:
        import webbrowser
        webbrowser.open("https://www.instagram.com/direct/new/")
        time.sleep(3.5)
        pyautogui.write(receiver, interval=0.05)
        time.sleep(1.5)
        pyautogui.press("down")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.5)
        for _ in range(3):
            pyautogui.press("tab")
            time.sleep(0.1)
        pyautogui.press("enter")
        time.sleep(1.5)
        pyautogui.write(message, interval=0.04)
        time.sleep(0.2)
        pyautogui.press("enter")
        return f"Message sent to {receiver} via Instagram."
    except Exception as e:
        return f"Instagram error: {e}"


def _send_telegram(receiver: str, message: str) -> str:
    try:
        if not _open_app("Telegram"):
            return "Could not open Telegram."
        time.sleep(1.5)
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.4)
        pyautogui.write(receiver, interval=0.04)
        time.sleep(1.0)
        pyautogui.press("enter")
        time.sleep(0.8)
        pyautogui.write(message, interval=0.03)
        time.sleep(0.2)
        pyautogui.press("enter")
        return f"Message sent to {receiver} via Telegram."
    except Exception as e:
        return f"Telegram error: {e}"


def _send_generic(platform: str, receiver: str, message: str) -> str:
    try:
        if not _open_app(platform):
            return f"Could not open {platform}."
        time.sleep(1.5)
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.4)
        pyautogui.write(receiver, interval=0.04)
        time.sleep(1.0)
        pyautogui.press("enter")
        time.sleep(0.8)
        pyautogui.write(message, interval=0.03)
        time.sleep(0.2)
        pyautogui.press("enter")
        return f"Message sent to {receiver} via {platform}."
    except Exception as e:
        return f"{platform} error: {e}"


# Hebrew approval keywords
_HE_APPROVE = {"yes", "send", "confirm", "approved", "go ahead", "do it",
               "כן", "שלח", "בסדר", "אישור", "תשלח"}
_HE_REJECT  = {"no", "cancel", "stop", "wait", "hold on", "change it",
               "לא", "בטל", "עצור", "רגע"}


def _needs_hebrew_flow(receiver: str, message_text: str) -> bool:
    """Return True if we should run the Hebrew translation + approval flow."""
    hebrew_contacts = _load_hebrew_contacts()
    if receiver.lower() in hebrew_contacts:
        return True
    triggers = ["in hebrew", "translate", "בעברית", "תרגם"]
    lower_msg = message_text.lower()
    return any(t in lower_msg for t in triggers)


def send_message(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    """
    Called from main.py.

    parameters:
        receiver          : Contact name
        message_text      : Message content
        platform          : whatsapp | instagram | telegram | <any app>  (default: whatsapp)
        hebrew_approved   : True = user already approved Hebrew translation, proceed with send
        original_text     : Stored original before translation (passed back on approval call)
        hebrew_text       : Stored Hebrew translation (passed back on approval call)
        add_hebrew_contact: If set, add this name to hebrew_contacts.json
    """
    params   = parameters or {}
    receiver = params.get("receiver", "").strip()
    message_text = params.get("message_text", "").strip()
    platform = params.get("platform", "whatsapp").strip().lower()

    # Handle "add to Hebrew contacts" shortcut
    add_contact = params.get("add_hebrew_contact", "").strip()
    if add_contact:
        result = _add_hebrew_contact(add_contact)
        if player:
            player.write_log(f"ORACLE: {result}")
        return result

    if not receiver:
        return "Please specify who to send the message to, sir."
    if not message_text:
        return "Please specify what message to send, sir."

    is_whatsapp = "whatsapp" in platform or "wp" in platform or "wapp" in platform

    # ── Hebrew flow (WhatsApp only) ────────────────────────────────────────────
    if is_whatsapp and _needs_hebrew_flow(receiver, message_text):

        # Step 2a: If already approved, use stored hebrew_text and send
        if params.get("hebrew_approved"):
            hebrew_text = params.get("hebrew_text", message_text)
            result = _send_whatsapp(receiver, hebrew_text)
            if player:
                player.write_log(f"ORACLE: WhatsApp → {receiver} [HE] ✓")
            return f"Sent to {receiver} in Hebrew."

        # Step 2b: Translate
        api_key = _load_api_key()
        hebrew_text = _translate_to_hebrew(message_text, api_key) if api_key else message_text

        if player:
            player.write_log(f"ORACLE: Translated for {receiver}: {hebrew_text[:60]}")

        # Step 3: Return approval request so Jarvis speaks it and waits
        # The tool returns a special marker; main.py must handle confirmation loop.
        # We embed the hebrew_text in the result so Gemini can pass it back.
        return (
            f"HEBREW_APPROVAL_REQUIRED|receiver={receiver}|"
            f"hebrew_text={hebrew_text}|platform={platform}\n"
            f"Here is the message for {receiver} in Hebrew:\n"
            f"{hebrew_text}\n"
            f"Shall I send it?"
        )

    # ── Normal send ────────────────────────────────────────────────────────────
    print(f"[SendMessage] 📨 {platform} → {receiver}: {message_text[:40]}")
    if player:
        player.write_log(f"[msg] Sending to {receiver} via {platform}...")

    if is_whatsapp:
        result = _send_whatsapp(receiver, message_text)
    elif "instagram" in platform or "ig" in platform or "insta" in platform:
        result = _send_instagram(receiver, message_text)
    elif "telegram" in platform or "tg" in platform:
        result = _send_telegram(receiver, message_text)
    else:
        result = _send_generic(platform, receiver, message_text)

    print(f"[SendMessage] ✅ {result}")
    if player:
        player.write_log(f"[msg] {result}")
    return result
