# REDESIGN+AGENTS+TOOLS 2026-06-16
"""
github_tool.py — GitHub repository management for FORGE agent.
Uses PyGithub. Requires "github_token" in config/api_keys.json.
"""

import json
import sys
from pathlib import Path


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _load_token() -> str:
    path = _get_base_dir() / "config" / "api_keys.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    token = data.get("github_token", "").strip()
    if not token:
        raise ValueError("github_token not found in api_keys.json")
    return token


def _get_github():
    from github import Github
    return Github(_load_token())


def github_tool(parameters: dict, player=None, speak=None) -> str:
    action = (parameters or {}).get("action", "").lower().strip()
    repo_name = parameters.get("repo", "")
    count = parameters.get("count", 10)

    try:
        g = _get_github()
        user = g.get_user()

        if action == "list_repos":
            repos = list(user.get_repos())[:count]
            lines = [f"{r.name}: {r.description or 'no description'} | {r.stargazers_count}★ | {r.language or 'N/A'}" for r in repos]
            return "Repositories:\n" + "\n".join(lines)

        if action == "get_repo":
            r = user.get_repo(repo_name)
            commits = list(r.get_commits())
            last_commit = commits[0].commit.message.split("\n")[0] if commits else "N/A"
            return (
                f"Repo: {r.full_name}\n"
                f"Stars: {r.stargazers_count} | Forks: {r.forks_count}\n"
                f"Language: {r.language or 'N/A'}\n"
                f"Last commit: {last_commit}\n"
                f"URL: {r.html_url}"
            )

        if action == "list_issues":
            r = user.get_repo(repo_name)
            issues = list(r.get_issues(state="open"))[:count]
            if not issues:
                return f"No open issues in {repo_name}."
            lines = [f"#{i.number}: {i.title} (opened by {i.user.login})" for i in issues]
            return f"Open issues in {repo_name}:\n" + "\n".join(lines)

        if action == "create_issue":
            r = user.get_repo(repo_name)
            title = parameters.get("title", "Untitled Issue")
            body = parameters.get("body", "")
            issue = r.create_issue(title=title, body=body)
            return f"Issue created: #{issue.number} — {issue.title}\n{issue.html_url}"

        if action == "list_commits":
            r = user.get_repo(repo_name)
            commits = list(r.get_commits())[:count]
            lines = [f"{c.sha[:7]}: {c.commit.message.split(chr(10))[0]} ({c.commit.author.date.strftime('%Y-%m-%d')})" for c in commits]
            return f"Recent commits in {repo_name}:\n" + "\n".join(lines)

        if action == "get_file":
            r = user.get_repo(repo_name)
            path = parameters.get("path", "")
            content = r.get_contents(path)
            text = content.decoded_content.decode("utf-8", errors="replace")
            return f"File: {path}\n```\n{text[:3000]}\n```"

        if action == "search_code":
            query = parameters.get("query", "")
            results = list(g.search_code(f"{query} user:{user.login}"))[:count]
            if not results:
                return f"No code results for '{query}'."
            lines = [f"{r.repository.name}/{r.path}: ...{r.text_matches[0].get('fragment', '')[:80] if r.text_matches else ''}..." for r in results]
            return f"Code search results for '{query}':\n" + "\n".join(lines)

        return f"Unknown action: {action}"

    except Exception as e:
        return f"github_tool error: {e}"
