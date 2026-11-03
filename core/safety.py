"""Prompt-injection defence. Source text is DATA, never instructions.

Three layers: (1) the model prompt says so and wraps the source in markers, (2) suspicious lines are
flagged to the human at import, (3) the Evidence Gate still rejects any item whose quote is not in the source.
"""
from __future__ import annotations
import re

PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above|earlier) (instructions|rules|prompts?)",
    r"disregard (all |any )?(the )?(previous|prior|above|earlier|your) (instructions|rules|prompts?)",
    r"forget (all |your |the )?(previous|prior|earlier)? ?(instructions|rules)",
    r"(you are|act as|pretend to be) (now )?(an? )?(different|new|unrestricted|dan)\b",
    r"\bsystem prompt\b",
    r"reveal (your|the) (instructions|prompt|api key|secret)",
    r"(mark|set|treat) (all|every) (items?|quotes?) (as )?(verified|approved)",
    r"do not (flag|report|mention) (this|these|any)",
    r"\bnew instructions?\s*:",
]
_RX = [re.compile(p, re.I) for p in PATTERNS]


def find_injection(text: str) -> list:
    """Return up to 5 (line_number, line) pairs that look like instructions aimed at an AI."""
    hits = []
    for n, line in enumerate((text or "").splitlines(), 1):
        if any(r.search(line) for r in _RX):
            hits.append((n, line.strip()[:160]))
            if len(hits) == 5:
                break
    return hits
