"""Responsibility Transfer: hand each thing a leaving person owns to a named new owner, with approval.

Flow per responsibility:  Proposed  >  Approved (by a Lead)  >  Completed (new owner or Lead confirms)
                          or Rejected / Cancelled.  Every step is saved in transfer_events and the audit log.
Completing a transfer changes the item's owner (saved as an item version). The evidence quote is never changed.
"""
from __future__ import annotations
from . import db, roles

ACTIVE = ("proposed", "approved")
LABEL = {"proposed": "Waiting for approval", "approved": "Approved, waiting for the new owner",
         "completed": "Completed", "rejected": "Rejected", "cancelled": "Cancelled"}

def ensure_schema() -> None:
    """Tables are created by db.init(); this also covers databases made before this feature existed."""
    from contextlib import closing
    with closing(db.connect()) as c:
        c.executescript(db.TRANSFER_SCHEMA)
        c.commit()


def _event(tid: int, event: str, user: str, note: str = "") -> None:
    db.x("INSERT INTO transfer_events(transfer_id,event,by_user,at,note) VALUES (?,?,?,?,?)",
         (tid, event, user, db.now(), note))


def responsibilities(person: str) -> list:
    """Everything this person is the named owner of (rejected items excluded), with any live transfer."""
    ensure_schema()
    rows = db.q("SELECT i.id, i.type, i.text, i.owner, i.item_date, i.verify_status, i.review_status, i.visibility, "
                "s.name AS source_name FROM items i JOIN sources s ON s.id=i.source_id "
                "WHERE lower(trim(i.owner))=lower(trim(?)) AND i.review_status!='rejected' "
                "ORDER BY i.item_date, i.id", (person,))
    for r in rows:
        r["transfer"] = db.one("SELECT * FROM transfers WHERE item_id=? AND status IN ('proposed','approved') "
                               "ORDER BY id DESC LIMIT 1", (r["id"],))
    return rows


def owners() -> list:
    ensure_schema()
    return [r["owner"] for r in db.q("SELECT DISTINCT owner FROM items WHERE owner IS NOT NULL AND trim(owner)!='' "
                                     "AND review_status!='rejected' ORDER BY owner")]


def propose(user: str, role: str, item_id: int, to_owner: str, reason: str = "") -> int:
    ensure_schema()
    if role not in ("Lead", "Core"):
        raise PermissionError("Only a Lead or Core member can propose a transfer.")
    item = db.one("SELECT * FROM items WHERE id=?", (item_id,))
    if not item or item["review_status"] == "rejected":
        raise ValueError("That item is not available.")
    if not roles.can_see(role, item["visibility"]):
        raise PermissionError("You cannot see that item.")
    to_owner = (to_owner or "").strip()
    if not to_owner:
        raise ValueError("Choose or type the new owner.")
    if len(to_owner) > 60:
        raise ValueError("The new owner's name is too long.")
    frm = (item["owner"] or "").strip()
    if not frm:
        raise ValueError("This item has no owner yet. Use 'Find an owner' in the review screen instead.")
    if to_owner.lower() == frm.lower():
        raise ValueError("The new owner is the same person.")
    if db.one("SELECT 1 AS x FROM transfers WHERE item_id=? AND status IN ('proposed','approved')", (item_id,)):
        raise ValueError("This responsibility already has a transfer in progress.")
    tid = db.x("INSERT INTO transfers(item_id,from_owner,to_owner,status,reason,proposed_by,proposed_at) "
               "VALUES (?,?,?,?,?,?,?)", (item_id, frm, to_owner, "proposed", (reason or "").strip()[:300], user, db.now()))
    _event(tid, "proposed", user, f"{frm} -> {to_owner}")
    db.log(user, "transfer_propose", f"item #{item_id}", f"{frm} -> {to_owner}")
    return tid


def _get(tid: int) -> dict:
    t = db.one("SELECT * FROM transfers WHERE id=?", (tid,))
    if not t:
        raise ValueError("Transfer not found.")
    return t


def decide(user: str, role: str, tid: int, approve: bool, note: str = "") -> None:
    """Approval gate. Only a Lead; and not your own proposal when another Lead exists."""
    ensure_schema()
    if role != "Lead":
        raise PermissionError("Only a Lead can approve or reject a transfer.")
    t = _get(tid)
    if t["status"] != "proposed":
        raise ValueError("This transfer is not waiting for approval.")
    others = db.one("SELECT 1 AS x FROM users WHERE role='Lead' AND name!=?", (user,))
    if t["proposed_by"] == user and others:
        raise PermissionError("Another Lead must approve a transfer you proposed.")
    status = "approved" if approve else "rejected"
    db.x("UPDATE transfers SET status=?, decided_by=?, decided_at=? WHERE id=?", (status, user, db.now(), tid))
    _event(tid, status, user, note)
    db.log(user, f"transfer_{status}", f"item #{t['item_id']}", f"{t['from_owner']} -> {t['to_owner']}")


def complete(user: str, role: str, tid: int) -> None:
    """Finalize. Allowed only after approval, by the new owner or a Lead. Updates the item's owner."""
    ensure_schema()
    t = _get(tid)
    if t["status"] != "approved":
        raise ValueError("A transfer must be approved before it can be completed.")
    if not (role == "Lead" or user.lower() == t["to_owner"].lower()):
        raise PermissionError("Only the new owner or a Lead can complete this transfer.")
    item = db.one("SELECT * FROM items WHERE id=?", (t["item_id"],))
    if (item["owner"] or "").strip().lower() != t["from_owner"].strip().lower():
        raise ValueError("The item's owner changed since this was proposed. Cancel and propose again.")
    db.x("INSERT INTO item_versions(item_id,action,old_text,new_text,changed_by,changed_at) VALUES (?,?,?,?,?,?)",
         (item["id"], "owner_transfer", f"owner: {item['owner']}", f"owner: {t['to_owner']}", user, db.now()))
    db.x("UPDATE items SET owner=? WHERE id=?", (t["to_owner"], item["id"]))
    db.x("UPDATE transfers SET status='completed', completed_by=?, completed_at=? WHERE id=?", (user, db.now(), tid))
    _event(tid, "completed", user)
    db.log(user, "transfer_complete", f"item #{item['id']}", f"{t['from_owner']} -> {t['to_owner']}")


def cancel(user: str, role: str, tid: int) -> None:
    ensure_schema()
    t = _get(tid)
    if t["status"] not in ACTIVE:
        raise ValueError("Only a transfer in progress can be cancelled.")
    if not (role == "Lead" or user == t["proposed_by"]):
        raise PermissionError("Only a Lead or the proposer can cancel.")
    db.x("UPDATE transfers SET status='cancelled', decided_by=?, decided_at=? WHERE id=?", (user, db.now(), tid))
    _event(tid, "cancelled", user)
    db.log(user, "transfer_cancel", f"item #{t['item_id']}", f"{t['from_owner']} -> {t['to_owner']}")


def list_transfers(statuses=None, person=None) -> list:
    ensure_schema()
    sql = ("SELECT t.*, i.type, i.text FROM transfers t JOIN items i ON i.id=t.item_id")
    cond, par = [], []
    if statuses:
        cond.append("t.status IN (%s)" % ",".join("?" * len(statuses)))
        par += list(statuses)
    if person:
        cond.append("lower(t.from_owner)=lower(?)")
        par.append(person)
    return db.q(sql + (" WHERE " + " AND ".join(cond) if cond else "") + " ORDER BY t.id DESC", tuple(par))


def history(tid: int) -> list:
    ensure_schema()
    return db.q("SELECT at AS time, event, by_user AS by, note FROM transfer_events WHERE transfer_id=? ORDER BY id", (tid,))


def progress(person: str) -> dict:
    """Counts for one leaving person: how much is still without a finished transfer."""
    resp = responsibilities(person)
    done = db.one("SELECT COUNT(*) AS n FROM transfers WHERE lower(from_owner)=lower(?) AND status='completed'", (person,))["n"]
    pend = sum(1 for r in resp if r["transfer"] and r["transfer"]["status"] == "proposed")
    appr = sum(1 for r in resp if r["transfer"] and r["transfer"]["status"] == "approved")
    unassigned = sum(1 for r in resp if not r["transfer"])
    total = len(resp) + done
    return {"total": total, "completed": done, "awaiting_approval": pend, "awaiting_new_owner": appr,
            "not_started": unassigned, "percent": round(100 * done / total) if total else 100}


def incoming(user: str, role: str) -> list:
    """Responsibilities moving to this person (only items their role may see)."""
    rows = [t for t in list_transfers(("proposed", "approved", "completed")) if t["to_owner"].lower() == user.lower()]
    out = []
    for t in rows:
        item = db.one("SELECT visibility FROM items WHERE id=?", (t["item_id"],))
        if item and roles.can_see(role, item["visibility"]):
            out.append(t)
    return out
