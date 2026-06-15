"""
calendar_email.py
─────────────────────────────────────────────────────────────────────────────
Google Calendar + Gmail integration for JARVIS.

SETUP (one-time, manual — see SETUP_CALENDAR_EMAIL.md):
  1. Create a Google Cloud project, enable Calendar API + Gmail API.
  2. Create OAuth 2.0 Desktop credentials, download as
     config/google_credentials.json
  3. First run will open a browser for consent; token is cached to
     config/google_token.json for future runs.

Scopes requested:
  - calendar.events   (read/write events)
  - calendar.readonly (list calendars)
  - gmail.readonly    (read/search emails)
  - gmail.send        (send emails)

If config/google_credentials.json is missing, all functions return a helpful
setup message instead of crashing.
"""

import base64
import os
import sys
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime, timedelta

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR     = _get_base_dir()
CONFIG_DIR   = BASE_DIR / "config"
CRED_PATH    = CONFIG_DIR / "google_credentials.json"
TOKEN_PATH   = CONFIG_DIR / "google_token.json"

_SETUP_MSG = (
    "Google Calendar/Gmail isn't set up yet. "
    "Place your OAuth credentials at config/google_credentials.json "
    "(see SETUP_CALENDAR_EMAIL.md for the 5-minute setup steps), sir."
)


def _get_credentials():
    """Returns valid Google OAuth credentials, refreshing or running the
    consent flow as needed. Returns None if not configured."""
    if not CRED_PATH.exists():
        return None

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CRED_PATH), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return creds


# ── Calendar ─────────────────────────────────────────────────────────────────

def _calendar_service(creds):
    from googleapiclient.discovery import build
    return build("calendar", "v3", credentials=creds)


def _list_events(service, days_ahead: int = 7, max_results: int = 15) -> str:
    now   = datetime.utcnow().isoformat() + "Z"
    later = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now,
        timeMax=later,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])
    if not events:
        return f"No events in the next {days_ahead} days."

    lines = []
    for e in events:
        start = e["start"].get("dateTime", e["start"].get("date"))
        try:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            start_str = dt.strftime("%a %b %d, %I:%M %p")
        except Exception:
            start_str = start
        title = e.get("summary", "(no title)")
        lines.append(f"{start_str} — {title}")

    return "Upcoming events:\n" + "\n".join(lines)


def _create_event(service, title: str, start_iso: str, end_iso: str,
                   description: str = "", location: str = "") -> str:
    event = {
        "summary": title,
        "description": description,
        "location": location,
        "start": {"dateTime": start_iso},
        "end":   {"dateTime": end_iso},
    }
    created = service.events().insert(calendarId="primary", body=event).execute()
    return f"Event created: {title} ({created.get('htmlLink', 'no link')})"


def _delete_event(service, query: str, days_ahead: int = 14) -> str:
    now   = datetime.utcnow().isoformat() + "Z"
    later = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"

    events_result = service.events().list(
        calendarId="primary", timeMin=now, timeMax=later,
        q=query, singleEvents=True, maxResults=5,
    ).execute()

    events = events_result.get("items", [])
    if not events:
        return f"No event matching '{query}' found in the next {days_ahead} days."

    target = events[0]
    service.events().delete(calendarId="primary", eventId=target["id"]).execute()
    return f"Deleted event: {target.get('summary', '(no title)')}"


# ── Gmail ────────────────────────────────────────────────────────────────────

def _gmail_service(creds):
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=creds)


def _list_unread(service, max_results: int = 10) -> str:
    results = service.users().messages().list(
        userId="me", labelIds=["INBOX", "UNREAD"], maxResults=max_results
    ).execute()
    messages = results.get("messages", [])
    if not messages:
        return "No unread emails."

    lines = []
    for m in messages:
        msg = service.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "Subject"]
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        sender  = headers.get("From", "Unknown")
        subject = headers.get("Subject", "(no subject)")
        lines.append(f"{sender}: {subject}")

    return f"{len(messages)} unread:\n" + "\n".join(lines)


def _search_emails(service, query: str, max_results: int = 10) -> str:
    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()
    messages = results.get("messages", [])
    if not messages:
        return f"No emails found matching '{query}'."

    lines = []
    for m in messages:
        msg = service.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
        sender  = headers.get("From", "Unknown")
        subject = headers.get("Subject", "(no subject)")
        date    = headers.get("Date", "")
        lines.append(f"{date} | {sender}: {subject}")

    return f"{len(messages)} result(s):\n" + "\n".join(lines)


def _send_email(service, to: str, subject: str, body: str) -> str:
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    service.users().messages().send(
        userId="me", body={"raw": raw}
    ).execute()
    return f"Email sent to {to}: {subject}"


# ── Public API ───────────────────────────────────────────────────────────────

def calendar_email(parameters: dict, player=None, speak=None) -> str:
    """
    parameters:
        action : list_events | create_event | delete_event |
                 list_unread | search_email | send_email
        days_ahead   : int (for list_events, default 7)
        title        : str (for create_event)
        start        : ISO datetime string (for create_event)
        end          : ISO datetime string (for create_event)
        description  : str (optional, for create_event)
        location     : str (optional, for create_event)
        query        : str (for delete_event / search_email)
        to           : str (for send_email)
        subject      : str (for send_email)
        body         : str (for send_email)
        max_results  : int (optional)
    """
    creds = _get_credentials()
    if not creds:
        return _SETUP_MSG

    action = (parameters or {}).get("action", "").lower().strip()
    p = parameters or {}

    try:
        if action == "list_events":
            service = _calendar_service(creds)
            result = _list_events(
                service,
                days_ahead=int(p.get("days_ahead", 7)),
                max_results=int(p.get("max_results", 15)),
            )

        elif action == "create_event":
            service = _calendar_service(creds)
            result = _create_event(
                service,
                title=p.get("title", "New Event"),
                start_iso=p["start"],
                end_iso=p["end"],
                description=p.get("description", ""),
                location=p.get("location", ""),
            )

        elif action == "delete_event":
            service = _calendar_service(creds)
            result = _delete_event(
                service,
                query=p.get("query", ""),
                days_ahead=int(p.get("days_ahead", 14)),
            )

        elif action == "list_unread":
            service = _gmail_service(creds)
            result = _list_unread(service, max_results=int(p.get("max_results", 10)))

        elif action == "search_email":
            service = _gmail_service(creds)
            result = _search_emails(
                service, query=p.get("query", ""),
                max_results=int(p.get("max_results", 10)),
            )

        elif action == "send_email":
            service = _gmail_service(creds)
            result = _send_email(
                service,
                to=p["to"], subject=p.get("subject", "(no subject)"),
                body=p.get("body", ""),
            )

        else:
            result = f"Unknown action: {action}"

    except KeyError as e:
        result = f"Missing required parameter: {e}"
    except Exception as e:
        result = f"Calendar/Email error: {e}"

    print(f"[CalendarEmail] {result[:100]}")
    if player:
        player.write_log(f"[mail/cal] {result[:80]}")

    return result
