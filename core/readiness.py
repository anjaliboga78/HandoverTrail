"""Readiness score, handover status flow and the 'who is leaving' view. All numbers come from real data."""
from __future__ import annotations
from . import db, handover, roles

FLOW = ["Draft", "Under review", "Approved", "Shared", "Acknowledged"]


def status_flow() -> str:
    """Draft > Under review > Approved > Shared > Acknowledged, worked out from what has happened."""
    items = db.q("SELECT review_status FROM items")
    if not items:
        return "Draft"
    h = handover.current_handover()
    if not h:
        return "Under review" if any(i["review_status"] != "pending" for i in items) else "Draft"
    if db.one("SELECT 1 AS x FROM acks WHERE handover_id=?", (h["id"],)):
        return "Acknowledged"
    if db.one("SELECT 1 AS x FROM audit_log WHERE action='view_handover' AND target=? AND user_name NOT IN "
              "(SELECT name FROM users WHERE role='Lead')", (f"v{h['version']}",)):
        return "Shared"
    return "Approved"


# Eight measurable parts, 100 points in total. Every number comes from stored data; nothing is estimated.
WEIGHTS = {"review": 15, "evidence": 15, "docs": 15, "ownership": 15, "transfers": 15,
           "checklist": 10, "deps": 10, "ack": 5}
LABELS = {"review": "Reviewed by a human", "evidence": "Verified evidence", "docs": "Documentation completeness",
          "ownership": "Task ownership", "transfers": "Responsibility transfers", "checklist": "Checklist items done",
          "deps": "Dependencies and conflicts resolved", "ack": "Receipt acknowledged"}
DOC_TYPES = ("decision", "owner", "next_action", "contact", "deadline", "risk")   # what a useful handover should cover
OWNED_TYPES = ("next_action", "deadline", "owner")                                # things that must name a person
TRANSFER_CREDIT = {"completed": 1.0, "approved": 0.6, "proposed": 0.3}            # partial credit while a transfer is in flight
SCREEN = {"review": "3. Review and approve", "transfer": "5. Transfer responsibilities",
          "checklist": "6. Departure checklist", "handover": "4. Handover"}
MAX_IDS = 8


def band(score: int) -> str:
    return ("Ready to hand over" if score >= 85 else "Nearly there" if score >= 65
            else "In progress" if score >= 35 else "Just started")


def _status(pct: int) -> str:
    return "Strong" if pct >= 85 else "Needs work" if pct >= 50 else "Weak"


def _scope() -> tuple:
    """(leavers, people checked for checklist and dependencies). Leavers = anyone with a transfer or a checklist.
    If nobody is marked as leaving yet, the checklist and dependency parts look at every named owner."""
    from . import checklist, transfer
    transfer.ensure_schema()
    everyone = checklist.people()
    canon = {n.lower(): n for n in everyone}
    marked = {r["from_owner"].strip() for r in db.q("SELECT DISTINCT from_owner FROM transfers WHERE from_owner IS NOT NULL")}
    marked |= {r["person"].strip() for r in db.q("SELECT DISTINCT person FROM checklist")}
    leavers = sorted({canon.get(m.lower(), m) for m in marked if m}, key=str.lower)
    return leavers, (leavers or everyone)


def _action(text: str, where: str, ids=(), vis=None, role: str = "Intern", hidden: int = 0) -> dict:
    """One thing to do. Restricted items are only counted, never named: ids are limited to what `role` may see."""
    shown = [i for i in ids if vis is None or roles.can_see(role, vis.get(i, "Lead"))]
    hidden += len(list(ids)) - len(shown)
    return {"text": text, "where": where, "ids": shown[:MAX_IDS], "more": max(0, len(shown) - MAX_IDS), "hidden": hidden}


def _part(key: str, value: float, detail: str, actions: list) -> dict:
    pct = round(100 * value)
    w = WEIGHTS[key]
    return {"key": key, "label": LABELS[key], "weight": w, "pct": pct, "points": round(w * value, 1),
            "status": _status(pct), "detail": detail, "actions": actions if pct < 100 else []}


def readiness(role: str = "Intern") -> dict:
    """0-100 score from eight measurable parts, with a breakdown and what to improve.

    The score uses ALL data so it is the same for every reader. What is NAMED in the explanation depends on `role`:
    restricted items are only counted ("2 restricted item(s)"), never listed. Read-only: it changes nothing."""
    from . import checklist, transfer
    items = db.q("SELECT id, type, text, owner, topic, verify_status, review_status, is_conflict, is_gap, visibility FROM items")
    if not items:
        return {"score": 0, "band": band(0), "parts": {}, "breakdown": [], "improve": [],
                "todo": ["Import sources and run extraction."]}
    live = [i for i in items if i["review_status"] != "rejected"]
    n = max(len(live), 1)
    vis = {i["id"]: i["visibility"] for i in items}
    A = lambda text, where, ids=(), hidden=0: _action(text, where, list(ids), vis, role, hidden)  # noqa: E731
    leavers, scope = _scope()
    built = {p: checklist.build(p, "Lead") for p in dict.fromkeys(leavers + scope)}   # built once, read several times
    sect = lambda people, *keys: [e for p in people for s in built[p]["sections"] if s["key"] in keys  # noqa: E731
                                  for e in s["entries"]]
    h = handover.current_handover()
    parts = []

    # 1. human review
    pending = [i["id"] for i in live if i["review_status"] == "pending"]
    approved = sum(1 for i in live if i["review_status"] == "approved")
    parts.append(_part("review", approved / n, f"{approved} of {len(live)} item(s) approved by a person.",
                       [A(f"{len(pending)} item(s) still need a decision: approve, edit or reject.", SCREEN["review"], pending)]
                       if pending else []))

    # 2. verified evidence (a quote found word for word counts fully, a close match counts half)
    ver = [i for i in live if i["verify_status"] == "verified"]
    appr = [i["id"] for i in live if i["verify_status"] == "approximate"]
    unv = [i["id"] for i in live if i["verify_status"] == "unverified"]
    acts = []
    if unv:
        acts.append(A(f"{len(unv)} item(s) have a quote that was not found in the source: check the source or reject them.",
                      SCREEN["review"], unv))
    if appr:
        acts.append(A(f"{len(appr)} item(s) only have an approximate quote match: confirm them against the source.",
                      SCREEN["review"], appr))
    parts.append(_part("evidence", (len(ver) + 0.5 * len(appr)) / n,
                       f"{len(ver)} verified, {len(appr)} approximate (half credit), {len(unv)} unverified.", acts))

    # 3. documentation completeness: topics covered + technical know-how written down
    present = {i["type"] for i in live}
    missing = [t for t in DOC_TYPES if t not in present]
    coverage = (len(DOC_TYPES) - len(missing)) / len(DOC_TYPES)
    docs = sect(scope, "docs")
    docs_done = sum(1 for e in docs if e["done"])
    docs_ratio = docs_done / len(docs) if docs else 1.0
    acts = []
    if missing:
        acts.append(A("Nothing was found about: " + ", ".join(config_label(t) for t in missing)
                      + ". Add it with 'Add item' or confirm there is none.", SCREEN["review"]))
    if docs_done < len(docs):
        acts.append(A(f"{len(docs) - docs_done} technical topic(s) are not written down yet "
                      f"({', '.join(sorted({e['ref'].split(':')[1] for e in docs if not e['done']}))}).", SCREEN["checklist"]))
    parts.append(_part("docs", 0.5 * coverage + 0.5 * docs_ratio,
                       f"{len(DOC_TYPES) - len(missing)} of {len(DOC_TYPES)} key kinds of knowledge present; "
                       f"{docs_done} of {len(docs)} technical topic(s) documented.", acts))

    # 4. task ownership: every task, deadline and ownership line names a person
    tasks = [i for i in live if i["type"] in OWNED_TYPES]
    noown = [i["id"] for i in tasks if not (i["owner"] or "").strip()]
    parts.append(_part("ownership", (len(tasks) - len(noown)) / len(tasks) if tasks else 1.0,
                       (f"{len(tasks) - len(noown)} of {len(tasks)} task(s), deadline(s) and ownership line(s) name an owner."
                        if tasks else "No tasks or deadlines were found."),
                       [A(f"{len(noown)} item(s) have no owner: use 'Find an owner' in the review screen.", SCREEN["review"], noown)]
                       if noown else []))

    # 5. responsibility transfers (leavers only; completed = full credit, approved = 0.6, proposed = 0.3)
    t_total, t_credit, t_open = 0, 0.0, 0
    t_ids = {"proposed": [], "approved": [], "none": []}
    for e in sect(leavers, "transfers"):
        if e["item_id"] is None:
            continue
        t_total += 1
        if e["done"]:
            t_credit += 1
            continue
        t = db.one("SELECT status FROM transfers WHERE item_id=? AND status IN ('proposed','approved') "
                   "ORDER BY id DESC LIMIT 1", (e["item_id"],))
        t_credit += TRANSFER_CREDIT.get(t["status"], 0) if t else 0
        t_ids[t["status"] if t else "none"].append(e["item_id"])
        t_open += 1
    acts = []
    if not leavers:
        acts.append(A("Nobody is marked as leaving yet. Pick who is leaving and give their responsibilities new owners.",
                      SCREEN["transfer"]))
    else:
        for stage, text in (("none", "{n} responsibility(ies) have no new owner proposed."),
                            ("proposed", "{n} transfer(s) wait for a Lead to approve."),
                            ("approved", "{n} approved transfer(s) wait for the new owner or a Lead to complete them.")):
            if t_ids[stage]:
                acts.append(A(text.format(n=len(t_ids[stage])), SCREEN["transfer"], t_ids[stage]))
    parts.append(_part("transfers", (t_credit / t_total if t_total else 1.0) if leavers else 0.0,
                       (f"{_who(leavers)}: {t_total - t_open} of {t_total} responsibility(ies) handed over."
                        if leavers else "No transfer has been started."), acts))

    # 6. pending checklist items (tasks and decisions; documentation, transfers and dependencies are scored on their own)
    c_all = sect(scope, "tasks", "decisions")
    c_open = sorted((e for e in c_all if not e["done"]), key=lambda e: -e["score"])   # most urgent first
    # counts and ids only: an entry's reasons were built for a Lead and may quote items a smaller role cannot see
    parts.append(_part("checklist", (len(c_all) - len(c_open)) / len(c_all) if c_all else 1.0,
                       f"{len(c_all) - len(c_open)} of {len(c_all)} task and decision line(s) closed, for {_who(scope)}.",
                       [A(f"{len(c_open)} checklist line(s) are still open, most urgent first.", SCREEN["checklist"],
                          [e["item_id"] for e in c_open if e["item_id"]])] if c_open else []))

    # 7. unresolved dependencies, blockers, open questions and conflicts
    d_all = {e["ref"]: e for e in sect(scope, "deps")}
    d_open = [e for e in d_all.values() if not e["done"]]
    conf = [i for i in live if i["is_conflict"]]
    conf_open = [i["id"] for i in conf if i["review_status"] != "approved"]
    total = len(d_all) + len(conf)
    solved = (len(d_all) - len(d_open)) + (len(conf) - len(conf_open))
    acts = []
    if d_open:
        acts.append(A(f"{len(d_open)} dependency(ies), blocker(s) or open question(s) are not resolved.", SCREEN["checklist"],
                      [e["item_id"] for e in d_open if e["item_id"]]))
    if conf_open:
        acts.append(A(f"{len(conf_open)} conflicting decision(s) need one agreed answer.", SCREEN["review"], conf_open))
    parts.append(_part("deps", solved / total if total else 1.0,
                       f"{solved} of {total} dependency, blocker, question and conflict line(s) resolved.", acts))

    # 8. receipt acknowledged
    people = db.q("SELECT name FROM users WHERE role!='Lead'")
    acked = 0.0
    if h and people:
        got = db.q("SELECT DISTINCT user_name FROM acks WHERE handover_id=?", (h["id"],))
        acked = len(got) / len(people)
    parts.append(_part("ack", acked,
                       "No handover has been approved yet." if not h else f"{round(acked * len(people))} of {len(people)} reader(s) acknowledged.",
                       [A("A Lead must approve and share the handover.", SCREEN["review"])] if not h else
                       [A("Not everyone has acknowledged the handover.", SCREEN["handover"])]))

    score = round(sum(p["points"] for p in parts))
    # biggest losses first, so the person knows where the next points are
    improve = []
    for p in sorted(parts, key=lambda p: p["points"] - p["weight"]):
        lost = round(p["weight"] - p["points"], 1)
        if lost > 0 and p["actions"]:
            improve.append({"key": p["key"], "label": p["label"], "lost": lost, **p["actions"][0]})
    return {"score": score, "band": band(score), "parts": {p["label"]: p["pct"] for p in parts}, "breakdown": parts,
            "improve": improve, "todo": [f"{i['text']}" for i in improve[:5]]}


def _who(names: list) -> str:
    return ", ".join(names) if 0 < len(names) <= 3 else f"{len(names)} owner(s)" if names else "nobody yet"


def config_label(t: str) -> str:
    from . import config
    return config.TYPE_LABEL.get(t, t).lower()


def leaving_people() -> list:
    rows = db.q("SELECT DISTINCT owner FROM items WHERE owner IS NOT NULL AND owner!='' ORDER BY owner")
    return [r["owner"] for r in rows]


def leaving_summary(person: str) -> dict:
    """What would be lost if this person left: everything where they are the named owner."""
    like = f"%{person}%"
    owned = db.q("SELECT i.*, s.name AS source_name FROM items i JOIN sources s ON s.id=i.source_id "
                 "WHERE i.owner LIKE ? AND i.review_status!='rejected' ORDER BY i.item_date, i.id", (like,))
    mentions = db.q("SELECT COUNT(*) AS n FROM items WHERE (text LIKE ? OR quote LIKE ?) AND "
                    "(owner IS NULL OR owner NOT LIKE ?)", (like, like, like))[0]["n"]
    sole = [i for i in owned if i["type"] in ("decision", "owner", "blocker", "risk", "dependency")]
    return {"person": person, "owned": owned, "sole": sole, "mentions": mentions,
            "unreviewed": sum(1 for i in owned if i["review_status"] == "pending"),
            "unverified": sum(1 for i in owned if i["verify_status"] == "unverified")}
