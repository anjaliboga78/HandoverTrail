"""Departure Checklist: everything a leaving person must close before they go, and how far along it is.

The list is BUILT FROM REAL DATA every time (items, owners, transfers), so nothing is invented and it
never goes stale. Only the completion state (ticks, notes, custom lines) is stored, in the `checklist` table.

Five sections:
  transfers  things they own that need a new owner. Done only when the transfer is COMPLETED on screen 5
             (a tick would not change who owns it, so this section cannot be ticked by hand).
  tasks      pending tasks and deadlines they own. Done when ticked, or when the task was transferred.
  decisions  decisions they own. Tick when the decision is recorded and the successor knows it.
  docs       one line per technical topic (database, payments, deployment, access) they own items in.
  deps       dependencies, blockers and open questions they own or are named in. Tick when resolved.
Restricted items show as a placeholder (number and type only) and are left out of the progress numbers.
"""
from __future__ import annotations
import re

from . import config, db, flags, handover, roles, transfer

SECTIONS = [("transfers", "Responsibility transfers"), ("tasks", "Pending tasks"), ("decisions", "Important decisions"),
            ("docs", "Technical documentation"), ("deps", "Unresolved dependencies")]
TITLE = dict(SECTIONS)
TYPE_SECTION = {"owner": "transfers", "risk": "transfers", "contact": "transfers", "next_action": "tasks",
                "deadline": "tasks", "decision": "decisions", "dependency": "deps", "blocker": "deps",
                "open_question": "deps"}
MENTION_TYPES = ("dependency", "blocker", "open_question", "owner")   # "owner" = a responsibility nobody holds
TECH_TOPICS = ("database", "payments", "deployment", "access")
URGENT_AT = 2          # score at or above this counts as "needs attention"
LOCK_TRANSFER = "Done when its transfer is completed (screen 5). Ticking would not change who owns it."


def ensure_schema() -> None:
    from contextlib import closing
    with closing(db.connect()) as c:
        c.executescript(db.SCHEMA)
        c.commit()


def can_edit(user: str, role: str, person: str) -> bool:
    """A Lead, or the leaving person themselves."""
    return role == "Lead" or (user or "").strip().lower() == (person or "").strip().lower()


def people() -> list:
    """Everyone who owns something, plus the signed-in demo users."""
    ensure_schema()
    names = {r["owner"].strip() for r in db.q("SELECT DISTINCT owner FROM items WHERE owner IS NOT NULL AND trim(owner)!='' "
                                              "AND review_status!='rejected'")}
    names |= {r["person"] for r in db.q("SELECT DISTINCT person FROM checklist")}
    return sorted(names, key=str.lower)


# ------------------------------------------------------------------ build
def _saved(person: str) -> dict:
    rows = db.q("SELECT * FROM checklist WHERE lower(person)=lower(?)", (person,))
    return {(r["section"], r["ref"]): r for r in rows}


def _mentions(person: str, it: dict) -> bool:
    return bool(re.search(rf"\b{re.escape(person)}\b", f"{it['text']} {it['quote']}", re.I))


def _transfer_for(person: str, item_id: int):
    return db.one("SELECT * FROM transfers WHERE item_id=? AND lower(from_owner)=lower(?) ORDER BY "
                  "CASE status WHEN 'completed' THEN 0 WHEN 'approved' THEN 1 WHEN 'proposed' THEN 2 ELSE 3 END, id DESC",
                  (item_id, person))


def build(person: str, role: str) -> dict:
    """The whole checklist for one leaving person, as one reader with `role` may see it."""
    ensure_schema()
    person = (person or "").strip()
    items = handover.list_items("WHERE i.review_status!='rejected'")
    lookup = {i["id"]: i for i in items}
    saved = _saved(person)
    entries, seen = [], set()

    def new(section, ref, item=None, label="", detail="", **kw):
        s = saved.get((section, ref)) or {}
        e = {"section": section, "ref": ref, "item_id": item["id"] if item else None, "label": label, "detail": detail,
             "done": bool(s.get("done")), "done_by": s.get("done_by"), "done_at": s.get("done_at"), "note": s.get("note") or "",
             "custom": False, "locked": False, "locked_reason": "", "auto": False, "restricted": False,
             "reasons": [], "score": 0, "row_id": s.get("id")}
        e.update(kw)
        entries.append(e)
        return e

    owned = [i for i in items if (i["owner"] or "").strip().lower() == person.lower()]
    # items that already moved to someone else through a completed transfer still count as work done
    moved = db.q("SELECT item_id, to_owner, completed_by, completed_at FROM transfers WHERE lower(from_owner)=lower(?) "
                 "AND status='completed'", (person,))
    moved = {m["item_id"]: m for m in moved if m["item_id"] in lookup}
    ids = {i["id"] for i in owned} | set(moved)
    for iid in sorted(ids):
        it = lookup[iid]
        section = TYPE_SECTION.get(it["type"], "transfers")
        ref = f"item:{iid}"
        seen.add(iid)
        if not roles.can_see(role, it["visibility"]):
            new(section, ref, it, f"Restricted item #{iid} ({config.TYPE_LABEL.get(it['type'], it['type'])})",
                "Ask a Lead. The text is hidden for your role.", restricted=True, locked=True)
            continue
        t = _transfer_for(person, iid)
        e = new(section, ref, it, it["text"], f"{config.TYPE_LABEL.get(it['type'], it['type'])} | source: {it['source_name']}")
        if iid in moved or (t and t["status"] == "completed"):
            m = moved.get(iid) or t
            e.update(done=True, auto=True, done_by=m["completed_by"], done_at=m["completed_at"],
                     detail=e["detail"] + f" | handed to {m['to_owner']}")
        if section == "transfers":
            e.update(locked=True, locked_reason=LOCK_TRANSFER)
        if not e["done"]:
            _why_open(e, it, t, lookup, role, person, section)

    # dependencies, blockers and questions that only mention the person
    for it in items:
        if it["id"] in seen or it["type"] not in MENTION_TYPES or not roles.can_see(role, it["visibility"]):
            continue
        if it["type"] == "owner" and it["owner"]:
            continue                    # an ownership line with a named owner is not a dependency
        if (it["owner"] or "").strip().lower() != person.lower() and _mentions(person, it):
            e = new("deps", f"item:{it['id']}", it, it["text"],
                    f"{config.TYPE_LABEL.get(it['type'], it['type'])} | names {person}"
                    + (f" | owner: {it['owner']}" if it["owner"] else " | nobody owns it")
                    + f" | source: {it['source_name']}")
            if not e["done"]:
                _why_open(e, it, None, lookup, role, person, "deps")
                if not it["owner"]:
                    e["reasons"].append(f"Names {person} and nobody owns it")
                    e["score"] += 2

    # one documentation line per technical topic the person owns (or handed over) items in; visible items only
    topics = {}
    # items already handed over still count: the know-how behind them has to be written down either way
    for it in owned + [lookup[i] for i in moved]:
        if it["topic"] in TECH_TOPICS and roles.can_see(role, it["visibility"]):
            topics.setdefault(it["topic"], []).append(it)
    for topic in TECH_TOPICS:
        if topic in topics:
            group = topics[topic]
            e = new("docs", f"topic:{topic}", None, f"Write down how {topic} works so a successor can take over",
                    f"{len(group)} item(s) about {topic} are owned by {person}, for example #{group[0]['id']}")
            if not e["done"]:
                e["reasons"].append("Not documented yet")
                e["score"] += 1

    # lines people added by hand
    for r in db.q("SELECT * FROM checklist WHERE lower(person)=lower(?) AND custom=1 ORDER BY id", (person,)):
        e = new(r["section"], f"custom:{r['id']}", None, r["label"], f"Added by {r['created_by']}", custom=True)
        if not e["done"]:
            e["reasons"].append("Added by hand")
            e["score"] += 1

    return _summarise(person, entries)


def _why_open(e: dict, it: dict, t, lookup: dict, role: str, person: str, section: str) -> None:
    if section in ("transfers", "tasks"):
        if not t or t["status"] in ("rejected", "cancelled"):
            e["reasons"].append("No new owner proposed yet")
            e["score"] += 3
        elif t["status"] == "proposed":
            e["reasons"].append("Transfer waiting for a Lead to approve")
            e["score"] += 2
        elif t["status"] == "approved":
            e["reasons"].append(f"Waiting for {t['to_owner']} to complete the transfer")
            e["score"] += 1
    for f in flags.describe(it, lookup, role):
        if f.startswith(("Conflicts", "Unverified")):
            e["reasons"].append(f)
            e["score"] += 3 if f.startswith("Conflicts") else 2
    if it["review_status"] == "pending":
        e["reasons"].append("Not reviewed by a Lead yet")
        e["score"] += 1
    if not e["reasons"]:
        e["reasons"].append("Still open")
        e["score"] += 1


def _summarise(person: str, entries: list) -> dict:
    order = {k: n for n, (k, _) in enumerate(SECTIONS)}
    secs = []
    for key, title in SECTIONS:
        rows = [e for e in entries if e["section"] == key]
        rows.sort(key=lambda e: (e["done"], -e["score"], e["item_id"] or 10 ** 9, e["label"]))
        live = [e for e in rows if not e["restricted"]]
        done = sum(1 for e in live if e["done"])
        secs.append({"key": key, "title": title, "entries": rows, "done": done, "total": len(live),
                     "percent": round(100 * done / len(live)) if live else 100})
    live = [e for e in entries if not e["restricted"]]
    done = sum(1 for e in live if e["done"])
    open_ = sorted((e for e in live if not e["done"]), key=lambda e: (-e["score"], order[e["section"]], e["item_id"] or 10 ** 9))
    return {"person": person, "sections": secs, "total": len(live), "done": done, "left": len(live) - done,
            "percent": round(100 * done / len(live)) if live else 0,
            "attention": open_, "urgent": sum(1 for e in open_ if e["score"] >= URGENT_AT),
            "restricted": sum(1 for e in entries if e["restricted"]), "ready": bool(live) and done == len(live)}


def find(data: dict, section: str, ref: str):
    return next((e for s in data["sections"] if s["key"] == section for e in s["entries"] if e["ref"] == ref), None)


# ------------------------------------------------------------------ change state
def _entry_for_change(user: str, role: str, person: str, section: str, ref: str) -> dict:
    if section not in TITLE:
        raise ValueError("Unknown checklist section.")
    if not can_edit(user, role, person):
        raise PermissionError("Only a Lead or the person who is leaving can change this checklist.")
    e = find(build(person, role), section, ref)
    if not e:
        raise ValueError("That checklist line was not found.")
    if e["restricted"]:
        raise PermissionError("That item is restricted for your role.")
    return e


def set_done(user: str, role: str, person: str, section: str, ref: str, done: bool) -> bool:
    """Tick or untick one line. Returns True if something changed."""
    e = _entry_for_change(user, role, person, section, ref)
    if e["locked"]:
        raise ValueError(e["locked_reason"] or "This line cannot be ticked by hand.")
    if e["auto"]:
        raise ValueError("This was completed by a transfer and cannot be unticked here.")
    if bool(done) == e["done"]:
        return False
    row = db.one("SELECT id FROM checklist WHERE lower(person)=lower(?) AND section=? AND ref=?", (person, section, ref))
    when = db.now() if done else None
    if row:
        db.x("UPDATE checklist SET done=?, done_by=?, done_at=? WHERE id=?", (1 if done else 0, user if done else None, when, row["id"]))
    else:
        db.x("INSERT INTO checklist(person,section,ref,label,custom,done,done_by,done_at,created_by,created_at) "
             "VALUES (?,?,?,?,0,?,?,?,?,?)", (person, section, ref, e["label"][:120], 1 if done else 0,
                                              user if done else None, when, user, db.now()))
    db.log(user, "checklist_done" if done else "checklist_undone", f"{person}: {TITLE[section]}", e["label"][:120])
    return True


def set_note(user: str, role: str, person: str, section: str, ref: str, note: str) -> None:
    e = _entry_for_change(user, role, person, section, ref)
    note = re.sub(r"[\x00-\x08\x0b-\x1f]", "", (note or "")).strip()[:300]
    row = db.one("SELECT id FROM checklist WHERE lower(person)=lower(?) AND section=? AND ref=?", (person, section, ref))
    if row:
        db.x("UPDATE checklist SET note=? WHERE id=?", (note, row["id"]))
    else:
        db.x("INSERT INTO checklist(person,section,ref,label,custom,done,note,created_by,created_at) VALUES (?,?,?,?,0,0,?,?,?)",
             (person, section, ref, e["label"][:120], note, user, db.now()))
    db.log(user, "checklist_note", f"{person}: {TITLE[section]}", e["label"][:120])


def add_custom(user: str, role: str, person: str, section: str, label: str) -> int:
    ensure_schema()
    if section not in TITLE:
        raise ValueError("Choose a section.")
    if not (person or "").strip():
        raise ValueError("Choose who is leaving.")
    if not can_edit(user, role, person):
        raise PermissionError("Only a Lead or the person who is leaving can add lines.")
    label = " ".join((label or "").split())
    if not label:
        raise ValueError("Write what needs to be done.")
    if len(label) > 120:
        raise ValueError("Keep it under 120 characters.")
    rid = db.x("INSERT INTO checklist(person,section,ref,label,custom,done,created_by,created_at) VALUES (?,?,?,?,1,0,?,?)",
               (person.strip(), section, "pending", label, user, db.now()))
    db.x("UPDATE checklist SET ref=? WHERE id=?", (f"custom:{rid}", rid))
    db.log(user, "checklist_add", f"{person}: {TITLE[section]}", label)
    return rid


def delete_custom(user: str, role: str, person: str, ref: str) -> None:
    if not can_edit(user, role, person):
        raise PermissionError("Only a Lead or the person who is leaving can remove lines.")
    row = db.one("SELECT * FROM checklist WHERE lower(person)=lower(?) AND ref=? AND custom=1", (person, ref))
    if not row:
        raise ValueError("Only lines added by hand can be removed.")
    db.x("DELETE FROM checklist WHERE id=?", (row["id"],))
    db.log(user, "checklist_remove", f"{person}: {TITLE[row['section']]}", row["label"][:120])


# ------------------------------------------------------------------ export
def export_markdown(data: dict) -> str:
    p = data["person"]
    lines = [f"# Departure checklist: {p}", f"{data['done']} of {data['total']} done ({data['percent']}%). "
             + ("Ready to leave." if data["ready"] else f"{data['left']} left, {data['urgent']} need attention."), ""]
    if data["restricted"]:
        lines += [f"_{data['restricted']} restricted item(s) are not included in these numbers._", ""]
    for s in data["sections"]:
        lines.append(f"## {s['title']} ({s['done']}/{s['total']})")
        rows = [e for e in s["entries"] if not e["restricted"]]
        if not rows:
            lines.append("- Nothing found.")
        for e in rows:
            tick = "x" if e["done"] else " "
            extra = f" (done by {e['done_by']} on {e['done_at'][:10]})" if e["done"] and e["done_by"] else ""
            lines.append(f"- [{tick}] {e['label']}{extra}")
            if not e["done"] and e["reasons"]:
                lines.append(f"  - Needs: {'; '.join(e['reasons'])}")
            if e["note"]:
                lines.append(f"  - Note: {e['note']}")
        lines.append("")
    return "\n".join(lines)
