"""
portfolio_tracker.py
─────────────────────────────────────────────────────────────────────────────
Checks CardLadder (sports cards) and Collectr (sealed Pokémon / TCG) portfolio
values by driving a PERSISTENT Chrome profile via Playwright.

Why persistent profile:
  CardLadder and Collectr require a logged-in session. A fresh Playwright
  context has no cookies, so it would hit a login wall every time. By pointing
  Playwright at a dedicated Chrome user-data-dir (separate from your daily
  browsing profile, but where you've logged into these sites ONCE manually),
  the session persists across runs — JARVIS reuses your existing login.

First-time setup (one-time, manual):
  1. JARVIS will launch a visible Chrome window on first call.
  2. Log into cardladder.com and collectr.app normally in that window.
  3. Close it. JARVIS will reuse this profile on every future call.

Profile location:
  %LOCALAPPDATA%\\JarvisChromeProfile  (Windows)
  ~/.jarvis_chrome_profile             (Mac/Linux)
"""

import asyncio
import os
import platform
import re
import sys
import threading
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


def _profile_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "JarvisChromeProfile"
    return Path.home() / ".jarvis_chrome_profile"


CARDLADDER_URL = "https://cardladder.com/portfolio"
COLLECTR_URL   = "https://app.collectr.com/portfolio"


class _PortfolioThread:
    """Runs a persistent Chrome context on its own event loop / thread."""

    def __init__(self):
        self._loop       = None
        self._thread     = None
        self._ready      = threading.Event()
        self._playwright = None
        self._context    = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="PortfolioThread")
        self._thread.start()
        self._ready.wait(timeout=15)

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._init())
        self._ready.set()
        self._loop.run_forever()

    async def _init(self):
        self._playwright = await async_playwright().start()

    def run(self, coro, timeout: int = 60):
        if not self._loop:
            raise RuntimeError("PortfolioThread not started.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    async def _ensure_context(self):
        if self._context:
            return self._context

        profile_dir = _profile_dir()
        profile_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,
                channel="chrome",
                viewport=None,
                args=["--start-maximized"],
            )
        except Exception:
            # Fallback to bundled chromium if real Chrome isn't found
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,
                viewport=None,
                args=["--start-maximized"],
            )
        return self._context

    async def _get_page(self, url: str):
        for attempt in range(2):
            try:
                ctx = await self._ensure_context()
                page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                return page
            except Exception as e:
                print(f"[Portfolio] Browser error (attempt {attempt + 1}): {e}")
                # Context is dead — tear it down and let _ensure_context rebuild
                if self._context:
                    try:
                        await self._context.close()
                    except Exception:
                        pass
                    self._context = None
                if attempt >= 1:
                    raise
        raise RuntimeError("Could not open browser page after retrying.")

    async def cardladder_summary(self) -> str:
        page = await self._get_page(CARDLADDER_URL)

        # Allow client-side rendering to settle
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeout:
            pass

        # Check for login wall
        url_now = page.url
        if "login" in url_now.lower() or "sign-in" in url_now.lower():
            return (
                "CardLadder requires login. A Chrome window is open — "
                "please log in to cardladder.com, then ask me again."
            )

        text = await page.inner_text("body")
        return _extract_portfolio_numbers(text, source="CardLadder")

    async def collectr_summary(self) -> str:
        page = await self._get_page(COLLECTR_URL)

        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeout:
            pass

        url_now = page.url
        if "login" in url_now.lower() or "sign-in" in url_now.lower() or "auth" in url_now.lower():
            return (
                "Collectr requires login. A Chrome window is open — "
                "please log in to app.collectr.com, then ask me again."
            )

        text = await page.inner_text("body")
        return _extract_portfolio_numbers(text, source="Collectr")

    async def close(self):
        if self._context:
            await self._context.close()
            self._context = None


def _extract_portfolio_numbers(page_text: str, source: str) -> str:
    """
    Heuristically pulls dollar-amount figures and percentage changes from the
    rendered page text. Both CardLadder and Collectr render portfolio totals
    as large $ figures near the top of the page, often with a % change.
    """
    # Find all dollar amounts like $12,345.67 or $1,234
    dollar_matches = re.findall(r"\$[\d,]+(?:\.\d{1,2})?", page_text)
    pct_matches    = re.findall(r"[+-]?\d{1,3}(?:\.\d{1,2})?%", page_text)

    if not dollar_matches:
        return (
            f"{source}: Page loaded but no portfolio value could be detected. "
            f"The page layout may have changed — try asking me to screenshot it instead."
        )

    # Largest dollar figure is usually the total portfolio value
    def _to_float(s: str) -> float:
        return float(s.replace("$", "").replace(",", ""))

    sorted_vals = sorted(set(dollar_matches), key=_to_float, reverse=True)
    top_value   = sorted_vals[0]

    summary = f"{source} portfolio value: {top_value}"
    if pct_matches:
        # Take the first percentage as the likely day/period change
        summary += f" ({pct_matches[0]} change)"

    return summary


# ── Singleton ──────────────────────────────────────────────────────────────

_pt         = _PortfolioThread()
_pt_started = False
_pt_lock    = threading.Lock()


def _ensure_started():
    global _pt_started
    with _pt_lock:
        if not _pt_started:
            _pt.start()
            _pt_started = True


def portfolio_tracker(parameters: dict, player=None, speak=None) -> str:
    """
    parameters:
        platform : "cardladder" | "collectr" | "both" (default: both)
        close    : bool — close the browser context when done (default: False)
    """
    _ensure_started()

    plat  = (parameters or {}).get("platform", "both").lower().strip()
    close = (parameters or {}).get("close", False)

    results = []
    try:
        if plat in ("cardladder", "both", "sports", "sport"):
            results.append(_pt.run(_pt.cardladder_summary(), timeout=60))

        if plat in ("collectr", "both", "pokemon", "tcg", "sealed"):
            results.append(_pt.run(_pt.collectr_summary(), timeout=60))

        if not results:
            results.append(f"Unknown platform '{plat}'. Use cardladder, collectr, or both.")

        if close:
            _pt.run(_pt.close(), timeout=15)

    except Exception as e:
        results.append(f"Portfolio check failed: {e}")

    result = "\n".join(results)
    print(f"[Portfolio] {result[:120]}")
    if player:
        player.write_log(f"[portfolio] {result[:100]}")

    return result
