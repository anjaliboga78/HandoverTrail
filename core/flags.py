"""Step 3 (continued) - Verify: conflicts, gaps and recurring problems.

Flags are stored as data (ids and booleans), never as text that names a source, so a reader
who may not see a restricted source can never learn its name or contents from a flag.
"""
from __future__ import annotations
import json
import re
from collections import defaultdict

from . import db, roles

TECH = {"mysql": "MySQL", "postgresql": "PostgreSQL", "postgres": "PostgreSQL", "mongodb": "MongoDB",
        "sqlite": "SQLite", "firebase": "Firebase", "razorpay": "Razorpay", "stripe": "Stripe",
        "paypal": "PayPal"}
MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
R_DATE = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTHS})\b", re.I)
CONFLICT_TOPICS = {"database", "deadline", "payments"}


def signature(text: str) -> frozenset:
    t = text.lower()
    sig = {TECH[k] for k in TECH if re.search(rf"\b{k}\b", t)}
    sig |= {f"{int(m.group(1))} {m.group(2).lower()}" for m in R_DATE.finditer(text)}
    return frozenset(sig)


def recompute() -> None:
    db.x("UPDATE items SET is_conflict=0, is_gap=0, is_recurring=0, conflict_with='[]'")
    items = db.q("SELECT id, source_id, type, owner, topic, text FROM items")
    # gaps: ownership with nobody named, or an action with no owner
    for i in items:
        if (i["type"] == "owner" and not i["owner"]) or (i["type"] == "next_action" and not i["owner"]):
            db.x("UPDATE items SET is_gap=1 WHERE id=?", (i["id"],))
    # conflicts between decisions on the same topic
    groups = defaultdict(list)
    for i in items:
        if i["type"] == "decision" and i["topic"] in CONFLICT_TOPICS:
            sig = signature(i["text"])
            if sig:
                groups[i["topic"]].append((i, sig))
    for _, members in groups.items():
        if len({s for _, s in members}) < 2:
            continue
        for i, sig in members:
            others = [j["id"] for j, s in members if s != sig and j["source_id"] != i["source_id"]]
            if others:
                db.x("UPDATE items SET is_conflict=1, conflict_with=? WHERE id=?", (json.dumps(others), i["id"]))
    # recurring problems: the same risk or blocker topic in three or more different sources
    rec = defaultdict(set)
    for i in items:
        if i["type"] in ("risk", "blocker") and i["topic"] != "general":
            rec[(i["type"], i["topic"])].add(i["source_id"])
    for (typ, topic), sources in rec.items():
        if len(sources) >= 3:
            db.x("UPDATE items SET is_recurring=1 WHERE type=? AND topic=?", (typ, topic))


def describe(item: dict, all_items: dict, role: str) -> list:
    """Human-readable flags for ONE reader. Hidden counterparts are never mentioned."""
    out = []
    if item.get("is_gap"):
        out.append("Gap: no owner found")
    if item.get("is_recurring"):
        out.append("Recurring problem: appears in several sources")
    if item.get("is_conflict"):
        ids = json.loads(item.get("conflict_with") or "[]")
        vis = [all_items[i] for i in ids if i in all_items and roles.can_see(role, all_items[i]["visibility"])]
        if vis:
            o = vis[0]
            out.append(f"Conflicts with item #{o['id']}: \"{o['text'][:70]}\"")
    if item.get("verify_status") == "unverified":
        out.append("Unverified: the quote was not found in the source")
    return out
