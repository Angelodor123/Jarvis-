# Google Calendar + Gmail Setup

JARVIS uses OAuth 2.0 to access your Google Calendar and Gmail. This is a
one-time setup (~5 minutes).

## 1. Create a Google Cloud project

1. Go to https://console.cloud.google.com/
2. Create a new project (e.g. "Jarvis Assistant")

## 2. Enable APIs

In your project, enable:
- **Google Calendar API**
- **Gmail API**

(APIs & Services → Library → search each → Enable)

## 3. Create OAuth credentials

1. APIs & Services → Credentials → Create Credentials → OAuth client ID
2. Application type: **Desktop app**
3. Name it anything (e.g. "Jarvis Desktop")
4. Download the JSON file

## 4. Configure consent screen (if prompted)

- User type: External (or Internal if using a Google Workspace account)
- Add your own email as a test user
- Scopes: you don't need to add them manually — JARVIS requests them at first run

## 5. Place the credentials file

Rename the downloaded file to `google_credentials.json` and place it at:

```
config/google_credentials.json
```

## 6. First run

The first time you ask JARVIS to check your calendar or email, a browser
window will open asking you to log in and grant permission. After approving,
a `config/google_token.json` file is created automatically — you won't be
asked again unless the token expires or is revoked.

## Troubleshooting

- **"Access blocked: app not verified"** — click "Advanced" → "Go to [app
  name] (unsafe)". This is normal for personal OAuth apps in testing mode.
- **Token expired errors** — delete `config/google_token.json` and re-run;
  it will re-trigger the consent flow.
- **Wrong account** — delete `config/google_token.json` to switch accounts.

## What JARVIS can do once configured

- "What's on my calendar this week?"
- "Schedule a supplier call with [name] tomorrow at 2pm"
- "Cancel my 3pm meeting"
- "Do I have any unread emails?"
- "Search my email for invoices from [supplier]"
- "Send an email to [name] about the new menu items"
