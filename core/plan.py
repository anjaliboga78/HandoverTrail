"""Step 5 - an action plan built ONLY from approved items the reader may see.

Rule-based on purpose: every line points back to the items it came from, so nothing is invented.
"""
from __future__ import annotations


def _short(t: str, n: int = 120) -> str:
    t = t.strip().rstrip(".")
    return t if len(t) <= n else t[:n - 1] + "..."


def build_plan(items: list) -> dict:
    plan = {"Day 1": [], "Week 1": [], "Month 1": []}
    used = set()

    def put(bucket, text, item):
        if item["id"] in used:
            return
        used.add(item["id"])
        plan[bucket].append({"text": text, "ids": [item["id"]]})

    # recurring problems: one line for the whole group, citing every item in it
    groups = {}
    for it in items:
        if it.get("is_recurring") and it["type"] == "risk":
            groups.setdefault(it["topic"], []).append(it)
    for _, group in groups.items():
        ids = [g["id"] for g in group]
        used.update(ids)
        plan["Week 1"].append({
            "text": f"Look into this recurring problem first (it shows up in {len(group)} places): {_short(group[0]['text'])}",
            "ids": ids})
    for it in items:
        if it.get("is_conflict"):
            put("Month 1", f"Get the owner to resolve this conflict: {_short(it['text'])}", it)
        elif it.get("is_gap"):
            t = it["text"]
            if t.startswith("No owner for "):
                put("Month 1", f"Find an owner for {_short(t[len('No owner for '):])}", it)
            else:
                put("Month 1", f"Find an owner: {_short(t.replace('No owner: ', ''))}", it)
    for it in items:
        t = it["type"]
        if t == "contact":
            put("Day 1", f"Introduce yourself to {it.get('owner') or 'the contact'}, a key contact named in the notes", it)
        elif t == "owner" and it.get("owner"):
            put("Day 1", f"Talk to {it['owner']} about what they own: {_short(it['text'])}", it)
        elif t == "blocker":
            put("Week 1", f"Unblock: {_short(it['text'])}", it)
        elif t == "risk":
            put("Week 1", f"Look into the risk: {_short(it['text'])}", it)
        elif t == "dependency":
            put("Week 1", f"Arrange what is needed: {_short(it['text'])}", it)
        elif t == "open_question":
            put("Week 1", f"Find an answer: {_short(it['text'])}", it)
        elif t == "deadline":
            put("Week 1", f"Check the deadline and who is on it: {_short(it['text'])}", it)
        elif t == "next_action":
            put("Month 1", f"Follow through: {_short(it['text'])}", it)
    # recurring problems first in Week 1
    plan["Week 1"].sort(key=lambda p: 0 if "recurring" in p["text"] else 1)
    return plan
