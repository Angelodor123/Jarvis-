# REDESIGN+AGENTS+TOOLS 2026-06-16
"""
image_gen_tool.py — Gemini Imagen image generation for VECTOR agent.
Uses existing gemini_api_key. Model: imagen-3.0-generate-002.
"""

import json
import sys
from pathlib import Path


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _load_api_key() -> str:
    path = _get_base_dir() / "config" / "api_keys.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for k in ("gemini_api_key", "google_api_key", "api_key"):
        val = data.get(k, "").strip()
        if val:
            return val
    raise ValueError("No Gemini API key found in api_keys.json")


ASPECT_MAP = {
    "1:1":  "1:1",
    "9:16": "9:16",
    "16:9": "16:9",
    "4:3":  "4:3",
}

STYLE_SUFFIXES = {
    "photorealistic": ", photorealistic, 8k, professional photography",
    "illustration":   ", digital illustration, vibrant colors, clean lines",
    "minimal":        ", minimalist design, flat style, clean background",
    "cinematic":      ", cinematic lighting, film grain, dramatic composition",
    "product":        ", product photography, studio lighting, white background",
}


def _default_output() -> Path:
    out = Path.home() / "Desktop" / "Jarvis_Exports"
    out.mkdir(parents=True, exist_ok=True)
    return out


def image_gen_tool(parameters: dict, player=None, speak=None) -> str:
    action    = (parameters or {}).get("action", "generate").lower().strip()
    prompt    = parameters.get("prompt", "")
    style     = parameters.get("style", "photorealistic").lower()
    out_dir   = Path(parameters.get("output_path", str(_default_output())))
    filename  = parameters.get("filename", "")
    count     = min(int(parameters.get("count", 2)), 4)
    aspect    = ASPECT_MAP.get(parameters.get("aspect", "1:1"), "1:1")

    if not prompt:
        return "image_gen_tool: 'prompt' is required."

    try:
        import google.generativeai as genai
        genai.configure(api_key=_load_api_key())

        full_prompt = prompt + STYLE_SUFFIXES.get(style, "")
        out_dir.mkdir(parents=True, exist_ok=True)

        num_images = 1 if action == "generate" else count

        model = genai.ImageGenerationModel("imagen-3.0-generate-002")
        result = model.generate_images(
            prompt=full_prompt,
            number_of_images=num_images,
            aspect_ratio=aspect,
        )

        saved = []
        base_name = filename or "jarvis_img"
        for i, img in enumerate(result.images):
            suffix = f"_{i+1}" if num_images > 1 else ""
            out_path = out_dir / f"{base_name}{suffix}.png"
            img._pil_image.save(str(out_path))
            saved.append(str(out_path))

        if len(saved) == 1:
            return f"Image generated: {saved[0]}"
        return f"{len(saved)} images generated:\n" + "\n".join(saved)

    except Exception as e:
        return f"image_gen_tool error: {e}"
