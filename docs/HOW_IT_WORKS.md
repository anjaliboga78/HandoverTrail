# What was built and how it works

## The idea in one line
When someone leaves a project, rebuild what they knew from the material the team already has, prove every claim
with its source, flag what is uncertain, let a human approve it, and show each reader only what their role may see.

## What is in the app (screen by screen)

| Screen | What the user does | What the code does |
|---|---|---|
| 1 Connect | Uploads notes, chats, CSV tasks, GitHub JSON, or loads the demo; sets who may see each source | `core/ingest.py` parses each file, `core/redact.py` masks keys, passwords, emails and phones **before** storing, and records only a masked preview |
| 2 Reconstruct and verify | Clicks Run extraction, inspects any item and its highlighted proof | `core/extract.py` extracts decisions, owners, blockers, risks, dependencies, contacts, next actions and open questions with an exact quote; `core/verify.py` (the **Evidence Gate**) checks the quote exists; `core/flags.py` finds conflicts, gaps and recurring problems |
| 3 Review and approve | Approves, edits or rejects each item; adds an item by hand; approves the whole handover | `core/handover.py` stores every change as a version, requires a human tick for unverified items, lets only a Lead approve, and freezes an immutable snapshot per version |
| 4 Handover | Reads the action plan, timeline, items and proof; acknowledges receipt | The snapshot is filtered by role first (`core/roles.py`), then `core/plan.py` builds a Day 1 / Week 1 / Month 1 plan only from what that role may see |
| 5 Transfer responsibilities | Gives everything a leaving person owns a new owner; a Lead approves each transfer | `core/transfer.py` |
| 6 Departure checklist | Picks who is leaving; ticks off transfers, tasks, decisions, documentation and dependencies; sees progress and what needs attention | `core/checklist.py` builds the list from real items and transfers; only the ticks and notes are stored |
| 7 Audit log | Sees who did what and when | `core/db.py` logs imports, extraction, edits, approvals, role switches and acknowledgements |

## How the trust rules are enforced (in code, not just in words)
- **Traceable:** every item has `quote` and `source_id`. The Evidence Gate marks it Verified, Approximate or Unverified.
- **No invention:** an unverified item can only enter a handover if a human ticks "I checked the source myself".
- **Permission-aware:** restricted items are removed before a view, plan, flag or timeline is built. Flags are stored as item ids,
  and their text is produced per reader, so a hidden source is never named. Tests prove an Intern never receives lead-only or core-only content.
- **Human control:** only a Lead can approve. Nothing is visible to others before approval.
- **Uncertainty shown:** conflicts (MySQL vs PostgreSQL, 10 vs 24 March), gaps (no owner) and recurring problems (the server crash) are labelled, never merged.

## The two extractors
1. **Offline rule-based** (default): looks for phrases like "we decided", "blocked by", "nobody owns", "will", "?" and copies the exact sentence as the quote. It makes the whole workflow runnable and testable with no key.
2. **Language model** (optional): `core/llm.py` calls Anthropic, OpenAI or Gemini over plain HTTPS with a strict prompt: use only the text, copy quotes exactly, return JSON. The reply is parsed safely, retried once, and every item still goes through the Evidence Gate.

## The look (frontend)
`ui.py` holds all styling and HTML building: a hero banner, a five-step progress stepper that updates from the database,
item cards with chips (type, evidence, conflict, gap, recurring), a three-column action plan, a visual timeline, and highlighted proof boxes.
All user text is HTML-escaped. `.streamlit/config.toml` sets the colour theme.

## Tests
`tests/test_core.py` (redaction, gate, permissions, approvals, plan, parsing) and `tests/test_app_smoke.py`
(walks every screen as Lead, Core and Intern). About 37 tests, all passing at the time of delivery.

## What is NOT done yet (your Round 3 promises and honest limits)
- Stronger conflict and gap detection across paraphrased statements (today: same topic with different technology or dates).
- The cited question-and-answer assistant, and the Knowledge Risk Radar from commit data.
- Real login (today: a demo user switcher), live Slack or email connectors, and a private language model.
- The language-model path and the live GitHub connector need internet and were not exercised in the build environment.
- The screens were checked with an automated stand-in for Streamlit and a static visual preview, so open the real app once and report anything odd.
