# REDESIGN+AGENTS+TOOLS 2026-06-16
"""
pizzax_tool.py — Pizza X BOH system integration for CHEF agent.
Uses supabase-py. Requires "supabase_url" and "supabase_key" in config/api_keys.json.
"""

import json
import sys
from datetime import date
from pathlib import Path


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _get_client():
    from supabase import create_client
    path = _get_base_dir() / "config" / "api_keys.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    url = data.get("supabase_url", "").strip()
    key = data.get("supabase_key", "").strip()
    if not url or not key:
        raise ValueError("supabase_url/supabase_key not found in api_keys.json")
    return create_client(url, key)


def pizzax_tool(parameters: dict, player=None, speak=None) -> str:
    action = (parameters or {}).get("action", "").lower().strip()
    name   = parameters.get("name", "")
    notes  = parameters.get("notes", "")
    count  = parameters.get("count", 10)

    try:
        sb = _get_client()

        if action == "list_shortages":
            res = sb.table("shortages").select("*").eq("resolved", False).order("created_at", desc=True).limit(count).execute()
            rows = res.data or []
            if not rows:
                return "No active shortages."
            lines = [f"- {r.get('item_name', 'Unknown')}: {r.get('notes', '')} (reported: {r.get('created_at', '')[:10]})" for r in rows]
            return "Active shortages:\n" + "\n".join(lines)

        if action == "add_shortage":
            sb.table("shortages").insert({"item_name": name, "notes": notes, "resolved": False}).execute()
            return f"Shortage logged: {name}. Notes: {notes or 'none'}."

        if action == "list_suppliers":
            res = sb.table("suppliers").select("name, contact_email, contact_phone, notes").limit(count).execute()
            rows = res.data or []
            if not rows:
                return "No suppliers found."
            lines = [f"- {r.get('name', '')}: {r.get('contact_email', '')} / {r.get('contact_phone', '')}" for r in rows]
            return "Suppliers:\n" + "\n".join(lines)

        if action == "get_supplier":
            res = sb.table("suppliers").select("*").ilike("name", f"%{name}%").limit(1).execute()
            rows = res.data or []
            if not rows:
                return f"Supplier '{name}' not found."
            r = rows[0]
            return f"Supplier: {r.get('name')}\nEmail: {r.get('contact_email')}\nPhone: {r.get('contact_phone')}\nNotes: {r.get('notes', '')}"

        if action == "list_recipes":
            res = sb.table("recipes").select("name, category").limit(count).execute()
            rows = res.data or []
            if not rows:
                return "No recipes found."
            lines = [f"- {r.get('name', '')}: {r.get('category', '')}" for r in rows]
            return "Recipes:\n" + "\n".join(lines)

        if action == "get_recipe":
            res = sb.table("recipes").select("*").ilike("name", f"%{name}%").limit(1).execute()
            rows = res.data or []
            if not rows:
                return f"Recipe '{name}' not found."
            r = rows[0]
            return f"Recipe: {r.get('name')}\nCategory: {r.get('category')}\nIngredients: {r.get('ingredients', 'N/A')}\nInstructions: {r.get('instructions', 'N/A')}"

        if action == "list_tasks":
            today = date.today().isoformat()
            res = sb.table("tasks").select("*").eq("completed", False).gte("date", today).order("date").limit(count).execute()
            rows = res.data or []
            if not rows:
                return "No open tasks for today."
            lines = [f"- [{r.get('id', '')}] {r.get('title', '')} — assigned: {r.get('assigned_to', 'unassigned')}" for r in rows]
            return "Open tasks:\n" + "\n".join(lines)

        if action == "complete_task":
            task_id = parameters.get("task_id", "")
            sb.table("tasks").update({"completed": True}).eq("id", task_id).execute()
            return f"Task {task_id} marked complete."

        if action == "shift_feed":
            res = sb.table("shift_feed").select("*").order("created_at", desc=True).limit(count).execute()
            rows = res.data or []
            if not rows:
                return "No shift feed entries."
            lines = [f"[{r.get('created_at', '')[:16]}] {r.get('author', 'Unknown')}: {r.get('content', '')}" for r in rows]
            return "Shift feed:\n" + "\n".join(lines)

        if action == "add_shift_note":
            sb.table("shift_feed").insert({"content": notes, "author": "J.A.R.V.I.S"}).execute()
            return f"Shift note added: {notes}"

        if action == "list_orders":
            res = sb.table("orders").select("*").eq("status", "pending").order("created_at", desc=True).limit(count).execute()
            rows = res.data or []
            if not rows:
                return "No pending orders."
            lines = [f"- Order #{r.get('id', '')}: {r.get('supplier_name', '')} — {r.get('items_count', 0)} items" for r in rows]
            return "Pending orders:\n" + "\n".join(lines)

        return f"Unknown action: {action}"

    except Exception as e:
        return f"pizzax_tool error: {e}"
