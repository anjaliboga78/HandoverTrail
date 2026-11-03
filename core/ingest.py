"""Step 1 - Connect: bring in authorised sources. Everything is redacted before it is stored."""
from __future__ import annotations
import csv
import io
import json
import re

from . import config, db
from .redact import redact
from .safety import find_injection


def infer_date(text: str, filename: str = ""):
    m = re.search(r"(?im)^\s*date\s*:\s*(\d{4}-\d{2}-\d{2})", text)
    if m:
        return m.group(1)
    m = re.search(r"(\d{4}-\d{2}-\d{2})", filename or "")
    return m.group(1) if m else None


def add_source(name, stype, text, visibility, source_date=None, user="system") -> int:
    if visibility not in config.LEVELS:
        raise ValueError(f"Unknown visibility '{visibility}'")
    clean, found = redact(text)
    sid = db.x(
        "INSERT INTO sources(name,type,source_date,visibility,text,redaction_count,extracted,created_at)"
        " VALUES (?,?,?,?,?,?,0,?)",
        (name, stype, source_date, visibility, clean, len(found), db.now()))
    for tag, prev in found:
        db.x("INSERT INTO redactions(source_id,tag,preview) VALUES (?,?,?)", (sid, tag, prev))
    db.log(user, "import_source", name, f"type={stype}, visibility={visibility}, masked={len(found)}")
    sus = find_injection(clean)
    if sus:
        db.log(user, "injection_warning", name, f"{len(sus)} line(s) look like instructions to an AI; treated as data")
    return sid


# ----------------------------------------------------------------- parsers
def csv_to_text(raw: str) -> str:
    """Turn a task list into plain sentences so every row can be quoted as evidence."""
    rows = list(csv.DictReader(io.StringIO(raw)))
    if not rows:
        raise ValueError("The CSV file has no rows.")
    out = []
    for r in rows:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        out.append(f"Task {r.get('id', '?')}: {r.get('title', 'untitled')}. "
                   f"Owner: {r.get('owner') or 'none'}. Status: {r.get('status') or 'unknown'}. "
                   f"Due: {r.get('due') or 'none'}. Notes: {r.get('notes') or '-'}")
    return "\n".join(out)


def issues_to_sources(issues: list):
    out = []
    for it in issues:
        n, title = it.get("number"), (it.get("title") or "").strip()
        who = (it.get("user") or {}).get("login", "unknown")
        date = (it.get("created_at") or "")[:10] or None
        kind = "Pull request" if it.get("pull_request") else "Issue"
        body = (it.get("body") or "").strip()
        text = f"{kind} #{n} ({it.get('state', 'open')}) opened by {who} on {date}: {title}.\n{body}"
        out.append((f"{kind.lower()} #{n}", text, date))
    return out


def commits_to_source(commits: list):
    lines, newest = [], None
    for c in commits:
        info = c.get("commit", {})
        author = (info.get("author") or {}).get("name", "unknown")
        date = ((info.get("author") or {}).get("date") or "")[:10]
        msg = (info.get("message") or "").splitlines()[0]
        lines.append(f"{date} {author}: {msg}")
        newest = max(newest or date, date)
    return f"commit history ({len(lines)} commits)", "\n".join(lines), newest


def _guess_type(filename: str) -> str:
    f = filename.lower()
    if "meeting" in f or "notes" in f:
        return "meeting_notes"
    if "chat" in f:
        return "chat_export"
    if f.endswith(".csv"):
        return "task_list"
    return "document"


MAX_UPLOAD_BYTES = 2_000_000


def ingest_upload(filename: str, data: bytes, visibility: str, source_date=None, user="system") -> list:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"{filename} is larger than 2 MB. Split it into smaller files.")
    raw = data.decode("utf-8", errors="replace")
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    ids = []
    if ext == "json":
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"{filename} is not valid JSON ({e.msg}).") from e
        if isinstance(obj, list) and obj and isinstance(obj[0], dict) and "number" in obj[0]:
            for name, text, d in issues_to_sources(obj):
                ids.append(add_source(name, "github_issue", text, visibility, d, user))
        elif isinstance(obj, list) and obj and isinstance(obj[0], dict) and "sha" in obj[0]:
            name, text, d = commits_to_source(obj)
            ids.append(add_source(name, "github_commits", text, visibility, d, user))
        else:
            raise ValueError("JSON must be a list of GitHub issues or commits.")
    elif ext == "csv":
        ids.append(add_source(filename, "task_list", csv_to_text(raw), visibility,
                              source_date or infer_date(raw, filename), user))
    elif ext in ("txt", "md", ""):
        if not raw.strip():
            raise ValueError(f"{filename} is empty.")
        ids.append(add_source(filename, _guess_type(filename), raw, visibility,
                              source_date or infer_date(raw, filename), user))
    else:
        raise ValueError(f"Unsupported file type '.{ext}'. Use .txt, .md, .csv or .json.")
    return ids


def fetch_github(repo: str, token=None, limit: int = 30):
    """Live GitHub connector (public repos work without a token, but with a low rate limit)."""
    import requests
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo or ""):
        raise ValueError("Use the form owner/repository, for example octocat/Hello-World.")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    base = f"https://api.github.com/repos/{repo}"
    try:
        issues = requests.get(f"{base}/issues", params={"state": "all", "per_page": limit},
                              headers=headers, timeout=30)
        commits = requests.get(f"{base}/commits", params={"per_page": 50}, headers=headers, timeout=30)
        for r in (issues, commits):
            if r.status_code == 404:
                raise ValueError("Repository not found, or it is private.")
            if r.status_code == 403:
                raise ValueError("GitHub rate limit reached. Add a token or try again later.")
            r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Could not reach GitHub ({type(e).__name__}).") from e
    return issues.json(), commits.json()


def import_github(repo, token=None, visibility="Everyone", user="system") -> int:
    issues, commits = fetch_github(repo, token)
    n = 0
    for name, text, d in issues_to_sources(issues):
        add_source(f"{repo} {name}", "github_issue", text, visibility, d, user)
        n += 1
    if commits:
        name, text, d = commits_to_source(commits)
        add_source(f"{repo} {name}", "github_commits", text, visibility, d, user)
        n += 1
    return n


# ----------------------------------------------------------------- demo project
DEMO_VISIBILITY = {"sponsor_note.txt": "Lead", "chat_export.txt": "Core"}


def load_demo(user="system") -> int:
    count = 0
    for path in sorted(config.DEMO_DIR.iterdir()):
        if path.name.startswith(".") or path.suffix.lower() not in (".txt", ".md", ".csv", ".json"):
            continue
        vis = DEMO_VISIBILITY.get(path.name, "Everyone")
        count += len(ingest_upload(path.name, path.read_bytes(), vis, None, user))
    return count


def load_demo_files(names: list, user="system") -> int:
    """Sample picker: load only the chosen demo files."""
    count = 0
    for path in sorted(config.DEMO_DIR.iterdir()):
        if path.name in names:
            count += len(ingest_upload(path.name, path.read_bytes(), DEMO_VISIBILITY.get(path.name, "Everyone"), None, user))
    return count


def demo_file_names() -> list:
    return [p.name for p in sorted(config.DEMO_DIR.iterdir())
            if not p.name.startswith(".") and p.suffix.lower() in (".txt", ".md", ".csv", ".json")]


def add_pasted(name: str, text: str, visibility: str, source_date, user="system") -> int:
    """Paste-your-notes box: plain text becomes a source like any file."""
    if not (text or "").strip():
        raise ValueError("Paste some text first.")
    if len(text) > 200_000:
        raise ValueError("That is too long (limit 200,000 characters).")
    return add_source((name or "Pasted notes").strip()[:80], "pasted_notes", text, visibility, source_date, user)
