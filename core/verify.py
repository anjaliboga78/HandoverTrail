"""The Evidence Gate: does the quoted proof really exist in the cited source?"""
from __future__ import annotations
import difflib
import html
import re

try:
    from rapidfuzz import fuzz
except Exception:  # fall back to the standard library
    fuzz = None

MIN_QUOTE_CHARS = 12
APPROX_THRESHOLD = 92  # percent


def norm(s) -> str:
    s = (s or "").lower().replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    return " ".join(s.split())


def _approx_score(q: str, t: str) -> float:
    if fuzz is not None:
        return float(fuzz.partial_ratio(q, t))
    n = len(q)
    if n == 0 or not t:
        return 0.0
    best = 0.0
    step = max(1, n // 4)
    for i in range(0, max(1, len(t) - n + 1), step):
        r = difflib.SequenceMatcher(None, q, t[i:i + n]).ratio()
        best = max(best, r)
        if best >= 0.99:
            break
    return best * 100


def verify(quote, source_text):
    """Return (status, score). status is verified, approximate or unverified."""
    q, t = norm(quote), norm(source_text)
    if len(q) < MIN_QUOTE_CHARS:
        return "unverified", 0.0
    if q in t:
        return "verified", 100.0
    score = _approx_score(q, t)
    if score >= APPROX_THRESHOLD:
        return "approximate", round(score, 1)
    return "unverified", round(score, 1)


def highlight_html(source_text: str, quote: str) -> str:
    """HTML-escape the source and wrap the quote in <mark> if it can be located."""
    esc = html.escape(source_text)
    toks = [re.escape(html.escape(w)) for w in (quote or "").split()]
    if not toks:
        return esc
    m = re.search(r"\s+".join(toks), esc, flags=re.IGNORECASE)
    if not m:
        return esc
    return esc[:m.start()] + "<mark>" + esc[m.start():m.end()] + "</mark>" + esc[m.end():]
