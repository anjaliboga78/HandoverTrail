"""Steps 4 and 5 - Review, approve, share, acknowledge. Humans stay in control."""
from __future__ import annotations
import json

from . import db, roles


def list_items(where: str = "", params: tuple = ()) -> list:
    return db.q("SELECT i.*, s.name AS source_name, s.source_date AS source_date FROM items i "
                "JOIN sources s ON s.id=i.source_id " + where + " ORDER BY i.item_date, i.id", params)


def set_review(item_id: int, status: str, user: str, new_text=None) -> None:
    if status not in ("approved", "rejected", "pending"):
        raise ValueError("Unknown review status")
    item = db.one("SELECT * FROM items WHERE id=?", (item_id,))
    if not item:
        raise ValueError("Item not found")
    if new_text is not None and new_text.strip() and new_text.strip() != item["text"]:
        db.x("INSERT INTO item_versions(item_id,action,old_text,new_text,changed_by,changed_at) VALUES (?,?,?,?,?,?)",
             (item_id, "edit", item["text"], new_text.strip(), user, db.now()))
        db.x("UPDATE items SET text=? WHERE id=?", (new_text.strip(), item_id))
        db.log(user, "edit_item", f"item #{item_id}")
    if status != item["review_status"]:
        db.x("INSERT INTO item_versions(item_id,action,old_text,new_text,changed_by,changed_at) VALUES (?,?,?,?,?,?)",
             (item_id, status, item["review_status"], status, user, db.now()))
        db.x("UPDATE items SET review_status=? WHERE id=?", (status, item_id))
        db.log(user, f"{status}_item", f"item #{item_id}")


def approve_all_verified(user: str) -> int:
    rows = db.q("SELECT id FROM items WHERE review_status='pending' AND verify_status IN ('verified','approximate')"
                " AND is_conflict=0")
    for r in rows:
        set_review(r["id"], "approved", user)
    return len(rows)


def approve_handover(user: str, role: str) -> int:
    if role != "Lead":
        raise PermissionError("Only a Lead can approve and share a handover.")
    approved = list_items("WHERE i.review_status='approved'")
    if not approved:
        raise ValueError("Approve at least one item first.")
    snap = [{k: it[k] for k in ("id", "type", "text", "owner", "quote", "source_id", "source_name", "source_date",
                                "item_date", "visibility", "verify_status", "is_conflict", "is_gap",
                                "is_recurring", "conflict_with", "topic")} for it in approved]
    last = db.one("SELECT MAX(version) AS v FROM handovers")
    version = (last["v"] or 0) + 1
    hid = db.x("INSERT INTO handovers(version,status,approved_by,approved_at,snapshot) VALUES (?,?,?,?,?)",
               (version, "approved", user, db.now(), json.dumps(snap)))
    db.log(user, "approve_handover", f"version {version}", f"{len(snap)} items")
    return hid


def current_handover():
    h = db.one("SELECT * FROM handovers WHERE status='approved' ORDER BY version DESC LIMIT 1")
    if h:
        h["items"] = json.loads(h["snapshot"])
    return h


def view_for(role: str):
    """The handover as this role may see it (restricted items removed BEFORE anything else)."""
    h = current_handover()
    if not h:
        return None
    visible = roles.filter_items(h["items"], role)
    vis_ids = {i["id"] for i in visible}
    withheld = [{"id": i["id"], "type": i["type"]} for i in h["items"] if i["id"] not in vis_ids]  # never the text
    return {"version": h["version"], "approved_by": h["approved_by"], "approved_at": h["approved_at"],
            "id": h["id"], "items": visible, "restricted": len(withheld), "withheld": withheld,
            "all_items": {i["id"]: i for i in h["items"]}}


def log_view(user: str, version: int) -> None:
    """Record who opened the handover (once per person per version)."""
    if not db.one("SELECT 1 AS x FROM audit_log WHERE action='view_handover' AND user_name=? AND target=?",
                  (user, f"v{version}")):
        db.log(user, "view_handover", f"v{version}")


def viewers() -> list:
    return db.q("SELECT user_name AS user, target AS handover_version, MIN(at) AS first_opened, COUNT(*) AS n "
                "FROM audit_log WHERE action='view_handover' GROUP BY user_name, target ORDER BY first_opened DESC")


def one_pager_html(view: dict, plan_dict: dict, user: str, role: str, ready: dict) -> str:
    """A single printable page (open it and press Ctrl+P > Save as PDF)."""
    from html import escape as e
    def li(xs): return "".join(f"<li>{x}</li>" for x in xs) or "<li>None</li>"
    acts = {b: li(f"{e(x['text'])} <small>(#{', #'.join(map(str, x['ids']))})</small>" for x in v[:4])
            for b, v in plan_dict.items()}
    flagged = [i for i in view["items"] if i.get("is_conflict") or i.get("is_gap")]
    contacts = [i for i in view["items"] if i["type"] == "contact"]
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Handover v{view['version']} - one page</title>
<style>body{{font:13px/1.4 Georgia,serif;max-width:780px;margin:24px auto;color:#101046}}h1{{font-size:22px;margin:0}}
h2{{font-size:14px;border-bottom:2px solid #101046;margin:14px 0 4px}}ul{{margin:0;padding-left:18px}}
.k{{display:flex;gap:10px}}.k div{{flex:1}}small{{color:#555}}@media print{{body{{margin:0}}}}</style></head><body>
<h1>Project handover v{view['version']}</h1>
<small>Approved by {e(view['approved_by'])} on {e(view['approved_at'])}. For {e(user)} ({e(role)}). Readiness {ready['score']}/100.
Every line below is backed by a quote that was checked against its source.</small>
<h2>Do first</h2><div class="k"><div><b>Day 1</b><ul>{acts['Day 1']}</ul></div><div><b>Week 1</b><ul>{acts['Week 1']}</ul></div>
<div><b>Month 1</b><ul>{acts['Month 1']}</ul></div></div>
<h2>Watch out (conflicts and gaps)</h2><ul>{li(e(i['text']) for i in flagged[:6])}</ul>
<h2>Key contacts</h2><ul>{li(e(i['text']) for i in contacts[:5])}</ul>
{'<p><small>' + str(view['restricted']) + ' item(s) are withheld for this role.</small></p>' if view['restricted'] else ''}
</body></html>"""


def timeline(items: list) -> list:
    dated = [i for i in items if i.get("item_date")]
    return sorted(dated, key=lambda i: (i["item_date"], i["id"]))


def acknowledge(user: str) -> bool:
    h = current_handover()
    if not h:
        raise ValueError("There is no approved handover yet.")
    if db.one("SELECT 1 AS x FROM acks WHERE handover_id=? AND user_name=?", (h["id"], user)):
        return False
    db.x("INSERT INTO acks(handover_id,user_name,acknowledged_at) VALUES (?,?,?)", (h["id"], user, db.now()))
    db.log(user, "acknowledge", f"handover v{h['version']}")
    return True


def acked(user: str):
    h = current_handover()
    if not h:
        return None
    return db.one("SELECT * FROM acks WHERE handover_id=? AND user_name=?", (h["id"], user))


def export_markdown(view: dict, plan_dict: dict, user: str, role: str) -> str:
    """A shareable copy of the handover exactly as THIS role may see it."""
    from . import config
    lines = [f"# Project handover (v{view['version']})",
             f"Approved by {view['approved_by']} on {view['approved_at']}. Prepared for {user} ({role}).", ""]
    if view["restricted"]:
        lines += [f"_{view['restricted']} item(s) are restricted for this role and are not included._", ""]
    lines.append("## Action plan")
    for bucket, entries in plan_dict.items():
        lines.append(f"### {bucket}")
        lines += [f"- {e['text']} (items {', '.join('#' + str(n) for n in e['ids'])})" for e in entries] or ["- Nothing for this role."]
    lines += ["", "## Everything we know, with proof"]
    for typ in config.ITEM_TYPES:
        group = [i for i in view["items"] if i["type"] == typ]
        if not group:
            continue
        lines.append(f"### {config.TYPE_LABEL[typ]}")
        for i in group:
            owner = f" (owner: {i['owner']})" if i["owner"] else ""
            lines.append(f"- #{i['id']} {i['text']}{owner}")
            lines.append(f"  - Proof ({i['verify_status']}): \"{i['quote']}\" - {i['source_name']}, {i['source_date'] or 'undated'}")
    return "\n".join(lines) + "\n"
