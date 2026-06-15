# Getting This Into Your Own GitHub Repo

I can't create or push to GitHub for you (no network access / credentials in
this environment), but here's the fastest path to a repo you control, with a
workflow that avoids manual full-folder swaps going forward.

## 1. Create the repo (2 minutes)

1. Go to https://github.com/new
2. Name it e.g. `jarvis-mark39` — set to **Private** (it will contain
   references to your business setup and API key placeholders)
3. Don't initialize with a README (you already have files)
4. Click "Create repository"

## 2. Push this folder

Unzip `Mark-XXXIX-OR-UPGRADED.zip` somewhere on your PC, then in that folder:

```bash
cd Mark-XXXIX-OR-UPGRADED
git init
git add .
git commit -m "Initial commit: upgraded Mark XXXIX-OR"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/jarvis-mark39.git
git push -u origin main
```

The `.gitignore` already excludes your API keys, Google credentials, and
runtime memory files — they won't be committed.

## 3. Ongoing updates — no manual folder swaps

Once it's a repo, any future changes I make for you come as either:

**A) A patch/diff** — I give you a `.patch` file, you run:
```bash
git apply the_changes.patch
git commit -am "Applied Jarvis upgrade: <description>"
```

**B) Direct file replacements** — for small changes, I give you the full
content of just the 1-2 changed files. You overwrite them and:
```bash
git add .
git commit -am "Updated: <description>"
```

Either way, `git diff` lets you review exactly what changed before committing.

## 4. Optional: Claude Code workflow (since you're exploring this)

If you set up Claude Code on your PC and point it at this repo, future
sessions can directly edit files in the repo, run `git diff` to show you
changes, and commit on your approval — no copy-pasting needed at all. That's
the smoothest long-term setup given where you're headed with this project.

## 5. Keep secrets out of git, always

Never commit:
- `config/api_keys.json`
- `config/google_credentials.json`
- `config/google_token.json`

These are already in `.gitignore`. If you ever accidentally commit one,
rotate that key/credential immediately (git history retains it even after
deletion unless you rewrite history).
