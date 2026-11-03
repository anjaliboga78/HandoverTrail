"""Settings and constants for HandoverTrail."""
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")
except Exception:  # python-dotenv is optional
    pass

DB_PATH = os.environ.get("HT_DB", str(BASE / "data" / "handovertrail.db"))
DEMO_DIR = BASE / "data" / "demo"

# Visibility of a source (and of every item extracted from it).
LEVELS = {"Everyone": 1, "Core": 2, "Lead": 3}
# What each role is allowed to see.
ROLE_LEVEL = {"Intern": 1, "Core": 2, "Lead": 3}

ITEM_TYPES = ["decision", "owner", "open_question", "blocker", "risk",
              "dependency", "contact", "next_action", "deadline"]
TYPE_LABEL = {
    "decision": "Decision", "owner": "Ownership", "open_question": "Open question",
    "blocker": "Blocker", "risk": "Risk", "dependency": "Dependency",
    "contact": "Contact", "next_action": "Next action", "deadline": "Deadline",
}


def llm_provider() -> str:
    """offline (rule-based demo extractor), anthropic, openai or gemini."""
    return os.environ.get("LLM_PROVIDER", "offline").strip().lower()
