"""Visual layer: CSS and small HTML builders. Pure functions, so they are easy to test and preview.

Look: the base rules live in styles.py (all colours are CSS variables); core/themes.py swaps the variables to
make 20 themes. Default is a paper notebook (cream page, dotted grid, margin line), sticky notes, tape,
handwritten headings and a dotted "trail" between the five steps.

Everything that comes from user data is HTML-escaped here.
"""
from __future__ import annotations
import base64
import html
import re
from functools import lru_cache

from core import config, flags, notes as notes_core, themes
import styles

STATUS_TEXT = {"verified": "Verified", "approximate": "Approximate", "unverified": "Unverified"}
STATUS_KIND = {"verified": "ok", "approximate": "warn", "unverified": "bad"}

CSS = styles.base_css()


def esc(s) -> str:
    return html.escape("" if s is None else str(s))


@lru_cache(maxsize=None)
def asset_uri(name: str) -> str:
    """A data: URI for a file in assets/ (so the app needs no static file server). Empty if the file is missing."""
    try:
        data = (config.BASE / "assets" / name).read_bytes()
    except OSError:
        return ""
    return "data:image/png;base64," + base64.b64encode(data).decode()


def chip(text: str, kind: str = "type") -> str:
    return f"<span class='chip {kind}'>{esc(text)}</span>"


def type_label(t: str) -> str:
    return config.TYPE_LABEL.get(t, t)


def sidebar_logo() -> str:
    uri = asset_uri("logo.png")
    img = f"<img src='{uri}' alt='HandoverTrail logo'>" if uri else "<b>HandoverTrail</b>"
    return (f"<div class='side-logo'>{img}</div>"
            "<div class='side-tag'>Verified, role-based project handovers</div>")


def name_tag(user: str, role: str) -> str:
    return (f"<div class='nametag'><div class='top'>HELLO, I'M</div><div class='nm'>{esc(user)}</div>"
            f"<div class='rl'><span>Role: {esc(role)}</span></div></div>")


def footer() -> str:
    return "<div class='foot'>HandoverTrail &middot; built by Echo Relay &middot; knowledge stays when people go</div>"


def hero(title: str, subtitle: str, user: str, role: str) -> str:
    uri = asset_uri("icon.png")
    mark = f"<img class='mark' src='{uri}' alt='HandoverTrail mark'>" if uri else ""
    name = esc(title)
    if title == "HandoverTrail":
        name = "Handover<span class='t'>Trail</span>"
    return (f"<div class='hero'>{mark}<div class='words'><h1>{name}</h1><p>{esc(subtitle)}</p></div>"
            f"<span class='who'>Signed in as {esc(user)} &middot; {esc(role)}</span></div>")


def stepper(done: dict, current: str) -> str:
    names = ["Connect", "Reconstruct", "Verify", "Review", "Handover"]
    out = []
    for n, name in enumerate(names, 1):
        cls = "done" if done.get(name) else ("current" if name == current else "")
        out.append(f"<span class='step {cls}'><span class='num'>{n}</span>{name}</span>")
    return "<div class='stepper'>" + "".join(out) + "</div>"


def notice(text: str) -> str:
    return f"<div class='notice'>{esc(text)}</div>"


def flag_chips(item: dict, lookup: dict, role: str) -> str:
    out = []
    for line in flags.describe(item, lookup, role):
        if line.startswith("Unverified"):
            continue  # already shown as the evidence chip
        kind = "gap" if line.startswith("Gap") else "rec" if line.startswith("Recurring") else "conf"
        out.append(chip(line, kind))
    return "".join(out)


def item_card(item: dict, lookup: dict, role: str, show_visibility: bool = False, notes=None, viewer: str = "") -> str:
    status = item["verify_status"]
    edge = "bad" if status == "unverified" else "conf" if item.get("is_conflict") else "warn" if status == "approximate" else ""
    top = chip(type_label(item["type"]), "type") + chip(STATUS_TEXT[status], STATUS_KIND[status]) + flag_chips(item, lookup, role)
    if show_visibility:
        top += chip("Visible to " + item["visibility"], "vis")
    owner = f"Owner: {esc(item['owner'])} &middot; " if item.get("owner") else ""
    date = item.get("item_date") or item.get("source_date") or "undated"
    src = item.get("source_name") or ""
    rot = (-0.5, 0.35, -0.2, 0.5)[item["id"] % 4]
    tape = (-2, 2, -1, 3)[item["id"] % 4]
    kind = re.sub(r"[^a-z_]", "", str(item["type"]))
    return (f"<div class='card t-{kind} {edge}' style='--r:{rot}deg;--tr:{tape}deg'><div class='top'>{top}</div>"
            f"<div class='text'>{esc(item['text'])}</div>"
            f"<div class='meta'>{owner}{esc(src)} &middot; {esc(date)} &middot; item #{item['id']}</div>"
            f"{mini_notes(notes, viewer)}</div>")


def status_bars(counts: dict) -> str:
    """Three hand-drawn style bars: how many items passed the Evidence Gate."""
    total = max(counts.get("total", 0), 1)
    rows = ""
    for key, label, cls in (("verified", "Verified", "ok"), ("approximate", "Approximate", "warn"),
                            ("unverified", "Unverified", "bad")):
        n = counts.get(key, 0)
        rows += (f"<div class='bar-row'><div class='bar-l'>{label}</div><div class='bar-track'>"
                 f"<div class='bar-fill {cls}' style='width:{round(100 * n / total)}%'></div></div>"
                 f"<div class='bar-n'>{n}</div></div>")
    return f"<div class='bars'>{rows}</div>"


def readiness_html(rd: dict) -> str:
    """Score, one bar per part (points earned of points possible), and what to do next. All text is escaped."""
    if not rd.get("breakdown"):
        return notice(" ".join(rd.get("todo", [])))
    cls = {"Strong": "ok", "Needs work": "warn", "Weak": "bad"}
    out = (f"<div class='rd-head'><div class='rd-score'>{rd['score']}<small>/100</small></div>"
           f"<div class='rd-band'>{esc(rd['band'])}</div></div>")
    for p in rd["breakdown"]:
        out += (f"<div class='bar-row rd-part'><div class='bar-l'>{esc(p['label'])}</div><div class='bar-track'>"
                f"<div class='bar-fill {cls[p['status']]}' style='width:{int(p['pct'])}%'></div></div>"
                f"<div class='bar-n'>{p['points']:g}/{p['weight']}</div></div>"
                f"<div class='rd-detail'>{esc(p['status'])}: {esc(p['detail'])}</div>")
        for a in p["actions"]:
            refs = " ".join(f"#{n}" for n in a["ids"]) + (f" +{a['more']} more" if a["more"] else "")
            hid = f" {a['hidden']} restricted item(s) not listed." if a["hidden"] else ""
            out += (f"<div class='rd-do'>&rarr; {esc(a['text'])}{esc(hid)} <span class='ref'>{esc(refs)} "
                    f"&middot; {esc(a['where'])}</span></div>")
    return f"<div class='rd'>{out}</div>"


def plan_columns(plan: dict) -> list:
    """One HTML block per bucket (Day 1, Week 1, Month 1)."""
    cols = []
    for n, (bucket, lines) in enumerate(plan.items()):
        body = ""
        for ln in lines:
            refs = " ".join(f"#{n}" for n in ln["ids"])
            body += f"<div class='planline'>{esc(ln['text'])}<span class='ref'>{refs}</span></div>"
        if not body:
            body = "<div class='planline'>Nothing here for your role.</div>"
        cols.append(f"<div class='plancol p{n % 3}'><h4>{esc(bucket)}</h4>{body}</div>")
    return cols


def timeline_html(entries: list) -> str:
    if not entries:
        return notice("No dated items for your role.")
    rows = ""
    for t in entries:
        rows += (f"<div class='tl-item'><div class='tl-date'>{esc(t['item_date'])}</div>"
                 f"<div class='tl-body'>{chip(type_label(t['type']), 'type')} {esc(t['text'])} "
                 f"<span class='chip vis'>#{t['id']}</span></div></div>")
    return f"<div class='tl'>{rows}</div>"


def evidence_html(source_text: str, quote: str) -> str:
    from core import verify as ev
    body = re.sub(r"\n+", "<br>", ev.highlight_html(source_text, quote))
    return f"<div class='ev'>{body}</div>"


# ---------------------------------------------------------------- notes
def mini_notes(notes, viewer: str = "") -> str:
    """Small sticky notes stuck on the corner of an item card. Shows at most two, newest first."""
    out = ""
    for n in (notes or [])[:2]:
        who = "Your note" if n["author"] == viewer else f"{esc(n['author'])}'s note"
        out += f"<span class='stuck c-{esc(n['color'])}'><b>{who}:</b> {esc(n['body'])}</span>"
    extra = len(notes or []) - 2
    if extra > 0:
        out += f"<span class='stuck'>+{extra} more note(s) in My notes</span>"
    return out


def note_card(n: dict, viewer: str, signals: list, ref=None) -> str:
    """One note as a sticky. Everything user-written is escaped."""
    kind = notes_core.KINDS.get(n["kind"], n["kind"])
    chips = chip(kind, "type") + chip(notes_core.VIS[n["visibility"]], "vis")
    if n["link_item_id"]:
        chips += chip(f"Item #{n['link_item_id']}", "vis")
    if n["promoted_item_id"]:
        chips += chip(f"Promoted to item #{n['promoted_item_id']}", "prom")
    if n["author"] == viewer and n["remind_on"] and not n["done"]:
        label, kd = notes_core.when_label(n["remind_on"], ref)
        chips += chip("Remind: " + label, kd or "later")
    for sg in signals:
        chips += chip(sg, "sig")
    who = "You" if n["author"] == viewer else esc(n["author"])
    cls = "sn c-%s%s%s" % (esc(n["color"]), " pinned" if n["pinned"] else "", " done" if n["done"] else "")
    rot = (-0.8, 0.6, -0.3, 0.9)[n["id"] % 4]
    return (f"<div class='{cls}' style='--r:{rot}deg'><div class='sn-top'><div>{chips}</div><div class='sn-who'>{who}</div></div>"
            f"<div class='sn-body'>{esc(n['body'])}</div></div>")


def reminder_banner(overdue: int, today_n: int) -> str:
    bits = []
    if today_n:
        bits.append(f"{today_n} due today")
    if overdue:
        bits.append(f"{overdue} overdue")
    return (f"<div class='remind'><b>Reminders:</b> {' and '.join(bits)}. "
            "Open <i>My notes</i> in the sidebar and pick the Due filter.</div>")


def notes_empty(filtered: bool) -> str:
    msg = ("No note matches these filters. Clear the search or pick another filter." if filtered
           else "No notes yet. Write your first one on the left: a question, a to-do or a hunch.")
    return f"<div class='sn-empty'>{esc(msg)}</div>"


NOTES_RULE = ("<div class='noev'><b>Notes are not evidence.</b> They stay out of the handover unless a Lead promotes one "
              "with an exact quote from a source. Secrets are masked before a note is saved.</div>")


# ---------------------------------------------------------------- appearance
def theme_preview(key: str, current: bool) -> str:
    """A small live preview tile drawn with the real card, chip and trail classes."""
    t = themes.THEMES[key]
    tag = "<span class='chip ok'>Verified</span>"
    return (f"<div class='tp th-{key}{' current' if current else ''}'>"
            "<div class='tp-brand'>Handover<span>Trail</span></div>"
            "<div class='tp-trail'><i class='d'></i><b></b><i class='d'></i><b></b><i class='c'></i><b></b><i></i></div>"
            f"<div class='card t-decision' style='--r:-.5deg'><div class='top'>{tag}</div>"
            "<div class='text'>We decided to use PostgreSQL for event data.</div></div>"
            "<div class='card t-owner' style='--r:.4deg'><div class='text'>Karan will own the backend.</div></div>"
            "<div class='tp-btn'>Approve all</div></div>"
            f"<div class='tp-name'>{esc(t['name'])}{' &middot; current' if current else ''}</div>"
            f"<div class='tp-desc'>{esc(t['desc'])}</div>")


def swatches() -> str:
    return "<div class='swatches'>" + "".join(f"<i style='background:{a}'></i>" for a, _ in themes.ACCENTS.values()) + "</div>"
