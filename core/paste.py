"""Paste your notes - read pasted text, show it as an editable preview, import only what a human approves.

Flow (nothing is stored until the last step):
  1. analyze()         mask secrets, then find tasks, decisions, deadlines, people, missing owners, open questions
  2. the app shows the rows in an editable table: Approve / Review / Reject, and every cell can be edited
  3. import_approved() store the source, then only the approved rows, each one still checked by the Evidence Gate

Every row carries an exact quote from the (masked) text, so the Evidence Gate works as for any other source.
Everything found here is a "suggestion, not verified" until a person approves it.
"""
from __future__ import annotations
import re

from . import config, db, extract, flags, ingest
from .redact import redact
from .verify import verify

# ------------------------------------------------------------------ labels shown in the preview
KIND_LABEL = {"next_action": "Task", "decision": "Decision", "deadline": "Deadline", "contact": "Person",
              "owner": "Ownership", "open_question": "Open question", "blocker": "Blocker",
              "risk": "Risk", "dependency": "Dependency"}
MISSING_OWNER = "Missing owner"          # an "owner" item that names nobody
KIND_OPTIONS = ["Task", "Decision", "Deadline", "Person", "Open question", MISSING_OWNER, "Ownership",
                "Blocker", "Risk", "Dependency"]
LABEL_TO_TYPE = {v: k for k, v in KIND_LABEL.items()}
LABEL_TO_TYPE[MISSING_OWNER] = "owner"
STATUS_OPTIONS = ["Approve", "Review", "Reject"]
MAX_ROWS = 150


def kind_label(typ: str, owner) -> str:
    if typ == "owner" and not (owner or "").strip():
        return MISSING_OWNER
    return KIND_LABEL.get(typ, typ)


# ------------------------------------------------------------------ patterns
MONTHS = "jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
WEEKDAYS = "mon(?:day)?|tue(?:s(?:day)?)?|wed(?:nesday)?|thu(?:r(?:s(?:day)?)?)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?"
DATE_TOKEN = (rf"\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:{MONTHS})\b(?:\s+\d{{4}})?"
              rf"|(?:{MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?\b(?:,?\s+\d{{4}})?|\d{{1,2}}/\d{{1,2}}(?:/\d{{2,4}})?"
              rf"|(?:(?:next|this|coming)\s+)?(?:{WEEKDAYS})\b|tomorrow|tonight|today"
              rf"|end of (?:the )?(?:day|week|month|sprint|quarter|year)|eod|eow|eom"
              rf"|(?:next|this)\s+(?:week|month|sprint|quarter)|in \d+\s+(?:days?|weeks?|months?)")
R_DUE = re.compile(rf"\b(?:(by|before|due(?: on| by)?|until|till|on|deadline(?: is| of)?:?)\s+)?({DATE_TOKEN})", re.I)
R_DUE_CUE = re.compile(r"\b(deadline|due|launch(?:es)?|release|go[- ]live|beta|demo day|submission|submit by|milestone|ship)\b", re.I)

R_HEAD = re.compile(r"^\s*(?:#{1,6}\s*)?(?:\*\*)?([A-Za-z][A-Za-z /&-]{2,30}?)(?:\*\*)?\s*:?\s*$")
SECTION = [  # heading words -> what every line under it is
    (r"action items?|actions?|to-?dos?|next steps?|tasks?|follow[- ]ups?", "next_action"),
    (r"decisions?|decided|agreed|resolutions?", "decision"),
    (r"open questions?|questions?|unresolved|tbd|parking lot|to be decided|unknowns?", "open_question"),
    (r"blockers?|blocked", "blocker"),
    (r"risks?|concerns?|issues?", "risk"),
    (r"deadlines?|dates?|milestones?|timeline", "deadline"),
    (r"contacts?|key people|who to ask|people", "contact"),
    (r"attendees?|present|participants?|agenda|summary|notes?|discussion|updates?", None),
]
R_BULLET = re.compile(r"^\s*(?:[-*\u2022\u25cf>]+|\d{1,2}[.)]|\[[ xX]?\]|\(\s?[ xX]?\s?\))\s*(?:\[[ xX]?\]\s*)?")
R_CHAT = re.compile(r"^\s*(?:\[(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})[^\]]*\]\s*"
                    r"|(\d{1,2}/\d{1,2}/\d{2,4}),?\s+\d{1,2}:\d{2}(?:\s?[APap][Mm])?\s*-\s*)?([A-Z][a-z]{2,}):\s+")
R_LABEL = re.compile(r"^\s*(?:action|todo|to-do|task|ai|decision|question|q|risk|blocker|deadline)\s*[:\-]\s*", re.I)

_R_DECISION_EXTRA = re.compile(r"\b(we(?:'ll| will) go with|settled on|agreed (?:that|on)|final decision|approved (?:the|a)\b|"
                              r"confirmed that|resolved to|it was decided)", re.I)


class _Any:
    def __init__(self, *rx):
        self.rx = rx

    def search(self, s):
        for r in self.rx:
            m = r.search(s)
            if m:
                return m
        return None


R_DECISION = _Any(extract.R_DECISION, _R_DECISION_EXTRA)
R_QUESTION = re.compile(r"(\?\s*$)|\b(not decided|still open|unclear|no decision|not yet decided|tbd|to be decided|"
                        r"need(?:s)? to (?:figure out|find out|decide|confirm|check)|not sure|unknown|open question|"
                        r"nobody knows|no one knows|have to decide|whether (?:we|to))\b", re.I)
R_NOOWNER = re.compile(r"\b(nobody|no one|noone)\b.{0,40}\b(owns?|responsible|handles?|handling|maintains?|taking|picked)\b|"
                       r"\b(unassigned|no owner|ownerless|needs? an owner|owner\s*[:=]\s*(?:none|tbd|\?|unknown)|"
                       r"who(?:'s| is| will| should| owns| takes| is going to))\b", re.I)
R_TASK_VERB = re.compile(r"\b(will|to|needs? to|should|must|has to|have to|is going to|going to|'ll|can you|please)\b", re.I)
R_TASK_NONAME = re.compile(r"\b(we|someone|somebody|team)\s+(?:need|needs|should|must|have to|has to|to)\b|"
                           r"\bneed(?:s)? to\b|\bmust\b|\bshould\b|\bhave to\b|^(?:please\s+)?(?:send|fix|set up|update|check|"
                           r"call|email|write|review|add|remove|pay|renew|book|schedule|create|prepare|share|move|ask|"
                           r"confirm|follow up|finish|deploy|test|migrate|document|collect|share)\b", re.I)
R_BLOCK = extract.R_BLOCK
R_RISK = extract.R_RISK
R_DEPEND = extract.R_DEPEND
R_CONTACT_CUE = re.compile(
    r"\b(?i:contact|call|reach out to|talk to|get in touch with|ask|speak to|email|meet)\s+(?P<n1>(?:Mr|Ms|Mrs|Dr)\.\s+[A-Z][a-z]+|[A-Z][a-z]{2,})\b"
    r"|\b(?P<n2>[A-Z][a-z]{2,})\s+(?:is|was)\s+(?:our|the|my)\s+(?P<role>[a-z][a-z \-]{2,40}?)(?:\s+(?:at|for|from)\b|[.,;]|$)"
    r"|\b(?P<n3>[A-Z][a-z]{2,})\s+(?:from|at|of)\s+(?P<org>[A-Z][\w&-]+(?:\s+[A-Z][\w&-]+)?)")
R_ASSIGN = re.compile(r"\b(?:assigned to|owner\s*[:=]|owned by|handled by|lead\s*[:=]|responsible\s*[:=]?|@)\s*([A-Z][a-z]{2,}|[a-z]{3,})\b")
R_PAREN_OWNER = re.compile(r"\(\s*(?:owner\s*[:=]\s*)?([A-Z][a-z]{2,})\s*\)")
R_LEAD_NAME = re.compile(r"^(?:(?:and|then|also|so|ok|okay)\s+)?([A-Z][a-z]{2,})(?:\s*(?:,|&|and)\s*([A-Z][a-z]{2,}))?\s*"
                         r"(?:will|to|needs? to|should|must|has to|is going to|going to|'ll|can|owns?|is responsible|will own|"
                         r"will lead|will handle|:|-|\u2013)\s*", re.I)
R_SUBJ_ANY = re.compile(r"\b([A-Z][a-z]{2,})\s+(?:will|needs? to|should|must|has to|is going to|to)\s+[a-z]")
R_COMMIT = re.compile(r"\b([A-Z][a-z]{2,})\s+(?:said|says|agreed|promised|committed|offered|volunteered|confirmed|told us)\s*"
                      r"(?:that\s+)?(?:(?:he|she|they)\s+)?(?:will|would|to|can|'ll)\b")
R_SELF = re.compile(r"\b(i|i'll|i will|i'm going to|let me|my task)\b", re.I)

NOT_NAMES = {
    "We", "The", "It", "This", "That", "There", "Nobody", "Someone", "Please", "Also", "Next", "Today", "Still", "Then",
    "Task", "Owner", "Status", "Due", "Notes", "Issue", "Pull", "Meeting", "Date", "And", "But", "Our", "They", "She",
    "Action", "Actions", "Decision", "Decisions", "Question", "Questions", "Todo", "Risk", "Risks", "Blocker", "Deadline",
    "Team", "Everyone", "Everybody", "Anyone", "Who", "What", "When", "Where", "Why", "How", "If", "Maybe", "Need", "Needs",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "January", "February", "March", "April",
    "June", "July", "August", "September", "October", "November", "December", "Sept", "Tomorrow", "Tonight", "Yesterday",
    "Razorpay", "Stripe", "Paypal", "Mysql", "Postgres", "Postgresql", "Sqlite", "Mongodb", "Firebase", "Github", "Figma",
    "Slack", "Whatsapp", "Google", "Excel", "Docker", "Python", "React", "Streamlit", "Beta", "Alpha", "Demo", "Launch",
    "Sponsor", "Budget", "Server", "Database", "Payment", "Payments", "Webhook", "Login", "Design", "Theme", "App",
    "Attendees", "Present", "Agenda", "Summary", "Discussion", "Update", "Updates", "Contact", "Contacts", "People",
}
STOP_FIRST = {"Let", "Have", "Make", "Get", "Check", "Send", "Fix", "Add", "Ask", "Call", "Email", "Write", "Review",
              "Pay", "Book", "Create", "Share", "Move", "Update", "Confirm", "Finish", "Test", "Prepare", "Remember",
              "Follow", "Set", "Run", "Use", "Try", "Keep", "Talk", "Speak", "Reach", "Contact", "Ping", "Chat", "Discuss",
              "Meet", "Look", "Wait", "Remind", "Tell", "Find", "Work", "Plan", "Order", "Buy", "Print", "Submit",
              "Publish", "Merge", "Push", "Build", "Clean", "Open", "Close", "Start", "Stop", "Take", "Give", "Bring",
              "Pick", "Join", "Read", "Collect", "Sort", "Decide", "Renew", "Upload", "Download", "Install", "Verify",
              "Approve", "Ship", "Release", "Draft", "Fill", "Sign", "Transfer", "Arrange", "Organise", "Organize"}


# ------------------------------------------------------------------ small helpers
def known_people() -> set:
    """People the project already knows: the demo users and every owner named in earlier items."""
    names = set()
    try:
        names |= {r["name"] for r in db.q("SELECT name FROM users")}
        names |= {r["owner"].split()[0] for r in db.q("SELECT DISTINCT owner FROM items WHERE owner IS NOT NULL AND owner<>''")}
    except Exception:
        pass
    return {n for n in names if n}


def _is_name(w) -> bool:
    return bool(w) and w not in NOT_NAMES and w not in STOP_FIRST and len(w) >= 3


def _find_due(s: str):
    """Return the due phrase in a sentence (for example 'by Friday' or '14 March') or None."""
    m = R_DUE.search(s)
    if not m:
        return None
    prep = (m.group(1) or "").strip().lower().rstrip(":")
    tok = m.group(2).strip()
    # a bare 'on 3' or a number that is not a date never reaches here (DATE_TOKEN needs a month, ISO or slash form)
    if prep.startswith("deadline"):
        prep = "by"
    if prep in ("on", ""):
        return tok
    return f"{prep} {tok}"


def _sentences(body: str):
    protected = re.sub(r"\b(Mr|Ms|Mrs|Dr|vs|e\.g|i\.e|etc|approx|no)\.", lambda m: m.group(1) + "\u2024", body)
    protected = re.sub(r"(?<=\d)\.(?=\d)", "\u2024", protected)
    for sm in extract.R_SENT.finditer(protected):
        s = sm.group().strip().replace("\u2024", ".")
        if s:
            yield s


def _section_of(line: str):
    """If the line is a heading such as 'Action items:' return (True, type_or_None)."""
    if len(line) > 45 or R_BULLET.match(line) and not line.strip().endswith(":"):
        return False, None
    m = R_HEAD.match(line.strip().strip("*#_ "))
    if not m:
        return False, None
    word = m.group(1).strip().lower()
    for pat, typ in SECTION:
        if re.fullmatch(pat, word):
            return True, typ
    # unknown heading ending in a colon ends the current section
    return (line.strip().endswith(":") and len(line.split()) <= 4), None


def _owner_of(s: str, speaker, known: set):
    """Best guess of who owns a sentence. Returns (owner or None, how_sure 0..1)."""
    m = R_ASSIGN.search(s)
    if m and _is_name(m.group(1).capitalize()):
        return m.group(1).capitalize(), 0.9
    m = R_LEAD_NAME.match(s)
    if m and _is_name(m.group(1)):
        names = [n for n in (m.group(1), m.group(2)) if n and _is_name(n)]
        return " and ".join(names), 0.85
    m = R_PAREN_OWNER.search(s)
    if m and _is_name(m.group(1)):
        return m.group(1), 0.8
    m = R_COMMIT.search(s)
    if m and _is_name(m.group(1)):
        return m.group(1), 0.85
    m = R_SUBJ_ANY.search(s)
    if m and _is_name(m.group(1)):
        return m.group(1), 0.75
    if speaker and R_SELF.search(s):
        return speaker, 0.7
    # a trailing "- Karan" or "(Karan)" style signature
    m = re.search(r"[-\u2013\u2014]\s*([A-Z][a-z]{2,})\s*$", s)
    if m and _is_name(m.group(1)):
        return m.group(1), 0.7
    return None, 0.0


def _topic(s: str) -> str:
    return extract.topic_of(s)


# ------------------------------------------------------------------ the rule-based reader
def rule_extract(text: str, known=None) -> list:
    """Read pasted notes without any AI. Returns candidate dicts (type, text, owner, due, quote, topic, confidence, why)."""
    known = known if known is not None else known_people()
    out, seen = [], set()

    def add(typ, txt, owner, quote, conf, due=None, d=None, why=""):
        key = (typ, quote)
        if key in seen or len(out) >= MAX_ROWS:
            return
        seen.add(key)
        if owner and owner.split(" and ")[0] in known:
            conf = min(0.95, conf + 0.1)
        txt = re.sub(r"\s+", " ", txt).strip().rstrip(".")
        out.append({"type": typ, "text": txt, "owner": owner, "due": due, "quote": quote, "topic": _topic(quote),
                    "confidence": round(conf, 2), "item_date": d, "why": why})

    section, in_section = None, 0
    for raw in text.splitlines():
        if not raw.strip():
            if in_section:                      # a blank line after the section's items ends the section
                section, in_section = None, 0
            continue
        head, sec = _section_of(raw)
        if head:
            section, in_section = sec, 0
            continue
        had_bullet = bool(R_BULLET.match(raw))
        if section and in_section and not had_bullet:   # plain prose after a bullet list: the section is over
            section, in_section = None, 0
        if section:
            in_section += 1
        body = R_BULLET.sub("", raw, count=1) if had_bullet else raw.strip()
        body = body.strip()
        if not body or extract.R_SKIP.match(body):
            continue
        speaker, d = None, None
        cm = R_CHAT.match(body)
        if cm:
            d, speaker = (cm.group(1) or cm.group(2)), cm.group(3)
            if _is_name(speaker):
                body = body[cm.end():]
            else:
                speaker = None
        lm = R_LABEL.match(body)
        label_type = None
        if lm:
            tag = lm.group(0).strip().rstrip(":-").strip().lower()
            label_type = {"action": "next_action", "todo": "next_action", "to-do": "next_action", "task": "next_action",
                          "ai": "next_action", "decision": "decision", "question": "open_question", "q": "open_question",
                          "risk": "risk", "blocker": "blocker", "deadline": "deadline"}.get(tag)
            body = body[lm.end():]
        # Structured task row from a CSV export: let the normal extractor deal with it
        if extract.R_TASK.match(body):
            for it in extract.offline_extract(body):
                add(it["type"], it["text"], it["owner"], it["quote"], it["confidence"], None, it["item_date"], "task list row")
            continue

        for s in _sentences(body):
            if len(re.sub(r"\[REDACTED-[A-Z]+\]", "", s).strip(" .:-")) < 8:
                continue
            quote = s
            fixed = label_type or section
            owner, osure = _owner_of(s, speaker, known)
            due = _find_due(s)
            dcue = bool(R_DUE_CUE.search(s))
            kind, conf, why = None, 0.6, ""

            m = R_CONTACT_CUE.search(s)
            person = None
            if m:
                person = m.group("n1") or m.group("n2") or m.group("n3")
                if person and not person.startswith(("Mr", "Ms", "Mrs", "Dr")) and not _is_name(person):
                    person = None

            if fixed == "contact" or (person and not owner):
                p = person or (_first_name(s))
                if p:
                    role = (m.group("role") if m and m.groupdict().get("role") else None) or (m.group("org") if m and m.groupdict().get("org") else None)
                    if not role and p:
                        om = re.search(re.escape(p) + r"\s+(?:from|at|of)\s+([A-Z][\w&-]+(?:\s+[A-Z][\w&-]+)?)", s)
                        role = om.group(1) if om else None
                    add("contact", f"Key contact: {p}" + (f" ({role.strip()})" if role else ""), p, quote, 0.7, None, d, "named as a person to ask or call")
                    continue
            if R_NOOWNER.search(s) and fixed not in ("decision",):
                add("owner", "No owner: " + s, None, quote, 0.75, due, d, "nobody is named as responsible")
                continue
            if fixed == "open_question" or R_QUESTION.search(s):
                add("open_question", s, None, quote, 0.7 if fixed == "open_question" else 0.6, due, d, "unresolved question")
                continue
            if fixed == "decision" or (R_DECISION.search(s) and not R_COMMIT.search(s)):
                add("decision", s, owner or speaker, quote, 0.75 if fixed == "decision" else 0.65, due, d, "a decision was stated")
                continue
            if fixed == "blocker" or R_BLOCK.search(s):
                add("blocker", s, owner, quote, 0.7, due, d, "something is stuck")
                continue
            if fixed == "risk":
                add("risk", s, owner, quote, 0.65, due, d, "listed as a risk")
                continue
            is_task = (fixed == "next_action" or (owner and R_TASK_VERB.search(s)) or R_TASK_NONAME.search(s)
                       or (had_bullet and bool(re.match(r"\[[ ]?\]", raw.strip().lstrip("-* ")))))
            if is_task and person and owner and person != owner:
                add("contact", f"Key contact: {person}", person, quote, 0.6, None, d, "named as a person to contact")
            if is_task:
                conf = 0.8 if (fixed == "next_action" or owner) else 0.6
                add("next_action", _task_text(s, owner), owner, quote, conf, due, d,
                    "task with a named owner" if owner else "task, but nobody is named")
                continue
            if fixed == "deadline" or (due and dcue):
                add("deadline", s, owner, quote, 0.7, due, d, "a date or deadline was stated")
                continue
            if R_DEPEND.search(s):
                add("dependency", s, owner, quote, 0.6, due, d, "depends on something else")
                continue
            if R_RISK.search(s):
                add("risk", s, None, quote, 0.55, due, d, "sounds like a problem")
    return out


def _first_name(s: str):
    for m in re.finditer(r"\b([A-Z][a-z]{2,})\b", s):
        if _is_name(m.group(1)):
            return m.group(1)
    return None


def _task_text(s: str, owner) -> str:
    """Tidy the task sentence a little but never invent words."""
    return s.strip()


# ------------------------------------------------------------------ AI reader (optional) + shared enrichment
def _ai_extract(name: str, text: str, date, provider: str):
    src = {"name": name, "text": text, "source_date": date}
    return extract.llm_extract(src, provider)


def _enrich(cand: dict, clean_text: str) -> dict:
    """Make every candidate follow one shape and check its quote against the exact pasted text."""
    typ = cand["type"] if cand["type"] in config.ITEM_TYPES else "next_action"
    owner = (cand.get("owner") or None)
    owner = owner.strip() if owner else None
    due = cand.get("due") or _find_due(cand.get("quote", "")) if typ in ("next_action", "deadline", "decision", "blocker") else cand.get("due")
    status, score = verify(cand.get("quote", ""), clean_text)
    issues = []
    if typ == "owner" and not owner:
        issues.append("Missing owner")
    if typ == "next_action" and not owner:
        issues.append("Missing owner")
    if typ == "next_action" and not due:
        issues.append("No deadline")
    if typ == "contact" and not owner:
        issues.append("No name")
    if status == "unverified":
        issues.append("Quote not found")
    elif status == "approximate":
        issues.append("Quote approximate")
    if len(cand.get("quote", "")) < 12:
        issues.append("Quote very short")
    if cand.get("confidence", 0.5) < 0.6:
        issues.append("Low confidence")
    return {"type": typ, "text": cand["text"].strip(), "owner": owner, "due": (due or None), "quote": cand.get("quote", "").strip(),
            "topic": cand.get("topic") or _topic(cand.get("quote", "")), "confidence": float(cand.get("confidence", 0.5)),
            "item_date": cand.get("item_date"), "why": cand.get("why", ""), "evidence": status, "score": score,
            "issues": issues}


def default_status(row: dict) -> str:
    """Clean, well-supported suggestions start as Approve. Anything with a problem starts as Review."""
    hard = [i for i in row["issues"] if i not in ("No deadline",)]
    return "Review" if hard else "Approve"


# ------------------------------------------------------------------ step 1: analyze
def analyze(name: str, text: str, visibility: str, source_date, provider: str = "offline") -> dict:
    """Mask secrets and read the notes. Stores NOTHING. Returns a draft the app keeps in the session."""
    if not (text or "").strip():
        raise ValueError("Paste some text first.")
    if len(text) > 200_000:
        raise ValueError("That is too long (limit 200,000 characters).")
    if visibility not in config.LEVELS:
        raise ValueError(f"Unknown visibility '{visibility}'")
    clean, found = redact(text)
    warnings, used = [], "rule-based reader (no AI, nothing leaves this computer)"
    cands = None
    if provider != "offline":
        from . import llm
        if not llm.available(provider):
            warnings.append(f"No API key for '{provider}'; used the rule-based reader.")
        else:
            try:
                cands = _ai_extract(name, clean, source_date, provider)
                used = f"AI reader ({provider}); the text was masked first"
            except (llm.LLMError, extract.ExtractionError) as e:
                warnings.append(f"{e} Used the rule-based reader instead.")
    if cands is None:
        cands = rule_extract(clean)
    rows = [_enrich(c, clean) for c in cands]
    for r in rows:
        r["status"] = default_status(r)
        r["original"] = {"type": r["type"], "text": r["text"], "owner": r["owner"], "due": r["due"]}
    people = {}
    for r in rows:
        for who in filter(None, (r["owner"] or "").split(" and ")):
            people[who] = people.get(who, 0) + 1
    return {"name": (name or "Pasted notes").strip()[:80] or "Pasted notes", "text": text, "clean": clean,
            "visibility": visibility, "date": source_date, "masked": len(found), "rows": rows,
            "people": people, "reader": used, "warnings": warnings}


# ------------------------------------------------------------------ preview table <-> rows
def rows_to_table(rows: list) -> list:
    """Plain dicts for the editable table, one per row, in the same order."""
    return [{"Import?": r["status"], "Kind": kind_label(r["type"], r["owner"]), "Item": r["text"],
             "Owner / person": r["owner"] or "", "Due": r["due"] or "",
             "Heads-up": ", ".join(r["issues"]) or "-", "Quote from your notes": r["quote"]} for r in rows]


def apply_table(rows: list, table: list) -> list:
    """Copy the user's edits from the table back into the rows (same order). Returns a new list."""
    if len(table) != len(rows):
        raise ValueError("The preview changed size; analyze the notes again.")
    out = []
    for r, t in zip(rows, table):
        n = dict(r)
        status = t.get("Import?")
        n["status"] = status if status in STATUS_OPTIONS else r["status"]
        kind = t.get("Kind")
        n["type"] = LABEL_TO_TYPE.get(kind, r["type"])
        n["text"] = str(t.get("Item") or "").strip()
        owner = str(t.get("Owner / person") or "").strip()
        n["owner"] = owner or None
        due = str(t.get("Due") or "").strip()
        n["due"] = due or None
        out.append(n)
    return out


def live_checks(rows: list) -> list:
    """Problems with the rows that are currently set to Approve. Shown under the table as the person edits."""
    msgs = []
    ap = [r for r in rows if r["status"] == "Approve"]
    empty = [r for r in ap if not r["text"]]
    if empty:
        msgs.append(("error", f"{len(empty)} approved row(s) have no item text. Write it or reject the row."))
    no_owner = [r for r in ap if r["type"] in ("next_action", "owner") and not r["owner"]]
    if no_owner:
        msgs.append(("warning", f"{len(no_owner)} approved task(s) still have no owner. You can add one in the table, "
                                "or import them as they are: they will show up as gaps for the Lead."))
    nameless = [r for r in ap if r["type"] == "contact" and not r["owner"]]
    if nameless:
        msgs.append(("warning", f"{len(nameless)} approved person row(s) have no name."))
    return msgs


def counts(rows: list) -> dict:
    c = {"Approve": 0, "Review": 0, "Reject": 0}
    for r in rows:
        c[r["status"]] = c.get(r["status"], 0) + 1
    return c


def summary(rows: list) -> dict:
    """How many of each kind were found (for the chips above the table)."""
    s = {}
    for r in rows:
        k = kind_label(r["type"], r["owner"])
        s[k] = s.get(k, 0) + 1
    return s


def set_all(rows: list, status: str, only_clean: bool = False) -> list:
    out = []
    for r in rows:
        n = dict(r)
        if status in STATUS_OPTIONS and (not only_clean or default_status(r) == "Approve"):
            n["status"] = status
        out.append(n)
    return out


# ------------------------------------------------------------------ step 3: import
def _final_text(row: dict) -> str:
    t = row["text"].strip()
    if row.get("due") and row["type"] in ("next_action", "deadline"):
        if row["due"].lower() not in t.lower():
            t = f"{t} (due {row['due']})"
    return t


def import_approved(draft: dict, rows: list, user: str) -> dict:
    """Store the source and ONLY the approved rows. Rows stay 'pending' for the Lead; the Evidence Gate runs on each."""
    approved = [r for r in rows if r["status"] == "Approve"]
    if not approved:
        raise ValueError("Approve at least one row first.")
    for r in approved:
        if not r["text"].strip():
            raise ValueError("An approved row has no item text.")
        if r["type"] not in config.ITEM_TYPES:
            raise ValueError("An approved row has an unknown kind.")
    sid = ingest.add_source(draft["name"], "pasted_notes", draft["text"], draft["visibility"], draft["date"], user)
    src = db.one("SELECT * FROM sources WHERE id=?", (sid,))
    edited = 0
    for r in approved:
        text = _final_text(r)
        owner = r["owner"] if r["type"] != "owner" or r["owner"] else None
        status, score = verify(r["quote"], src["text"])
        iid = db.x("INSERT INTO items(source_id,type,text,owner,quote,topic,confidence,verify_status,verify_score,"
                   "visibility,item_date,extractor,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (sid, r["type"], text, owner, r["quote"], r.get("topic") or "general", r["confidence"], status, score,
                    src["visibility"], r.get("item_date") or src["source_date"], "paste-preview", db.now()))
        o = r.get("original") or {}
        if (o.get("text"), o.get("owner"), o.get("due"), o.get("type")) != (r["text"], r["owner"], r["due"], r["type"]):
            edited += 1
            before = f"{o.get('text', '')} [{o.get('type', '')}; owner: {o.get('owner') or 'none'}; due: {o.get('due') or 'none'}]"
            db.x("INSERT INTO item_versions(item_id,action,old_text,new_text,changed_by,changed_at) VALUES (?,?,?,?,?,?)",
                 (iid, "edit", before, text, user, db.now()))
    db.x("UPDATE sources SET extracted=1 WHERE id=?", (sid,))     # already read: "Run extraction" must not duplicate these
    flags.recompute()
    rejected = sum(1 for r in rows if r["status"] == "Reject")
    skipped = sum(1 for r in rows if r["status"] == "Review")
    db.log(user, "paste_import", draft["name"],
           f"{len(approved)} approved ({edited} edited), {rejected} rejected, {skipped} left out, masked={draft['masked']}")
    return {"source_id": sid, "imported": len(approved), "edited": edited, "rejected": rejected, "left_out": skipped}
