# REDESIGN+AGENTS+TOOLS 2026-06-16
"""
canva_tool.py — Canva browser automation for VECTOR agent.
Uses Playwright with the persistent JarvisChromeProfile (same profile as portfolio_tracker).

First-time setup:
  1. Jarvis opens a Chrome window automatically on first call.
  2. Log into canva.com in that window.
  3. The session persists for all future calls.

Supported actions:
  create_design   — open Canva, click "Create a design", pick format, set title
  list_designs    — list recent designs from your Canva home
  export_design   — open a design URL/ID and download it locally
  get_design      — get the title and current URL of an open/recent design
"""

import asyncio
import os
import platform
import threading
import time
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

CANVA_HOME   = "https://www.canva.com/"
CANVA_CREATE = "https://www.canva.com/create/"

FORMAT_PATHS = {
    "instagram_post":  "https://www.canva.com/create/instagram-posts/",
    "instagram_story": "https://www.canva.com/create/instagram-stories/",
    "facebook_post":   "https://www.canva.com/create/facebook-posts/",
    "poster":          "https://www.canva.com/create/posters/",
    "presentation":    "https://www.canva.com/create/presentations/",
}


def _profile_dir() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "JarvisChromeProfile"
    return Path.home() / ".jarvis_chrome_profile"


def _default_output() -> Path:
    out = Path.home() / "Desktop" / "Jarvis_Exports"
    out.mkdir(parents=True, exist_ok=True)
    return out


class _CanvaThread:
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
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="CanvaThread")
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

    def run(self, coro, timeout: int = 90):
        if not self._loop:
            raise RuntimeError("CanvaThread not started.")
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
                ctx  = await self._ensure_context()
                page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                return page
            except Exception as e:
                print(f"[Canva] Browser error (attempt {attempt + 1}): {e}")
                if self._context:
                    try:
                        await self._context.close()
                    except Exception:
                        pass
                    self._context = None
                if attempt >= 1:
                    raise
        raise RuntimeError("Could not open Canva page after retrying.")

    def _is_logged_in(self, url: str) -> bool:
        return "canva.com" in url and "login" not in url and "signup" not in url

    async def list_designs(self) -> str:
        page = await self._get_page(CANVA_HOME)
        try:
            await page.wait_for_load_state("networkidle", timeout=12000)
        except PlaywrightTimeout:
            pass

        if not self._is_logged_in(page.url):
            return (
                "Canva requires login. A Chrome window is open — "
                "please log into canva.com, then ask me again."
            )

        # Scrape design card titles from the home page
        try:
            await page.wait_for_selector("[data-testid='design-card'], [class*='designCard'], [class*='DesignCard']", timeout=8000)
        except PlaywrightTimeout:
            pass

        titles = await page.evaluate("""
            () => {
                const candidates = [
                    ...document.querySelectorAll('[data-testid="design-card"] [class*="title"]'),
                    ...document.querySelectorAll('[class*="designCardTitle"]'),
                    ...document.querySelectorAll('[class*="DesignCard"] span'),
                    ...document.querySelectorAll('li[class*="design"] span'),
                ];
                return [...new Set(candidates.map(el => el.textContent.trim()).filter(t => t.length > 0))].slice(0, 15);
            }
        """)

        if not titles:
            return "Canva home loaded but no designs detected. Try asking me to create a new design instead."
        return "Recent Canva designs:\n" + "\n".join(f"- {t}" for t in titles)

    async def create_design(self, fmt: str, prompt: str) -> str:
        url = FORMAT_PATHS.get(fmt.lower(), CANVA_CREATE)
        page = await self._get_page(url)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeout:
            pass

        if not self._is_logged_in(page.url):
            return (
                "Canva requires login. A Chrome window is open — "
                "please log into canva.com, then ask me again."
            )

        # Click "Create [format]" or the primary CTA button
        try:
            btn = page.locator(
                "a[href*='/design/'], button[class*='create'], button[class*='Create'], "
                "[data-testid*='create'], a[class*='cta']"
            ).first
            if await btn.is_visible(timeout=5000):
                await btn.click()
                await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        current_url = page.url
        return (
            f"Canva design opened for format: {fmt}.\n"
            f"Prompt/concept: {prompt}\n"
            f"URL: {current_url}\n"
            "The design is open in the browser — you can edit it directly in Canva."
        )

    async def export_design(self, design_url: str, exp_fmt: str, out_dir: Path) -> str:
        if not design_url.startswith("http"):
            # treat as design ID
            design_url = f"https://www.canva.com/design/{design_url}/edit"

        page = await self._get_page(design_url)
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except PlaywrightTimeout:
            pass

        if not self._is_logged_in(page.url):
            return "Canva requires login. Please log in and try again."

        # Click the Share/Download button (Canva uses a "Share" button that opens download)
        try:
            share_btn = page.locator(
                "button[data-testid='share-button'], button[aria-label*='Share'], "
                "button[class*='share'], button[data-testid*='share']"
            ).first
            await share_btn.click(timeout=8000)
            await page.wait_for_timeout(1000)
        except Exception:
            return (
                "Could not find the Share/Download button. "
                "The design is open in the browser — please download it manually."
            )

        # Click "Download" option inside the share panel
        try:
            dl_btn = page.locator(
                "[data-testid='download-button'], button[aria-label*='Download'], "
                "li[data-testid*='download'], [class*='download']"
            ).first
            await dl_btn.click(timeout=5000)
            await page.wait_for_timeout(1000)
        except Exception:
            return "Share panel opened. Click 'Download' in the panel to save the design."

        # Set format if selector available
        try:
            fmt_select = page.locator("[data-testid='file-type-selector'], select[class*='fileType']").first
            if await fmt_select.is_visible(timeout=3000):
                await fmt_select.select_option(label=exp_fmt.upper())
        except Exception:
            pass

        # Click the final Download button and capture the download
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            async with page.expect_download(timeout=30000) as dl_info:
                final_btn = page.locator(
                    "button[data-testid='download-submit-button'], "
                    "button[class*='downloadButton'], button[aria-label*='Download']"
                ).last
                await final_btn.click(timeout=8000)
            download = await dl_info.value
            save_path = out_dir / (download.suggested_filename or f"canva_export.{exp_fmt}")
            await download.save_as(str(save_path))
            return f"Design exported to: {save_path}"
        except Exception as e:
            return (
                f"Download initiated but could not auto-save: {e}\n"
                "Check your browser's download folder."
            )

    async def get_design(self) -> str:
        ctx = await self._ensure_context()
        if not ctx.pages:
            return "No Canva design currently open."
        page = ctx.pages[0]
        title = await page.title()
        return f"Current design: {title}\nURL: {page.url}"

    async def close(self):
        if self._context:
            await self._context.close()
            self._context = None


# ── Singleton ──────────────────────────────────────────────────────────────────
_ct         = _CanvaThread()
_ct_started = False
_ct_lock    = threading.Lock()


def _ensure_started():
    global _ct_started
    with _ct_lock:
        if not _ct_started:
            _ct.start()
            _ct_started = True


def canva_tool(parameters: dict, player=None, speak=None) -> str:
    """
    parameters:
        action        : create_design | list_designs | export_design | get_design
        prompt        : design description / concept (for create_design)
        format        : instagram_post | instagram_story | facebook_post | poster | presentation
        design_id     : design URL or ID (for export_design)
        export_format : png | pdf | jpg (default: png)
        output_path   : local folder path (default: Desktop/Jarvis_Exports)
    """
    _ensure_started()

    action     = (parameters or {}).get("action", "").lower().strip()
    prompt     = parameters.get("prompt", "")
    fmt        = parameters.get("format", "instagram_post").lower()
    design_id  = parameters.get("design_id", "")
    exp_fmt    = parameters.get("export_format", "png").lower()
    out_dir    = Path(parameters.get("output_path", str(_default_output())))

    try:
        if action == "list_designs":
            result = _ct.run(_ct.list_designs(), timeout=60)

        elif action == "create_design":
            result = _ct.run(_ct.create_design(fmt, prompt), timeout=60)

        elif action == "export_design":
            if not design_id:
                return "export_design requires a design_id (URL or Canva design ID)."
            result = _ct.run(_ct.export_design(design_id, exp_fmt, out_dir), timeout=90)

        elif action == "get_design":
            result = _ct.run(_ct.get_design(), timeout=30)

        elif action == "resize_design":
            return "resize_design: open the design in Canva and use Resize & Magic Switch from the toolbar."

        else:
            return f"Unknown canva_tool action: '{action}'. Use: create_design | list_designs | export_design | get_design."

    except Exception as e:
        result = f"canva_tool error: {e}"

    print(f"[Canva] {result[:120]}")
    if player:
        player.write_log(f"[canva] {result[:100]}")

    return result
