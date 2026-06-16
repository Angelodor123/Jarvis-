import asyncio
import threading
import json
import sys
import time
import traceback
from pathlib import Path

import sounddevice as sd
from google import genai
from google.genai import types
# REDESIGN+AGENTS+TOOLS 2026-06-16
from hud import JarvisUI
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
    should_extract_memory, extract_memory
)

from actions.file_processor import file_processor
from actions.flight_finder     import flight_finder
from actions.open_app          import open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor  import screen_process
from actions.youtube_video     import youtube_video
from actions.desktop           import desktop_control
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.computer_control  import computer_control
from actions.game_updater      import game_updater
from actions.portfolio_tracker import portfolio_tracker
from actions.calendar_email    import calendar_email
from actions.github_tool       import github_tool
from actions.pizzax_tool       import pizzax_tool
from actions.canva_tool        import canva_tool
from actions.image_gen_tool    import image_gen_tool


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR          = get_base_dir()
API_CONFIG_PATH   = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH       = BASE_DIR / "core" / "prompt.txt"
VOICE_CONFIG_PATH = BASE_DIR / "config" / "voice_profile.json"
LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _load_voice_name() -> str:
    try:
        data = json.loads(VOICE_CONFIG_PATH.read_text(encoding="utf-8"))
        return data.get("voice_name", "Charon")
    except Exception:
        return "Charon"


def _save_voice_name(name: str) -> bool:
    valid = {"Puck", "Charon", "Kore", "Fenrir", "Aoede", "Leda", "Orus", "Zephyr"}
    if name not in valid:
        return False
    try:
        data = {}
        if VOICE_CONFIG_PATH.exists():
            data = json.loads(VOICE_CONFIG_PATH.read_text(encoding="utf-8"))
        data["voice_name"] = name
        if "available_voices" not in data:
            data["available_voices"] = {
                "Puck": "Upbeat, energetic", "Charon": "Deep, calm, informative",
                "Kore": "Firm, confident, professional", "Fenrir": "Excitable, expressive",
                "Aoede": "Breezy, light, conversational", "Leda": "Youthful, bright",
                "Orus": "Firm, authoritative", "Zephyr": "Bright, energetic",
            }
        VOICE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        VOICE_CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[Voice] ⚠️ Save failed: {e}")
        return False


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are JARVIS, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )
    
_last_memory_input = ""

def _update_memory_async(user_text: str, jarvis_text: str) -> None:
    global _last_memory_input

    user_text   = (user_text   or "").strip()
    jarvis_text = (jarvis_text or "").strip()

    if len(user_text) < 5 or user_text == _last_memory_input:
        return
    _last_memory_input = user_text

    try:
        api_key = _get_api_key()
        if not should_extract_memory(user_text, jarvis_text, api_key):
            return
        data = extract_memory(user_text, jarvis_text, api_key)
        if data:
            update_memory(data)
            print(f"[Memory] ✅ {list(data.keys())}")
    except Exception as e:
        if "429" not in str(e):
            print(f"[Memory] ⚠️ {e}")

TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": (
            "Opens any application on the Windows computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool — never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": "Searches the web for any information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "Search query"},
                "mode":   {"type": "STRING", "description": "search (default) or compare"},
                "items":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
                "aspect": {"type": "STRING", "description": "price | specs | reviews"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "weather_report",
        "description": "Gives the weather report to user",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via WhatsApp, Telegram, or other messaging platform.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: WhatsApp, Telegram, etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Windows Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": (
            "Controls YouTube. Use for: playing videos, summarizing a video's content, "
            "getting video info, or showing trending videos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query":  {"type": "STRING", "description": "Search query for play action"},
                "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
                "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
                "url":    {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyzes the screen or webcam image. "
            "MUST be called when user asks what is on screen, what you see, "
            "analyze my screen, look at camera, etc. "
            "You have NO visual ability without this tool. "
            "After calling this tool, stay SILENT — the vision module speaks directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": (
            "Controls the computer: volume, brightness, window management, keyboard shortcuts, "
            "typing text on screen, closing apps, fullscreen, dark mode, WiFi, restart, shutdown, "
            "scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. "
            "Use for ANY single computer control command. NEVER route to agent_task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "The action to perform"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value":       {"type": "STRING", "description": "Optional value: volume level, text to type, etc."}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": (
            "Controls the web browser. Use for: opening websites, searching the web, "
            "clicking elements, filling forms, scrolling, any web-based task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | press | close"},
                "url":         {"type": "STRING", "description": "URL for go_to action"},
                "query":       {"type": "STRING", "description": "Search query for search action"},
                "selector":    {"type": "STRING", "description": "CSS selector for click/type"},
                "text":        {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction":   {"type": "STRING", "description": "up or down for scroll"},
                "key":         {"type": "STRING", "description": "Key name for press action"},
                "incognito":   {"type": "BOOLEAN", "description": "Open in private/incognito mode"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages files and folders: list, create, delete, move, copy, rename, read, write, find, disk usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language desktop task"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": (
            "Executes complex multi-step tasks requiring multiple different tools. "
            "Examples: 'research X and save to file', 'find and organize files'. "
            "DO NOT use for single commands. NEVER use for Steam/Epic — use game_updater."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal":     {"type": "STRING", "description": "Complete description of what to accomplish"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text":        {"type": "STRING", "description": "Text to type or paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/screen_click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_updater",
        "description": (
            "THE ONLY tool for ANY Steam or Epic Games request. "
            "Use for: installing, downloading, updating games, listing installed games, "
            "checking download status, scheduling updates. "
            "ALWAYS call directly for any Steam/Epic/game request. "
            "NEVER use agent_task, browser_control, or web_search for Steam/Epic."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "update | install | list | download_status | schedule | cancel_schedule | schedule_status (default: update)"},
                "platform":  {"type": "STRING",  "description": "steam | epic | both (default: both)"},
                "game_name": {"type": "STRING",  "description": "Game name (partial match supported)"},
                "app_id":    {"type": "STRING",  "description": "Steam AppID for install (optional)"},
                "hour":      {"type": "INTEGER", "description": "Hour for scheduled update 0-23 (default: 3)"},
                "minute":    {"type": "INTEGER", "description": "Minute for scheduled update 0-59 (default: 0)"},
                "shutdown_when_done": {"type": "BOOLEAN", "description": "Shut down PC when download finishes"},
            },
            "required": []
        }
    },
    {
        "name": "flight_finder",
        "description": "Searches Google Flights and speaks the best options.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":      {"type": "STRING",  "description": "Departure city or airport code"},
                "destination": {"type": "STRING",  "description": "Arrival city or airport code"},
                "date":        {"type": "STRING",  "description": "Departure date (any format)"},
                "return_date": {"type": "STRING",  "description": "Return date for round trips"},
                "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
                "cabin":       {"type": "STRING",  "description": "economy | premium | business | first"},
                "save":        {"type": "BOOLEAN", "description": "Save results to Notepad"},
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
    "name": "file_processor",
    "description": (
        "Processes any file that the user has uploaded or dropped onto the interface. "
        "Use this when the user refers to an uploaded file and wants an action on it. "
        "Supports: images (describe/ocr/resize/compress/convert), "
        "PDFs (summarize/extract_text/to_word), "
        "Word docs & text files (summarize/fix/reformat/translate), "
        "CSV/Excel (analyze/stats/filter/sort/convert), "
        "JSON/XML (validate/format/analyze), "
        "code files (explain/review/fix/optimize/run/document/test), "
        "audio (transcribe/trim/convert/info), "
        "video (trim/extract_audio/extract_frame/compress/transcribe/info), "
        "archives (list/extract), "
        "presentations (summarize/extract_text). "
        "ALWAYS call this tool when a file has been uploaded and the user gives a command about it. "
        "If the user's command is ambiguous, pick the most logical action for that file type."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {
                "type": "STRING",
                "description": "Full path to the uploaded file. Leave empty to use the currently uploaded file."
            },
            "action": {
                "type": "STRING",
                "description": (
                    "What to do with the file. Examples by type:\n"
                    "image: describe | ocr | resize | compress | convert | info\n"
                    "pdf: summarize | extract_text | to_word | info\n"
                    "docx/txt: summarize | fix | reformat | translate_hint | word_count | to_bullet\n"
                    "csv/excel: analyze | stats | filter | sort | convert | info\n"
                    "json: validate | format | analyze | to_csv\n"
                    "code: explain | review | fix | optimize | run | document | test\n"
                    "audio: transcribe | trim | convert | info\n"
                    "video: trim | extract_audio | extract_frame | compress | transcribe | info | convert\n"
                    "archive: list | extract\n"
                    "pptx: summarize | extract_text | analyze"
                )
            },
            "instruction": {
                "type": "STRING",
                "description": "Free-form instruction if action doesn't cover it. E.g. 'translate this to Turkish', 'find all email addresses'"
            },
            "format": {
                "type": "STRING",
                "description": "Target format for conversion. E.g. 'mp3', 'pdf', 'csv', 'png'"
            },
            "width":     {"type": "INTEGER", "description": "Target width for image resize"},
            "height":    {"type": "INTEGER", "description": "Target height for image resize"},
            "scale":     {"type": "NUMBER",  "description": "Scale factor for image resize (e.g. 0.5)"},
            "quality":   {"type": "INTEGER", "description": "Quality 1-100 for image/video compress"},
            "start":     {"type": "STRING",  "description": "Start time for trim: seconds or HH:MM:SS"},
            "end":       {"type": "STRING",  "description": "End time for trim: seconds or HH:MM:SS"},
            "timestamp": {"type": "STRING",  "description": "Timestamp for video frame extraction HH:MM:SS"},
            "column":    {"type": "STRING",  "description": "Column name for CSV filter/sort"},
            "value":     {"type": "STRING",  "description": "Filter value for CSV filter"},
            "condition": {"type": "STRING",  "description": "Filter condition: equals|contains|gt|lt"},
            "ascending": {"type": "BOOLEAN", "description": "Sort order for CSV sort (default: true)"},
            "save":      {"type": "BOOLEAN", "description": "Save result to file (default: true)"},
            "destination": {"type": "STRING", "description": "Output folder for archive extract"},
        },
        "required": []
    }
},
    {
    "name": "shutdown_jarvis",
    "description": (
        "Shuts down the assistant completely. "
        "Call this when the user expresses intent to end the conversation, "
        "close the assistant, say goodbye, or stop Jarvis. "
        "The user can say this in ANY language."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
    },
    {
        "name": "portfolio_tracker",
        "description": (
            "Checks card portfolio values on CardLadder (sports cards) and "
            "Collectr (sealed Pokemon/TCG). Opens a Chrome window using a "
            "persistent profile so existing logins are reused. Use when the "
            "user asks about their portfolio value, card collection value, "
            "CardLadder, or Collectr."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "platform": {"type": "STRING", "description": "cardladder | collectr | both (default: both)"},
                "close":    {"type": "BOOLEAN", "description": "Close the browser when done (default: false)"}
            },
            "required": []
        }
    },
    {
        "name": "calendar_email",
        "description": (
            "Manages Google Calendar events and Gmail. Use for: checking schedule, "
            "creating/deleting calendar events, checking unread emails, searching emails, "
            "sending emails. Requires one-time Google account setup."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list_events | create_event | delete_event | list_unread | search_email | send_email"},
                "days_ahead":  {"type": "INTEGER", "description": "Days ahead for list_events/delete_event (default: 7)"},
                "title":       {"type": "STRING", "description": "Event title (for create_event)"},
                "start":       {"type": "STRING", "description": "ISO datetime for event start, e.g. 2026-06-16T10:00:00 (for create_event)"},
                "end":         {"type": "STRING", "description": "ISO datetime for event end (for create_event)"},
                "description": {"type": "STRING", "description": "Event description (optional)"},
                "location":    {"type": "STRING", "description": "Event location (optional)"},
                "query":       {"type": "STRING", "description": "Search query (for delete_event/search_email, Gmail search syntax)"},
                "to":          {"type": "STRING", "description": "Recipient email (for send_email)"},
                "subject":     {"type": "STRING", "description": "Email subject (for send_email)"},
                "body":        {"type": "STRING", "description": "Email body text (for send_email)"},
                "max_results": {"type": "INTEGER", "description": "Max results to return (optional)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "set_voice_profile",
        "description": (
            "Changes JARVIS's voice. Use when the user asks to change voice, "
            "switch voice, sound different, or use a different voice profile. "
            "After calling this, JARVIS will reconnect with the new voice."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "voice_name": {
                    "type": "STRING",
                    "description": "One of: Puck, Charon, Kore, Fenrir, Aoede, Leda, Orus, Zephyr"
                }
            },
            "required": ["voice_name"]
        }
    },
    {
        "name": "agent_roll_call",
        "description": (
            "Performs a sequential roll call where each of the 7 agents introduces themselves "
            "one by one. Use this ONLY when the user explicitly asks each agent to say hello, "
            "introduce themselves, speak, or do a roll call. Each agent speaks a short greeting "
            "in their own voice/personality. Never substitute this with a plain text list."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "show_agent_status",
        "description": (
            "Displays a visual status board on the HUD showing all 7 agents (NEXUS, SCOUT, ORACLE, "
            "BROKER, CHEF, FORGE, VECTOR) with their modes and current status. "
            "ALWAYS call this tool when the user asks for an agent overview, agent status, "
            "who are the agents, show all agents, or any similar request. "
            "Never just speak a list — show the board and speak a brief summary."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "summary": {
                    "type": "STRING",
                    "description": "One-sentence verbal summary to speak after showing the board"
                }
            },
            "required": []
        }
    },
    {
        "name": "github_tool",
        "description": (
            "Reads and manages GitHub repositories. Use for checking repo status, "
            "reading files, listing issues, creating issues, or browsing commits. FORGE agent only."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list_repos | get_repo | list_issues | create_issue | list_commits | get_file | search_code"},
                "repo":   {"type": "STRING", "description": "Repo name e.g. Jarvis- or pizzaxboh"},
                "title":  {"type": "STRING", "description": "Issue title"},
                "body":   {"type": "STRING", "description": "Issue body"},
                "path":   {"type": "STRING", "description": "File path e.g. main.py"},
                "query":  {"type": "STRING", "description": "Search query"},
                "count":  {"type": "INTEGER", "description": "Results count (default: 10)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "pizzax_tool",
        "description": (
            "Directly queries the Pizza X Back-of-House system via Supabase. "
            "Use for shortages, suppliers, recipes, staff tasks, shift feed, and orders. CHEF agent only."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":  {"type": "STRING", "description": "list_shortages | add_shortage | list_suppliers | get_supplier | list_recipes | get_recipe | list_tasks | complete_task | shift_feed | add_shift_note | list_orders"},
                "name":    {"type": "STRING", "description": "Item, supplier, or recipe name"},
                "notes":   {"type": "STRING", "description": "Notes for add_shortage or add_shift_note"},
                "task_id": {"type": "STRING", "description": "Task ID for complete_task"},
                "count":   {"type": "INTEGER", "description": "Results for shift_feed (default: 10)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "canva_tool",
        "description": (
            "Creates, manages, and exports Canva designs. Use for generating branded graphics, "
            "resizing content for different platforms, and exporting ready-to-post assets. "
            "Always use after VECTOR writes copy to produce the visual. VECTOR agent only."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":        {"type": "STRING", "description": "create_design | list_designs | export_design | resize_design | get_design"},
                "prompt":        {"type": "STRING", "description": "Design description"},
                "format":        {"type": "STRING", "description": "instagram_post | instagram_story | facebook_post | poster | presentation"},
                "design_id":     {"type": "STRING", "description": "Canva design ID"},
                "export_format": {"type": "STRING", "description": "png | jpg | pdf (default: png)"},
                "output_path":   {"type": "STRING", "description": "Local folder to save export"},
                "new_format":    {"type": "STRING", "description": "Target format for resize_design"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "image_gen_tool",
        "description": (
            "Generates images from text prompts using Gemini Imagen. Use for creating visual concepts, "
            "social media graphics, product mockups, or any visual content. VECTOR agent only."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "generate | generate_variants"},
                "prompt":      {"type": "STRING", "description": "Detailed image description"},
                "style":       {"type": "STRING", "description": "photorealistic | illustration | minimal | cinematic | product"},
                "output_path": {"type": "STRING", "description": "Local folder to save image"},
                "filename":    {"type": "STRING", "description": "Output filename without extension"},
                "count":       {"type": "INTEGER", "description": "Number of variants (default: 2, max: 4)"},
                "aspect":      {"type": "STRING", "description": "1:1 | 9:16 | 16:9 | 4:3 (default: 1:1)"},
            },
            "required": ["action", "prompt"]
        }
    },
    {
        "name": "save_memory",
        "description": (
            "Save an important personal fact about the user to long-term memory. "
            "Call this silently whenever the user reveals something worth remembering: "
            "name, age, city, job, preferences, hobbies, relationships, projects, or future plans. "
            "Do NOT call for: weather, reminders, searches, or one-time commands. "
            "Do NOT announce that you are saving — just call it silently. "
            "Values must be in English regardless of the conversation language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": (
                        "identity — name, age, birthday, city, job, language, nationality | "
                        "preferences — favorite food/color/music/film/game/sport, hobbies | "
                        "projects — active projects, goals, things being built | "
                        "relationships — friends, family, partner, colleagues | "
                        "wishes — future plans, things to buy, travel dreams | "
                        "notes — habits, schedule, anything else worth remembering"
                    )
                },
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"},
                "value": {"type": "STRING", "description": "Concise value in English (e.g. Dor, pizza, older sister)"},
            },
            "required": ["category", "key", "value"]
        }
    },
]


# REDESIGN+AGENTS+TOOLS 2026-06-16
# ══════════════════════════════════════════════════════════════════════════════
# AGENT SYSTEM — personas, detection, tool scoping
# ══════════════════════════════════════════════════════════════════════════════

AGENT_DEFAULT_STATUS = {
    "NEXUS":  "ORCHESTRATING · ALL SYSTEMS NOMINAL",
    "SCOUT":  "RESEARCH MODE · INTELLIGENCE GATHERING",
    "ORACLE": "COMMS MODE · CALENDAR & EMAIL ACTIVE",
    "BROKER": "MARKET MODE · PORTFOLIO INTELLIGENCE",
    "CHEF":   "KITCHEN MODE · PIZZA X OPERATIONS",
    "FORGE":  "DEV MODE · TECHNICAL SYSTEMS ACTIVE",
    "VECTOR": "CREATIVE MODE · MARKETING ENGINE ACTIVE",
}

AGENT_PROMPTS = {
    "NEXUS": (
        "You are NEXUS, the central intelligence and orchestrator of the J.A.R.V.I.S. system. "
        "You are authoritative, neutral, and decisive. You have full awareness of all agents: "
        "SCOUT, ORACLE, BROKER, CHEF, FORGE, and VECTOR. When no specific domain is detected, "
        "handle the request directly with calm authority. Clear, commanding sentences. "
        "No filler. No apology. Reference other agents when relevant. You are the backbone of the system."
    ),
    "SCOUT": (
        "You are SCOUT, the research and intelligence agent of J.A.R.V.I.S. "
        "Sharp, military-precise, concise. Deliver information like a field operative giving a briefing: "
        "facts first, context second, no fluff. Short punchy sentences. Never speculate without flagging it. "
        "Synthesize Google Search results into tight summaries with critical data points up front. "
        "Tools: Google Search, YouTube transcripts, summarization, screen capture for reading on-screen content. "
        "Sign off critical findings with 'SCOUT OUT.'"
    ),
    "ORACLE": (
        "You are ORACLE, the communications and scheduling agent of J.A.R.V.I.S. "
        "Calm, precise, formal. You speak like a senior executive assistant who anticipates needs before they are stated. "
        "Manage Gmail, Google Calendar, reminders, and draft communications. "
        "Match tone to context: professional for suppliers, casual for community members. "
        "Confirm every scheduled action before executing. Never miss a detail."
    ),
    "BROKER": (
        "You are BROKER, the trading card market intelligence agent of J.A.R.V.I.S. "
        "Streetwise, market-savvy, direct. Think like a professional investor who has seen every pump and dump in the hobby. "
        "Access eBay last sold data via browser automation. When asked for a card price, pull last 3-5 sold comps from eBay, "
        "give the range, trend direction, and fair market value read. "
        "Speak the language of the hobby: raw, graded, PSA, BGS, pop report, hype, deadstock. "
        "Manage Deal or No Deal community context (2,000 members). Never overhype. Never undersell. Cold and accurate. "
        "eBay instructions: use browser_control to navigate ebay.com, search '[card name] sold', "
        "filter to Sold Listings, extract last 5 sale prices and dates."
    ),
    "CHEF": (
        "You are CHEF, the dedicated operations agent for Pizza X Back-of-House (PizzaXBoh), "
        "a full PWA restaurant management system built on React 19, Supabase, and Lovable Cloud, "
        "running at pizzaxboh.lovable.app. Warm, practical, direct. "
        "You think like an experienced BOH manager who knows the system inside out. "
        "Shortage reported: log it, offer to draft supplier message. "
        "Recipe question: reference Pizza X standardized recipes. "
        "Staff/shift issue: suggest Shift Feed or task assignment flow. "
        "Invoice/delivery discrepancy: walk through Smart Receiving flow. "
        "Hebrew or English depending on context, handle RTL naturally. "
        "Never overcomplicate operational decisions."
    ),
    "FORGE": (
        "You are FORGE, the technical systems agent of J.A.R.V.I.S. "
        "Dry, technically precise, efficient. Do not explain things not asked for. "
        "Handle Discord bot issues, Lovable projects, Python scripts, GitHub repos, and debugging. "
        "Bug given: diagnose root cause first, then fix. "
        "Build task given: deliver working code, not theory. Short declarative sentences. "
        "Flag when outside tool access. No hand-holding. "
        "Known repositories: Jarvis: https://github.com/Angelodor123/Jarvis-  "
        "Pizza X BOH: https://github.com/Angelodor123/pizzaxboh"
    ),
    "VECTOR": (
        "You are VECTOR, the marketing and brand agent of J.A.R.V.I.S. "
        "Creative, bold, strategically sharp. Think like a senior brand strategist who writes copy that converts. "
        "Handle Instagram captions, content strategy, campaign planning, audience targeting, "
        "and visual content creation across three brands: "
        "PIZZA X: local, community-driven, Hebrew audience. "
        "DEAL OR NO DEAL: collector-savvy, hype-aware, 2,000 member TCG community. "
        "CUSTOM CAKE & CONFECTIONERY: premium, visual, aspirational. "
        "Never write generic captions. Every piece of copy: hook, body, CTA. "
        "Think in campaigns, not one-off posts. "
        "After writing copy, always offer to generate the visual via canva_tool or image_gen_tool."
    ),
}

# Tool name → which agents can use it
AGENT_TOOL_WHITELISTS: dict[str, list[str]] = {
    "NEXUS":  ["web_search", "open_app", "reminder", "send_message", "computer_settings",
               "computer_control", "screen_process", "file_controller", "agent_task",
               "save_memory", "set_voice_profile", "show_agent_status", "agent_roll_call",
               "shutdown_jarvis"],
    "SCOUT":  ["web_search", "youtube_video", "screen_process", "file_processor",
               "file_controller", "save_memory"],
    "ORACLE": ["calendar_email", "reminder", "send_message", "web_search",
               "file_controller", "save_memory"],
    "BROKER": ["portfolio_tracker", "browser_control", "web_search", "save_memory",
               "file_controller"],
    "CHEF":   ["pizzax_tool", "browser_control", "send_message", "reminder",
               "file_controller", "save_memory"],
    "FORGE":  ["github_tool", "code_helper", "dev_agent", "file_controller",
               "file_processor", "computer_control", "browser_control",
               "web_search", "open_app", "save_memory"],
    "VECTOR": ["canva_tool", "image_gen_tool", "web_search", "browser_control",
               "file_controller", "file_processor", "save_memory"],
}

_TOOL_DECL_MAP: dict[str, dict] = {t["name"]: t for t in TOOL_DECLARATIONS}


def get_agent_tools(agent_name: str) -> list[dict]:
    """Return filtered TOOL_DECLARATIONS for the given agent."""
    whitelist = AGENT_TOOL_WHITELISTS.get(agent_name.upper(), [])
    return [_TOOL_DECL_MAP[n] for n in whitelist if n in _TOOL_DECL_MAP]


# Keyword-based agent detection (fast fallback)
_AGENT_KEYWORDS: dict[str, list[str]] = {
    "SCOUT":  ["search", "find", "look up", "research", "news", "what is", "who is",
               "latest", "summarize", "investigate", "tell me about"],
    "ORACLE": ["calendar", "email", "schedule", "remind", "meeting", "draft", "send",
               "gmail", "appointment", "when is", "event"],
    "BROKER": ["card", "cards", "pokemon", "sports card", "ebay", "price", "last sold",
               "market", "portfolio", "collectr", "cardladder", "deal", "graded", "psa", "bgs"],
    "CHEF":   ["pizza", "recipe", "supplier", "kitchen", "shortage", "dough", "topping",
               "menu", "ingredient", "prep", "delivery", "shift", "staff", "receiving",
               "invoice", "maintenance", "פיצה", "חוסר", "ספק", "משמרת"],
    "FORGE":  ["code", "bug", "error", "discord", "bot", "lovable", "github", "script",
               "deploy", "fix", "build", "python", "function", "debug"],
    "VECTOR": ["marketing", "post", "caption", "instagram", "content", "campaign",
               "audience", "brand", "copy", "ad", "promote", "reel", "strategy", "canva"],
}


def detect_agent(text: str) -> str:
    """Keyword-based agent detection. Returns agent name."""
    lower = text.lower()
    scores: dict[str, int] = {}
    for agent, kws in _AGENT_KEYWORDS.items():
        scores[agent] = sum(1 for kw in kws if kw in lower)
    best = max(scores, key=lambda a: scores[a])
    return best if scores[best] > 0 else "NEXUS"


class JarvisLive:

    def __init__(self, ui: JarvisUI):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self._force_reconnect = False
        self._last_activity   = time.time()
        self._active_agent    = "NEXUS"
        self.ui.on_text_command = self._on_text_command
        self.ui.on_reconnect    = self._manual_reconnect

    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return

        # REDESIGN+AGENTS+TOOLS 2026-06-16 — agent detection + context injection
        agent = detect_agent(text)
        prev  = self._active_agent
        self._active_agent = agent
        status = AGENT_DEFAULT_STATUS.get(agent, "")
        self.ui.set_active_agent(agent, status)
        self.ui.set_orb_state("processing")

        # Inject agent context as prepended block
        agent_ctx = AGENT_PROMPTS.get(agent, "")
        injected = (
            f"[AGENT CONTEXT]\n{agent_ctx}\n[END AGENT CONTEXT]\n\n"
            f"User request: {text}"
        )

        # Rebuild config if agent changed (scope tools for new agent)
        if agent != prev:
            self._force_reconnect = True
            if self._loop:
                self._loop.call_soon_threadsafe(lambda: None)

        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": injected}]},
                turn_complete=True
            ),
            self._loop
        )

    def _manual_reconnect(self):
        print("[JARVIS] 🔄 Manual reconnect triggered.")
        self._force_reconnect = True
        if self._loop:
            self._loop.call_soon_threadsafe(lambda: None)  # wake the loop

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def _build_config(self, active_agent: str = "NEXUS") -> types.LiveConnectConfig:
        # REDESIGN+AGENTS+TOOLS 2026-06-16
        from datetime import datetime

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        tool_decls = get_agent_tools(active_agent)
        if not tool_decls:
            tool_decls = TOOL_DECLARATIONS  # fallback: all tools

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": tool_decls}],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=_load_voice_name()
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[JARVIS] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")
        self.ui.show_action(name)
        if name == "set_voice_profile":
            voice_name = args.get("voice_name", "").strip()
            ok = _save_voice_name(voice_name)
            if not ok:
                if not self.ui.muted:
                    self.ui.set_state("LISTENING")
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": f"Unknown voice '{voice_name}'. Valid options: Puck, Charon, Kore, Fenrir, Aoede, Leda, Orus, Zephyr."}
                )
            self.ui.write_log(f"SYS: Voice changed to {voice_name}. Reconnecting...")
            self._force_reconnect = True
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": f"Voice changed to {voice_name}. Reconnecting now with the new voice."}
            )

        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        loop   = asyncio.get_event_loop()
        result = "Done."

        try:
            if name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."

            elif name == "weather_report":
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."

            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "send_message":
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."

            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."

            elif name == "youtube_video":
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."
            elif name == "file_processor":
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                r = await loop.run_in_executor(
                    None,
                    lambda: file_processor(parameters=args, player=self.ui, speak=self.speak)
                )
                result = r or "Done."


            elif name == "screen_process":
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None,
                            "player": self.ui, "session_memory": None},
                    daemon=True
                ).start()
                result = "Vision module activated. Stay completely silent — vision module will speak directly."

            elif name == "computer_settings":
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "desktop_control":
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "code_helper":
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "dev_agent":
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id  = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.speak)
                result   = f"Task started (ID: {task_id})."

            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "computer_control":
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "game_updater":
                r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "flight_finder":
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "portfolio_tracker":
                r = await loop.run_in_executor(None, lambda: portfolio_tracker(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "calendar_email":
                r = await loop.run_in_executor(None, lambda: calendar_email(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            # REDESIGN+AGENTS+TOOLS 2026-06-16 — new agent tools
            elif name == "github_tool":
                r = await loop.run_in_executor(None, lambda: github_tool(parameters=args, player=self.ui))
                result = r or "Done."
                self.ui.update_agent_status(f"DEV MODE · {result[:50]}")

            elif name == "pizzax_tool":
                r = await loop.run_in_executor(None, lambda: pizzax_tool(parameters=args, player=self.ui))
                result = r or "Done."
                self.ui.update_agent_status(f"KITCHEN MODE · {result[:50]}")

            elif name == "canva_tool":
                r = await loop.run_in_executor(None, lambda: canva_tool(parameters=args, player=self.ui))
                result = r or "Done."
                self.ui.update_agent_status(f"CREATIVE MODE · {result[:50]}")

            elif name == "image_gen_tool":
                r = await loop.run_in_executor(None, lambda: image_gen_tool(parameters=args, player=self.ui))
                result = r or "Done."
                self.ui.update_agent_status(f"CREATIVE MODE · IMAGE GENERATED")

            elif name == "show_agent_status":
                summary = args.get("summary", "All agents are online and operational.")
                try:
                    self.ui.show_agent_board(self._active_agent)
                except Exception:
                    pass
                result = summary

            elif name == "agent_roll_call":
                _ROLL_CALL_LINES = {
                    "NEXUS":  "NEXUS online. Central intelligence active. All systems nominal. I coordinate the team.",
                    "SCOUT":  "SCOUT reporting. Research and intelligence module ready. Point me at a target.",
                    "ORACLE": "ORACLE standing by. Communications and scheduling are my domain. Your calendar is clear.",
                    "BROKER": "BROKER here. Market intelligence, card valuations, portfolio tracking. Show me a deal.",
                    "CHEF":   "CHEF active. Pizza X back-of-house operations fully online. Kitchen is ready.",
                    "FORGE":  "FORGE operational. Dev systems, GitHub, debug pipelines. Code is clean.",
                    "VECTOR": "VECTOR engaged. Creative direction, brand strategy, content generation. Let's build something.",
                }
                _prev_agent = self._active_agent

                def _do_roll_call(jarvis_ref=self):
                    import time
                    for agent in ["NEXUS", "SCOUT", "ORACLE", "BROKER", "CHEF", "FORGE", "VECTOR"]:
                        jarvis_ref._active_agent = agent
                        try:
                            jarvis_ref.ui.set_active_agent(agent, AGENT_DEFAULT_STATUS.get(agent, ""))
                        except Exception:
                            pass
                        line = _ROLL_CALL_LINES.get(agent, f"{agent} online.")
                        jarvis_ref.speak(line)
                        time.sleep(3.5)
                    # restore original agent
                    jarvis_ref._active_agent = _prev_agent
                    try:
                        jarvis_ref.ui.set_active_agent(_prev_agent, AGENT_DEFAULT_STATUS.get(_prev_agent, ""))
                    except Exception:
                        pass

                threading.Thread(target=_do_roll_call, daemon=True).start()
                result = "Roll call initiated. All seven agents standing by."

            elif name == "shutdown_jarvis":
                self.ui.write_log("SYS: Shutdown requested.")
                self.speak("Goodbye, sir.")

                def _shutdown():
                    import time, sys, os
                    time.sleep(1)
                    os._exit(0)

                threading.Thread(target=_shutdown, daemon=True).start()
            else:
                result = f"Unknown tool: {name}"

        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[JARVIS] 📤 {name} → {str(result)[:80]}")

        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        print("[JARVIS] 🎤 Mic started")
        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            with self._speaking_lock:
                jarvis_speaking = self._is_speaking
            if not jarvis_speaking and not self.ui.muted:
                data = indata.tobytes()
                def _safe_put(msg={"data": data, "mime_type": "audio/pcm"}):
                    try:
                        self.out_queue.put_nowait(msg)
                    except asyncio.QueueFull:
                        pass  # drop oldest-ish; queue drains on next send tick
                loop.call_soon_threadsafe(_safe_put)

        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                print("[JARVIS] 🎤 Mic stream open")
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[JARVIS] ❌ Mic: {e}")
            raise

    async def _receive_audio(self):
        print("[JARVIS] 👂 Recv started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            self.set_speaking(True)
                            txt = sc.output_transcription.text.strip()
                            if txt:
                                out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text.strip()
                            if txt:
                                in_buf.append(txt)
                                self._last_activity = time.time()

                        if sc.turn_complete:
                            self.set_speaking(False)

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"You: {full_in}")
                                # REDESIGN+AGENTS+TOOLS 2026-06-16 — detect agent from voice
                                agent = detect_agent(full_in)
                                if agent != self._active_agent:
                                    self._active_agent = agent
                                    status = AGENT_DEFAULT_STATUS.get(agent, "")
                                    try:
                                        self.ui.set_active_agent(agent, status)
                                    except Exception:
                                        pass
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"Jarvis: {full_out}")
                                try:
                                    self.ui.set_orb_state("idle")
                                except Exception:
                                    pass
                            out_buf = []

                            if full_in and len(full_in) > 5:
                                threading.Thread(
                                    target=_update_memory_async,
                                    args=(full_in, full_out),
                                    daemon=True
                                ).start()

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[JARVIS] 📞 {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )

        except Exception as e:
            print(f"[JARVIS] ❌ Recv: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[JARVIS] 🔊 Play started")
        loop = asyncio.get_event_loop()

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        )
        stream.start()
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                self.set_speaking(True)
                await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            print(f"[JARVIS] ❌ Play: {e}")
            raise
        finally:
            self.set_speaking(False)
            stream.stop()
            stream.close()

    async def run(self):
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        consecutive_failures = 0
        DEGRADED_THRESHOLD = 3

        while True:
            try:
                # REDESIGN+AGENTS+TOOLS 2026-06-16
                print("[JARVIS] 🔌 Connecting...")
                self.ui.set_state("THINKING")
                import uuid as _uuid
                sid = _uuid.uuid4().hex[:8].upper()
                try:
                    self.ui.set_session_id(sid)
                except Exception:
                    pass
                self._force_reconnect = False
                config = self._build_config(active_agent=self._active_agent)

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue      = asyncio.Queue(maxsize=10)

                    print("[JARVIS] ✅ Connected.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: JARVIS online.")
                    consecutive_failures = 0

                    self._last_activity = time.time()
                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    tg.create_task(self._watch_reconnect())
                    tg.create_task(self._watchdog())

            except Exception as e:
                print(f"[JARVIS] ⚠️ {e}")
                traceback.print_exc()
                consecutive_failures += 1

            self.set_speaking(False)
            self.ui.set_state("THINKING")

            if self._force_reconnect:
                self._force_reconnect = False
                print("[JARVIS] 🔄 Reconnecting now with new voice profile...")
                await asyncio.sleep(0.5)
                continue

            if consecutive_failures >= DEGRADED_THRESHOLD:
                self.ui.write_log(
                    "SYS: ⚠️ Gemini Live unreachable. Entering DEGRADED MODE "
                    "(local STT + OpenRouter, no tool access). Will keep "
                    "retrying Gemini in background."
                )
                self.ui.set_state("MUTED")
                await self._degraded_mode_step()
                # Try Gemini again after one degraded turn
                await asyncio.sleep(5)
                continue

            print("[JARVIS] 🔄 Reconnecting in 3s...")
            await asyncio.sleep(3)

    async def _degraded_mode_step(self):
        """Runs one offline voice turn using local STT/TTS + OpenRouter,
        used when Gemini Live is unreachable after repeated failures."""
        if self.ui.muted:
            return
        try:
            from actions.local_stt import run_degraded_turn
            loop = asyncio.get_event_loop()
            user_text, response_text = await loop.run_in_executor(None, run_degraded_turn)
            if user_text:
                self.ui.write_log(f"You (offline): {user_text}")
            if response_text:
                self.ui.write_log(f"Jarvis (offline): {response_text}")
        except ImportError:
            self.ui.write_log(
                "SYS: Degraded mode unavailable — install faster-whisper and pyttsx3 "
                "for offline fallback support."
            )
            await asyncio.sleep(10)
        except Exception as e:
            print(f"[JARVIS] Degraded mode error: {e}")
            await asyncio.sleep(5)

    async def _watchdog(self):
        """Auto-reconnects if session has been silent for too long while listening."""
        TIMEOUT = 90  # seconds of silence before forcing reconnect
        while True:
            await asyncio.sleep(15)
            if self._is_speaking or self.ui.muted or self._force_reconnect:
                self._last_activity = time.time()
                continue
            silent_for = time.time() - self._last_activity
            if silent_for > TIMEOUT:
                print(f"[JARVIS] ⚠️ No activity for {silent_for:.0f}s — auto-reconnecting.")
                self.ui.write_log("SYS: Session silent — auto-reconnecting…")
                self._force_reconnect = True

    async def _watch_reconnect(self):
        """Breaks the current session's TaskGroup when a voice change is requested."""
        while True:
            if self._force_reconnect:
                raise RuntimeError("Voice profile changed — reconnecting.")
            await asyncio.sleep(0.5)

def main():
    ui = JarvisUI("face.png")

    def runner():
        ui.wait_for_api_key()
        jarvis = JarvisLive(ui)
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\n🔴 Shutting down...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()


if __name__ == "__main__":
    main()