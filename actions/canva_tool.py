# REDESIGN+AGENTS+TOOLS 2026-06-16
"""
canva_tool.py — Canva Connect API integration for VECTOR agent.
Uses Canva Connect REST API directly (requests).
Requires "canva_api_key" in config/api_keys.json.
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

CANVA_API_BASE = "https://api.canva.com/rest/v1"

FORMAT_SIZES = {
    "instagram_post":  {"width": 1080, "height": 1080, "unit": "px"},
    "instagram_story": {"width": 1080, "height": 1920, "unit": "px"},
    "facebook_post":   {"width": 1200, "height": 630,  "unit": "px"},
    "poster":          {"width": 2480, "height": 3508, "unit": "px"},
    "presentation":    {"width": 1920, "height": 1080, "unit": "px"},
}


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _load_api_key() -> str:
    path = _get_base_dir() / "config" / "api_keys.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    key = data.get("canva_api_key", "").strip()
    if not key:
        raise ValueError("canva_api_key not found in api_keys.json")
    return key


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_load_api_key()}",
        "Content-Type":  "application/json",
    }


def _default_output() -> Path:
    desktop = Path.home() / "Desktop" / "Jarvis_Exports"
    desktop.mkdir(parents=True, exist_ok=True)
    return desktop


def canva_tool(parameters: dict, player=None, speak=None) -> str:
    action    = (parameters or {}).get("action", "").lower().strip()
    prompt    = parameters.get("prompt", "")
    fmt       = parameters.get("format", "instagram_post").lower()
    design_id = parameters.get("design_id", "")
    exp_fmt   = parameters.get("export_format", "png").lower()
    out_dir   = Path(parameters.get("output_path", str(_default_output())))
    new_fmt   = parameters.get("new_format", "instagram_post").lower()

    try:
        if action == "list_designs":
            r = requests.get(f"{CANVA_API_BASE}/designs", headers=_headers(), timeout=15)
            r.raise_for_status()
            designs = r.json().get("items", [])[:10]
            if not designs:
                return "No designs found in Canva account."
            lines = [f"- {d.get('title', 'Untitled')} (ID: {d.get('id')}, updated: {d.get('updated_at', '')[:10]})" for d in designs]
            return "Recent Canva designs:\n" + "\n".join(lines)

        if action == "get_design":
            r = requests.get(f"{CANVA_API_BASE}/designs/{design_id}", headers=_headers(), timeout=15)
            r.raise_for_status()
            d = r.json()
            return (
                f"Design: {d.get('title', 'Untitled')}\n"
                f"ID: {d.get('id')}\n"
                f"Preview: {d.get('thumbnail', {}).get('url', 'N/A')}\n"
                f"Updated: {d.get('updated_at', '')[:10]}"
            )

        if action == "create_design":
            size = FORMAT_SIZES.get(fmt, FORMAT_SIZES["instagram_post"])
            payload = {
                "design_type": {
                    "type": "custom",
                    "width":  size["width"],
                    "height": size["height"],
                    "unit":   size["unit"],
                },
                "title": prompt[:100] if prompt else "J.A.R.V.I.S Design",
            }
            r = requests.post(f"{CANVA_API_BASE}/designs", headers=_headers(), json=payload, timeout=15)
            r.raise_for_status()
            d = r.json().get("design", r.json())
            did = d.get("id", "")
            url = d.get("urls", {}).get("edit_url", "open Canva to edit")
            return f"Design created! ID: {did}\nEdit at: {url}\nFormat: {fmt} ({size['width']}×{size['height']}px)"

        if action == "export_design":
            payload = {"design_id": design_id, "format": exp_fmt.upper()}
            r = requests.post(f"{CANVA_API_BASE}/exports", headers=_headers(), json=payload, timeout=30)
            r.raise_for_status()
            job = r.json()
            job_id = job.get("job", {}).get("id", "")

            # Poll for completion
            for _ in range(20):
                time.sleep(2)
                status_r = requests.get(f"{CANVA_API_BASE}/exports/{job_id}", headers=_headers(), timeout=15)
                status_r.raise_for_status()
                status_data = status_r.json()
                status = status_data.get("job", {}).get("status", "")
                if status == "success":
                    urls = status_data.get("job", {}).get("urls", [])
                    if urls:
                        file_url = urls[0]
                        out_dir.mkdir(parents=True, exist_ok=True)
                        out_path = out_dir / f"canva_export_{design_id[:8]}.{exp_fmt}"
                        file_data = requests.get(file_url, timeout=30).content
                        out_path.write_bytes(file_data)
                        return f"Design exported to: {out_path}"
                    break
                elif status == "failed":
                    return "Export failed on Canva side."
            return "Export timed out. Check Canva account."

        if action == "resize_design":
            size = FORMAT_SIZES.get(new_fmt, FORMAT_SIZES["instagram_post"])
            payload = {
                "design_id": design_id,
                "design_type": {
                    "type": "custom",
                    "width":  size["width"],
                    "height": size["height"],
                    "unit":   size["unit"],
                },
            }
            r = requests.post(f"{CANVA_API_BASE}/designs/{design_id}/resize", headers=_headers(), json=payload, timeout=15)
            r.raise_for_status()
            d = r.json().get("design", r.json())
            return f"Design resized to {new_fmt} ({size['width']}×{size['height']}px). New ID: {d.get('id', design_id)}"

        return f"Unknown action: {action}"

    except Exception as e:
        return f"canva_tool error: {e}"
