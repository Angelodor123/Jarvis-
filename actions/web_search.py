#web_search.py
import json
import sys
import time
from pathlib import Path

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _gemini_search(query: str) -> str:
    from google import genai

    client   = genai.Client(api_key=_get_api_key())
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=query,
        config={"tools": [{"google_search": {}}]},
    )

    text = ""
    for part in response.candidates[0].content.parts:
        if hasattr(part, "text") and part.text:
            text += part.text

    text = text.strip()
    if not text:
        raise ValueError("Gemini returned an empty response.")
    return text


def _chrome_search(query: str, max_chars: int = 4000) -> str:
    """Fallback web search that drives the real Google Chrome browser
    (via actions.browser_control / Playwright) instead of scraping DDG."""
    from actions.browser_control import browser_control

    browser_control({"action": "search", "query": query, "engine": "google"})
    time.sleep(1.5)  # let the results render before scraping text
    text = (browser_control({"action": "get_text"}) or "").strip()
    return text[:max_chars] if text else f"No results found for: {query}"

def _compare(items: list[str], aspect: str) -> str:
    query = (
        f"Compare {', '.join(items)} in terms of {aspect}. "
        "Give specific facts and data."
    )
    try:
        return _gemini_search(query)
    except Exception as e:
        print(f"[WebSearch] ⚠️ Gemini compare failed: {e} — falling back to Chrome search")

    # Chrome fallback: fetch a results snippet per item and merge
    all_results: dict[str, str] = {}
    for item in items:
        try:
            all_results[item] = _chrome_search(f"{item} {aspect}", max_chars=600)
        except Exception:
            all_results[item] = ""

    lines = [f"Comparison — {aspect.upper()}", "─" * 40]
    for item in items:
        lines.append(f"\n▸ {item}")
        snippet = all_results.get(item, "")
        if snippet:
            lines.append(f"  • {snippet[:300]}")
    return "\n".join(lines)

def web_search(
    parameters:     dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params = parameters or {}
    query  = params.get("query", "").strip()
    mode   = params.get("mode",  "search").lower().strip()
    items  = params.get("items", [])
    aspect = params.get("aspect", "general").strip() or "general"

    if not query and not items:
        return "Please provide a search query, sir."

    if items and mode != "compare":
        mode = "compare"

    if player:
        player.write_log(f"[Search] {query or ', '.join(items)}")

    print(f"[WebSearch] 🔍 Query: {query!r}  Mode: {mode}")
# replace: result = _gemini_search(query) block with:
    try:
        from or_client import client
        result = client.chat(
            query,
            system="You are a web search assistant. Answer factually and concisely."
        )
        print("[WebSearch] ✅ OpenRouter OK.")
        return result
    except Exception as e:
        print(f"[WebSearch] ⚠️ OpenRouter failed ({e}) — trying Chrome search...")
        result = _chrome_search(query)
        print("[WebSearch] ✅ Chrome search complete.")
        return result
    
    except Exception as e:
        print(f"[WebSearch] ❌ All backends failed: {e}")
        return f"Search failed, sir: {e}"