"""Mask secrets and personal data BEFORE anything is stored or sent to an AI service."""
from __future__ import annotations
import re

RULES = [
    ("KEY", r"\b(?:sk|pk|rk|api|key|token)[_-][A-Za-z0-9_\-]{8,}\b"),
    ("KEY", r"\bAKIA[0-9A-Z]{16}\b"),
    ("PASSWORD", r"(?i)\b(?:password|passwd|pwd|pass)\s*(?:is|:|=)\s*\S+"),
    ("EMAIL", r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    ("PHONE", r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)"),
]


def _preview(s: str) -> str:
    s = s.strip()
    return (s[:2] + "***") if len(s) > 3 else "***"


def redact(text: str):
    """Return (clean_text, [(tag, preview), ...]). The original secret is never stored."""
    found = []
    for tag, pat in RULES:
        def sub(m, tag=tag):
            found.append((tag, _preview(m.group())))
            return f"[REDACTED-{tag}]"
        text = re.sub(pat, sub, text)
    return text, found
