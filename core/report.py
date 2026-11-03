"""PDF Handover Report: one professional document for ONE reader.

Everything in it comes from data this reader is allowed to see:
  * the approved handover is taken through handover.view_for(role), which removes restricted items first;
  * transfers, tasks and decisions are limited to items in that filtered view;
  * the readiness explanation only counts restricted items, it never names them;
  * a last redaction pass masks anything that still looks like a key, password, email or phone number.
Building the data is separate from drawing the PDF, so the content can be tested without opening the file.
Generating a report is written to the audit log (who, which version, which person; never the content).
"""
from __future__ import annotations
import datetime as dt
import html
import io
from collections import Counter

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from . import config, db, flags, handover, plan, readiness, roles, transfer
from .redact import redact

NAVY, TEAL, MUTED, LINE = colors.HexColor("#101046"), colors.HexColor("#168f84"), colors.HexColor("#5b5f7a"), colors.HexColor("#d9dbe6")
GOOD, WARN, BAD, TINT = colors.HexColor("#168f84"), colors.HexColor("#e0a800"), colors.HexColor("#d64532"), colors.HexColor("#f3f4f9")
TASK_TYPES = ("next_action", "deadline")
_SWAP = {"₹": "Rs ", "→": "->", "•": "-", "…": "...", "‑": "-", " ": " "}


# ------------------------------------------------------------------ data (role filtered)
def people_for(role: str) -> list:
    """Names this reader can pick as the departing member: owners of items in their filtered handover view."""
    view = handover.view_for(role)
    if not view:
        return []
    names = {(i["owner"] or "").strip() for i in view["items"]}
    ids = {i["id"] for i in view["items"]}
    names |= {t["from_owner"].strip() for t in transfer.list_transfers() if t["item_id"] in ids}
    return sorted((n for n in names if n), key=str.lower)


def _latest_transfer(item_id: int, person: str):
    return db.one("SELECT * FROM transfers WHERE item_id=? AND lower(from_owner)=lower(?) ORDER BY id DESC LIMIT 1",
                  (item_id, person))


def build_data(user: str, role: str, person: str) -> dict:
    """The report content for `user` (with `role`) about the departing member `person`."""
    view = handover.view_for(role)
    if not view:
        raise ValueError("There is no approved handover yet. A Lead must approve one first.")
    person = (person or "").strip()
    if not person:
        raise ValueError("Choose the departing member.")
    transfer.ensure_schema()
    items, lookup = view["items"], view["all_items"]
    ids = {i["id"] for i in items}
    by_id = {i["id"]: i for i in items}
    counts = Counter(i["type"] for i in items)
    ev = Counter(i["verify_status"] for i in items)
    sources = sorted({(i["source_name"], i["source_date"] or "undated") for i in items}, key=lambda s: (s[1], s[0]))
    dates = sorted(i["item_date"] for i in items if i.get("item_date"))

    # departing member's responsibilities and who takes them over
    cand = {i["id"] for i in items if (i["owner"] or "").strip().lower() == person.lower()}
    cand |= {t["item_id"] for t in transfer.list_transfers(person=person) if t["item_id"] in ids}
    resp = []
    for iid in sorted(cand):
        it, t = by_id[iid], _latest_transfer(iid, person)
        live = t and t["status"] in ("proposed", "approved", "completed")
        resp.append({"id": iid, "type": config.TYPE_LABEL.get(it["type"], it["type"]), "text": it["text"],
                     "new_owner": t["to_owner"] if live else "",
                     "status": transfer.LABEL[t["status"]] if live else "No new owner yet",
                     "state": t["status"] if live else "none", "evidence": it["verify_status"]})
    done = sum(1 for r in resp if r["state"] == "completed")

    # important decisions (with any conflict the reader may see)
    decisions = [{"id": i["id"], "text": i["text"], "owner": i["owner"] or "-", "date": i.get("item_date") or i["source_date"] or "undated",
                  "evidence": i["verify_status"],
                  "flags": [f for f in flags.describe(i, lookup, role) if not f.startswith("Unverified")]}
                 for i in items if i["type"] == "decision"]

    # pending tasks (anything finished or handed over is only counted)
    tasks, finished = [], 0
    for i in items:
        if i["type"] not in TASK_TYPES:
            continue
        owner = (i["owner"] or "").strip()
        t = db.one("SELECT * FROM transfers WHERE item_id=? ORDER BY id DESC LIMIT 1", (i["id"],))
        tick = db.one("SELECT 1 AS x FROM checklist WHERE ref=? AND section='tasks' AND done=1", (f"item:{i['id']}",))
        if (t and t["status"] == "completed") or tick:
            finished += 1
            continue
        status = "Open" if not (t and t["status"] in ("proposed", "approved")) else transfer.LABEL[t["status"]]
        tasks.append({"id": i["id"], "type": config.TYPE_LABEL[i["type"]], "text": i["text"], "owner": owner or "No owner",
                      "status": status, "mine": owner.lower() == person.lower()})
    tasks.sort(key=lambda t: (not t["mine"], t["owner"] == "No owner" and 1 or 0, t["id"]))

    rd = readiness.readiness(role)
    return {"user": user, "role": role, "person": person, "generated": dt.datetime.now().strftime("%d %b %Y, %H:%M"),
            "version": view["version"], "approved_by": view["approved_by"], "approved_at": view["approved_at"],
            "overview": {"items": len(items), "counts": {config.TYPE_LABEL[t]: counts[t] for t in config.ITEM_TYPES if counts[t]},
                         "evidence": dict(ev), "sources": sources, "span": (dates[0], dates[-1]) if dates else None,
                         "restricted": view["restricted"]},
            "resp": resp, "resp_done": done, "decisions": decisions, "tasks": tasks, "tasks_finished": finished,
            "readiness": rd, "plan": plan.build_plan(items)}


# ------------------------------------------------------------------ drawing
def _t(s) -> str:
    """Safe text for a Paragraph: masked once more, limited to characters the built-in fonts can draw, then escaped."""
    s = redact("" if s is None else str(s))[0]
    for a, b in _SWAP.items():
        s = s.replace(a, b)
    s = s.encode("cp1252", "replace").decode("cp1252")
    return html.escape(s)


def _styles() -> dict:
    base = ParagraphStyle("b", fontName="Helvetica", fontSize=9, leading=12.5, textColor=NAVY, alignment=TA_LEFT)
    return {"b": base,
            "small": ParagraphStyle("s", parent=base, fontSize=8, leading=10.5, textColor=MUTED),
            "cell": ParagraphStyle("c", parent=base, fontSize=8.4, leading=11),
            "head": ParagraphStyle("h", parent=base, fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white),
            "h1": ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=NAVY, spaceBefore=14, spaceAfter=5, keepWithNext=1),
            "title": ParagraphStyle("t", parent=base, fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=NAVY),
            "sub": ParagraphStyle("sub", parent=base, fontSize=11, leading=15, textColor=MUTED),
            "big": ParagraphStyle("big", parent=base, fontName="Helvetica-Bold", fontSize=30, leading=32, textColor=NAVY)}


class _Rule(Flowable):
    def __init__(self, width, color=TEAL, weight=1.6):
        super().__init__()
        self.width, self.height, self.color, self.weight = width, 3, color, weight

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.weight)
        self.canv.line(0, 1, self.width, 1)


class _Bar(Flowable):
    def __init__(self, pct, width=60 * mm, height=4.5 * mm):
        super().__init__()
        self.pct, self.width, self.height = max(0, min(100, pct)), width, height

    def draw(self):
        c = self.canv
        c.setFillColor(TINT)
        c.setStrokeColor(LINE)
        c.roundRect(0, 0, self.width, self.height, 2, fill=1, stroke=1)
        c.setFillColor(GOOD if self.pct >= 85 else WARN if self.pct >= 50 else BAD)
        if self.pct:
            c.roundRect(0, 0, max(4, self.width * self.pct / 100), self.height, 2, fill=1, stroke=0)


def _table(head: list, rows: list, widths: list, st: dict, empty: str = "Nothing to show for your access level.") -> Flowable:
    if not rows:
        return Paragraph(_t(empty), st["small"])
    data = [[Paragraph(_t(h), st["head"]) for h in head]]
    data += [[c if isinstance(c, Flowable) else Paragraph(_t(c), st["cell"]) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TINT]), ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                           ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
    return t


def _page(canvas, doc, d: dict) -> None:
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 11 * mm, w, 11 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(18 * mm, h - 7.4 * mm, "HandoverTrail")
    canvas.setFont("Helvetica", 8.5)
    canvas.drawRightString(w - 18 * mm, h - 7.4 * mm, _plain(f"Handover Report - v{d['version']}"))
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 14 * mm, w - 18 * mm, 14 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(18 * mm, 9.5 * mm, _plain(f"Confidential. Prepared for {d['user']} ({d['role']}); contains only what that role may see. {d['generated']}"))
    canvas.drawRightString(w - 18 * mm, 9.5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _plain(s: str) -> str:
    """For direct canvas drawing (no markup): same masking and character limits as _t, without HTML escaping."""
    return html.unescape(_t(s))


def render_pdf(d: dict) -> bytes:
    st = _styles()
    W = A4[0] - 36 * mm
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=20 * mm,
                            title=_plain(f"Handover Report: {d['person']}"), author="HandoverTrail", subject="Project handover report")
    P = lambda text, style="b": Paragraph(_t(text), st[style])  # noqa: E731
    ov, rd = d["overview"], d["readiness"]
    S = []

    # ---- title block and overview
    S += [P("Handover Report", "title"), Spacer(1, 2), P(f"Departing member: {d['person']}", "sub"), Spacer(1, 6), _Rule(W), Spacer(1, 8)]
    meta = [["Handover version", f"v{d['version']}", "Approved by", d["approved_by"]],
            ["Approved on", d["approved_at"].replace("T", " "), "Prepared for", f"{d['user']} ({d['role']})"]]
    S.append(Table([[Paragraph(f"<b>{_t(a)}</b>", st["cell"]), P(b, "cell"), Paragraph(f"<b>{_t(c)}</b>", st["cell"]), P(e, "cell")]
                    for a, b, c, e in meta], colWidths=[30 * mm, 50 * mm, 28 * mm, W - 108 * mm],
                   style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 3)]))

    S.append(P("1. Project overview", "h1"))
    done, total = d["resp_done"], len(d["resp"])
    kpi = [[P(str(ov["items"]), "big"), P(str(total), "big"), P(f"{rd['score']}", "big"), P(str(len(d["tasks"])), "big")],
           [P("items in this handover", "small"), P(f"responsibilities of {d['person']}", "small"),
            P(f"readiness score ({rd['band']})", "small"), P("pending tasks", "small")]]
    k = Table(kpi, colWidths=[W / 4] * 4)
    k.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TINT), ("BOX", (0, 0), (-1, -1), 0.5, LINE), ("LINEAFTER", (0, 0), (-2, -1), 0.5, LINE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, 1), (-1, 1), 8)]))
    S += [k, Spacer(1, 7)]
    mix = ", ".join(f"{n} {k_.lower()}{'s' if n != 1 else ''}" for k_, n in ov["counts"].items()) or "no items"
    span = f" Dated {ov['span'][0]} to {ov['span'][1]}." if ov["span"] else ""
    evd = ov["evidence"]
    S.append(P(f"This handover rebuilds what the team knew from {len(ov['sources'])} source(s). It holds {mix}.{span} "
               f"Every item is backed by a quote checked against its source: {evd.get('verified', 0)} verified, "
               f"{evd.get('approximate', 0)} approximate, {evd.get('unverified', 0)} unverified."))
    if ov["restricted"]:
        S += [Spacer(1, 3), P(f"{ov['restricted']} further item(s) are restricted for your role and are not included. Ask {d['approved_by']} if you need access.", "small")]
    S += [Spacer(1, 4), _table(["Source", "Date"], [[n, dte] for n, dte in ov["sources"]], [W - 30 * mm, 30 * mm], st)]

    # ---- responsibilities and new owners
    S.append(P(f"2. {d['person']}'s responsibilities and new owners", "h1"))
    S.append(P(f"{done} of {total} responsibilities have been fully handed over."
               if total else f"No approved responsibilities name {d['person']} for your access level."))
    S.append(Spacer(1, 4))
    S.append(_table(["#", "Type", "Responsibility", "New owner", "Transfer status"],
                    [[f"#{r['id']}", r["type"], r["text"], r["new_owner"] or "Not assigned", r["status"]] for r in d["resp"]],
                    [11 * mm, 22 * mm, W - 11 * mm - 22 * mm - 28 * mm - 36 * mm, 28 * mm, 36 * mm], st))

    # ---- decisions
    S.append(P("3. Important decisions", "h1"))
    S.append(_table(["#", "Decision", "Owner", "Date", "Evidence / notes"],
                    [[f"#{x['id']}", x["text"], x["owner"], x["date"], "; ".join([x["evidence"].capitalize()] + x["flags"])]
                     for x in d["decisions"]], [11 * mm, W - 11 * mm - 22 * mm - 22 * mm - 40 * mm, 22 * mm, 22 * mm, 40 * mm], st,
                    "No decisions are available for your access level."))

    # ---- pending tasks
    S.append(P("4. Pending tasks", "h1"))
    note = f" {d['tasks_finished']} other task(s) are already done or handed over." if d["tasks_finished"] else ""
    S.append(P(f"{len(d['tasks'])} task(s) and deadline(s) are still open.{note} Tasks owned by {d['person']} come first."))
    S.append(Spacer(1, 4))
    S.append(_table(["#", "Type", "Task", "Owner", "Status"],
                    [[f"#{x['id']}", x["type"], x["text"], x["owner"], x["status"]] for x in d["tasks"]],
                    [11 * mm, 22 * mm, W - 11 * mm - 22 * mm - 28 * mm - 36 * mm, 28 * mm, 36 * mm], st, "No pending tasks."))

    # ---- readiness
    S.append(P("5. Handover readiness", "h1"))
    S.append(P(f"Score {rd['score']}/100: {rd['band']}. The score uses all project data, so it is the same for every reader."))
    S.append(Spacer(1, 4))
    S.append(_table(["Part", "Progress", "Points", "Where it stands"],
                    [[p["label"], _Bar(p["pct"], 38 * mm), f"{p['points']:g}/{p['weight']}", f"{p['status']}: {p['detail']}"] for p in rd["breakdown"]],
                    [44 * mm, 41 * mm, 15 * mm, W - 100 * mm], st))
    if rd["improve"]:
        S.append(Spacer(1, 6))
        S.append(KeepTogether([P("What to improve first (biggest gain first)", "b")] + [
            Paragraph("- " + _t(f"{i['text']} (+{i['lost']:g} points)" + (f" {i['hidden']} restricted item(s) not listed." if i["hidden"] else "")), st["cell"])
            for i in rd["improve"][:5]]))

    # ---- onboarding plan
    head = [P("6. Onboarding plan for the new owner", "h1"),
            P("Built only from approved items you may see. Numbers refer to item numbers in the handover."), Spacer(1, 4)]
    for bucket, lines in d["plan"].items():
        block = [_table([bucket, "Items"], [[x["text"], ", ".join(f"#{n}" for n in x["ids"])] for x in lines],
                        [W - 28 * mm, 28 * mm], st, "Nothing for your role."), Spacer(1, 6)]
        S.append(KeepTogether(head + block))      # the heading travels with the first block
        head = []

    doc.build(S, onFirstPage=lambda c, dc: _page(c, dc, d), onLaterPages=lambda c, dc: _page(c, dc, d))
    return buf.getvalue()


def generate(user: str, role: str, person: str) -> bytes:
    """Build the PDF for this reader and record that it was made (never its contents)."""
    d = build_data(user, role, person)
    pdf = render_pdf(d)
    db.log(user, "generate_report", f"v{d['version']}", f"person={person}; role={role}; {len(pdf) // 1024} KB")
    return pdf
