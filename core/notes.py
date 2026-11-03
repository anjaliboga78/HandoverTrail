"""My notes: private and shared sticky notes that sit NEXT TO the evidence, never inside it.

Rules that make notes safe:
- A note is not evidence. It never enters a handover, plan or export by itself.
- Only a Lead can promote a note, and only with an exact quote that passes the Evidence Gate.
- Secrets and personal data are masked before a note is stored (same rules as sources).
- A note linked to an item is only visible to people who may see that item.
- The audit log records that a note was made, shared, promoted or deleted, but never the note text.
"""
from __future__ import annotations
import datetime as dt
import difflib
import re

from . import db, extract, handover, redact, roles, verify

try:
    from rapidfuzz import fuzz
except Exception:  # standard library fallback
    fuzz = None

KINDS = {"todo": "To-do", "question": "Question", "idea": "Idea", "headsup": "Heads-up", "learned": "I learned"}
KIND_COLOR = {"todo": "yellow", "question": "green", "idea": "blue", "headsup": "pink", "learned": "blue"}
KIND_TO_TYPE = {"todo": "next_action", "question": "open_question", "idea": "next_action",
                "headsup": "risk", "learned": "dependency"}
COLORS = ("yellow", "green", "blue", "pink")
VIS = {"me": "Only me", "team": "My team", "leads": "Leads only"}
MAX_LEN = 600
SCOPES = ("all", "mine", "shared", "pinned", "due")

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def today() -> dt.date:
    return dt.date.today()


# ------------------------------------------------------------------ reminders
def parse_when(text, ref: dt.date | None = None):
    """Understand 'tomorrow', 'in 3 days', '+2d', 'friday', '12 Nov', '12 Nov 2026', '2026-11-12'. Empty -> None."""
    s = (text or "").strip().lower()
    if not s:
        return None
    ref = ref or today()
    if s == "today":
        return ref.isoformat()
    if s == "tomorrow":
        return (ref + dt.timedelta(days=1)).isoformat()
    m = re.fullmatch(r"(?:in\s+|\+)(\d{1,3})\s*(d|day|days|w|week|weeks)", s)
    if m:
        n = int(m.group(1)) * (7 if m.group(2).startswith("w") else 1)
        return (ref + dt.timedelta(days=n)).isoformat()
    s2 = s.replace("next ", "")
    if s2 in _WEEKDAYS or s2 in [d[:3] for d in _WEEKDAYS]:
        idx = next(i for i, d in enumerate(_WEEKDAYS) if d.startswith(s2[:3]))
        return (ref + dt.timedelta(days=(idx - ref.weekday() - 1) % 7 + 1)).isoformat()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        try:
            return dt.date.fromisoformat(s).isoformat()
        except ValueError:
            raise ValueError("That date does not exist.")
    m = re.fullmatch(r"(\d{1,2})\s*([a-z]{3})[a-z]*\.?(?:\s+(\d{4}))?", s)
    if m and m.group(2) in _MONTHS:
        day, mon, yr = int(m.group(1)), _MONTHS.index(m.group(2)) + 1, m.group(3)
        try:
            d = dt.date(int(yr) if yr else ref.year, mon, day)
            if not yr and d < ref:
                d = dt.date(ref.year + 1, mon, day)
            return d.isoformat()
        except ValueError:
            raise ValueError("That date does not exist.")
    raise ValueError("Try 'tomorrow', 'in 3 days', 'friday', '12 Nov' or 2026-11-12.")


def when_label(remind_on, ref: dt.date | None = None):
    """('Due today' | 'Overdue 3 days' | 'In 4 days' | '12 Nov', kind) where kind is due, over or later."""
    if not remind_on:
        return "", ""
    ref = ref or today()
    d = dt.date.fromisoformat(remind_on)
    delta = (d - ref).days
    if delta == 0:
        return "Due today", "due"
    if delta < 0:
        return f"Overdue {-delta} day{'s' if delta < -1 else ''}", "over"
    if delta == 1:
        return "Tomorrow", "later"
    return (f"In {delta} days" if delta < 7 else f"{d.day} {d.strftime('%b')}"), "later"


# ------------------------------------------------------------------ which items a note may point at
def linkable_items(role: str) -> list:
    """Leads can link any item. Everyone else can only link items in the approved handover they may see."""
    if role == "Lead":
        return handover.list_items()
    view = handover.view_for(role)
    return list(view["items"]) if view else []


def _can_read(n: dict, user: str, role: str, link_ids: set, known_ids: set) -> bool:
    if n["author"] == user:
        return True
    if n["visibility"] == "me":
        return False
    if n["visibility"] == "leads" and role != "Lead":
        return False
    lid = n["link_item_id"]
    return lid is None or lid not in known_ids or lid in link_ids  # never reveal a note about a restricted item


# ------------------------------------------------------------------ create / change
def create(user: str, role: str, body: str, kind: str = "todo", color: str = "auto", visibility: str = "me",
           link_item_id=None, remind_text: str = "") -> int:
    body = (body or "").strip()
    if not body:
        raise ValueError("Write something on the note first.")
    if len(body) > MAX_LEN:
        raise ValueError(f"Keep notes under {MAX_LEN} characters. For long material, add a source instead.")
    if kind not in KINDS:
        raise ValueError("Unknown note type.")
    if visibility not in VIS:
        raise ValueError("Unknown visibility.")
    color = KIND_COLOR[kind] if color in ("auto", None, "") else color
    if color not in COLORS:
        raise ValueError("Unknown colour.")
    if link_item_id is not None:
        if link_item_id not in {i["id"] for i in linkable_items(role)}:
            raise ValueError("You cannot link a note to that item.")
    remind = parse_when(remind_text)
    clean, found = redact.redact(body)
    now = db.now()
    nid = db.x("INSERT INTO notes(author,body,kind,color,link_item_id,visibility,remind_on,created_at,updated_at) "
               "VALUES (?,?,?,?,?,?,?,?,?)", (user, clean, kind, color, link_item_id, visibility, remind, now, now))
    db.log(user, "note_create", f"note #{nid}", f"{kind}, {VIS[visibility]}" + (", secrets masked" if found else ""))
    return nid


def _mine(note_id: int, user: str) -> dict:
    n = db.one("SELECT * FROM notes WHERE id=?", (note_id,))
    if not n:
        raise ValueError("Note not found.")
    if n["author"] != user:
        raise PermissionError("Only the person who wrote a note can change it.")
    return n


def edit(note_id: int, user: str, body: str, visibility: str | None = None, remind_text=None) -> None:
    n = _mine(note_id, user)
    if n["promoted_item_id"]:
        raise ValueError("This note was promoted to a handover item. Edit the item instead.")
    body = (body or "").strip()
    if not body or len(body) > MAX_LEN:
        raise ValueError(f"A note needs 1 to {MAX_LEN} characters.")
    vis = visibility or n["visibility"]
    if vis not in VIS:
        raise ValueError("Unknown visibility.")
    remind = n["remind_on"] if remind_text is None else parse_when(remind_text)
    clean, _ = redact.redact(body)
    db.x("UPDATE notes SET body=?, visibility=?, remind_on=?, updated_at=? WHERE id=?",
         (clean, vis, remind, db.now(), note_id))
    if vis != n["visibility"]:
        db.log(user, "note_share", f"note #{note_id}", VIS[vis])


def set_pin(note_id: int, user: str, pinned: bool) -> None:
    _mine(note_id, user)
    db.x("UPDATE notes SET pinned=? WHERE id=?", (1 if pinned else 0, note_id))


def set_done(note_id: int, user: str, done: bool) -> None:
    _mine(note_id, user)
    db.x("UPDATE notes SET done=? WHERE id=?", (1 if done else 0, note_id))


def delete(note_id: int, user: str) -> None:
    _mine(note_id, user)
    db.x("DELETE FROM notes WHERE id=?", (note_id,))
    db.log(user, "note_delete", f"note #{note_id}")


# ------------------------------------------------------------------ reading
def list_for(user: str, role: str, scope: str = "all", query: str = "", ref: dt.date | None = None,
             kind: str = "all", show_done: bool = True) -> list:
    """Notes this person may see. Pinned first, then reminders that are due, then newest."""
    ref = ref or today()
    link_ids = {i["id"] for i in linkable_items(role)}
    known = {r["id"] for r in db.q("SELECT id FROM items")}
    rows = [n for n in db.q("SELECT * FROM notes") if _can_read(n, user, role, link_ids, known)]
    q = (query or "").strip().lower()
    out = []
    for n in rows:
        mine = n["author"] == user
        if kind != "all" and n["kind"] != kind:
            continue
        if not show_done and n["done"]:
            continue
        if scope == "mine" and not mine:
            continue
        if scope == "shared" and (mine or n["visibility"] == "me"):
            continue
        if scope == "pinned" and not n["pinned"]:
            continue
        if scope == "due" and not (mine and n["remind_on"] and not n["done"] and n["remind_on"] <= ref.isoformat()):
            continue
        if q and q not in n["body"].lower() and q not in n["author"].lower() and q not in KINDS[n["kind"]].lower():
            continue
        out.append(n)
    due_first = lambda n: 0 if (n["author"] == user and n["remind_on"] and not n["done"] and n["remind_on"] <= ref.isoformat()) else 1
    out.sort(key=lambda n: (-n["pinned"], n["done"], due_first(n), -n["id"]))
    return out


def count_open(user: str, role: str) -> int:
    return sum(1 for n in list_for(user, role, "mine") if not n["done"])


def stats(user: str, role: str, ref: dt.date | None = None) -> dict:
    mine = list_for(user, role, "mine")
    return {"open": sum(1 for n in mine if not n["done"]), "done": sum(1 for n in mine if n["done"]), "due": len(list_for(user, role, "due", ref=ref)),
            "shared": len(list_for(user, role, "shared")), "promoted": sum(1 for n in mine if n["promoted_item_id"])}


def due(user: str, role: str, ref: dt.date | None = None) -> list:
    return list_for(user, role, "due", ref=ref)


def by_item(user: str, role: str) -> dict:
    """{item id: [notes]} for the sticky notes shown on item cards."""
    out: dict = {}
    for n in list_for(user, role):
        if n["link_item_id"] and not n["done"]:
            out.setdefault(n["link_item_id"], []).append(n)
    return out


def signals(n: dict) -> list:
    """Quiet warnings: the thing this note points at has moved since the note was written."""
    lid = n["link_item_id"]
    if not lid:
        return []
    it = db.one("SELECT id, is_conflict, verify_status, review_status FROM items WHERE id=?", (lid,))
    if not it:
        return [f"Item #{lid} no longer exists"]
    out = []
    ch = db.one("SELECT MAX(changed_at) AS t FROM item_versions WHERE item_id=? AND action='edit'", (lid,))
    if ch and ch["t"] and ch["t"] > n["created_at"]:
        out.append(f"Item #{lid} was edited after you wrote this")
    if it["is_conflict"]:
        out.append(f"Item #{lid} has a conflict")
    if it["review_status"] == "rejected":
        out.append(f"Item #{lid} was rejected")
    if it["verify_status"] == "unverified":
        out.append(f"Item #{lid} is unverified")
    return out


# ------------------------------------------------------------------ promotion (Lead only, evidence required)
def _lines(text: str):
    for ln in re.split(r"(?<=[.!?])\s+|\n+", text or ""):
        ln = ln.strip(" -*#>\t")
        if len(ln) >= verify.MIN_QUOTE_CHARS:
            yield ln


def _score(a: str, b: str) -> float:
    a, b = a.lower(), b.lower()
    if fuzz is not None:
        return float(fuzz.token_set_ratio(a, b))
    return difflib.SequenceMatcher(None, a, b).ratio() * 100


def suggest_quotes(body: str, role: str, limit: int = 3, min_score: float = 45) -> list:
    """Lines in the sources this role may read that look like the note. A starting point for the proof quote."""
    found = []
    for s in db.q("SELECT id, name, visibility, text FROM sources ORDER BY id"):
        if not roles.can_see(role, s["visibility"]):
            continue
        for ln in _lines(s["text"]):
            sc = _score(body, ln)
            if sc >= min_score:
                found.append({"source_id": s["id"], "source_name": s["name"], "line": ln, "score": round(sc)})
    found.sort(key=lambda f: -f["score"])
    return found[:limit]


def promote(note_id: int, user: str, role: str, source_id: int, typ: str, quote: str, text=None, owner=None) -> int:
    if role != "Lead":
        raise PermissionError("Only a Lead can promote a note into the handover.")
    n = db.one("SELECT * FROM notes WHERE id=?", (note_id,))
    if not n:
        raise ValueError("Note not found.")
    link_ids = {i["id"] for i in linkable_items(role)}
    known = {r["id"] for r in db.q("SELECT id FROM items")}
    if not _can_read(n, user, role, link_ids, known):
        raise PermissionError("You cannot see this note.")
    if n["promoted_item_id"]:
        raise ValueError("This note was already promoted.")
    src = db.one("SELECT * FROM sources WHERE id=?", (source_id,))
    if not src or not roles.can_see(role, src["visibility"]):
        raise ValueError("Source not found.")
    if not (quote or "").strip():
        raise ValueError("Paste the exact quote from the source that proves this note.")
    status, _ = verify.verify(quote, src["text"])
    if status == "unverified":
        raise ValueError("That quote was not found in the source, so the note stays a note. Copy it exactly.")
    r = extract.add_manual_item(source_id, typ, (text or n["body"]), quote, owner, user)
    db.x("UPDATE notes SET promoted_item_id=?, updated_at=? WHERE id=?", (r["id"], db.now(), note_id))
    db.log(user, "note_promote", f"note #{note_id}", f"became item #{r['id']}, evidence={r['status']}")
    return r["id"]


# ------------------------------------------------------------------ export
def export_markdown(user: str, role: str) -> str:
    """Your own notes, as a file for YOU. This is never part of the handover."""
    lines = [f"# My notes ({user})", "_Notes are not evidence. They are not part of the handover._", ""]
    for n in list_for(user, role, "mine"):
        box = "[x]" if n["done"] else "[ ]" if n["kind"] == "todo" else "-"
        meta = [KINDS[n["kind"]], VIS[n["visibility"]]]
        if n["link_item_id"]:
            meta.append(f"item #{n['link_item_id']}")
        if n["remind_on"]:
            meta.append(f"remind {n['remind_on']}")
        lines.append(f"- {box} {n['body']}  ({', '.join(meta)})")
    return "\n".join(lines) + "\n"
