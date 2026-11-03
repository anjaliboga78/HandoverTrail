# Architecture and data flow

```
 files / GitHub JSON  ->  ingest  ->  redact  ->  sources (SQLite)
                                                      |
                                      extract (LLM or offline)  ->  items
                                                      |
                                   Evidence Gate (quote must exist in source)
                                                      |
                              flags: conflicts / gaps / recurring problems
                                                      |
                     human review (approve / edit / reject, versioned)  ->  approved handover snapshot
                                                      |
                       role filter (BEFORE anything is built for the reader)
                                                      |
                  action plan + timeline + items + evidence  ->  acknowledge  ->  audit log
```

## Modules

| File | Responsibility |
|---|---|
| `core/redact.py` | Masks keys, passwords, emails, phones before storage and before any AI call |
| `core/ingest.py` | Files, CSV task lists, GitHub issues/commits (file or live API), demo loader |
| `core/extract.py` | LLM extractor and offline rule-based extractor, one output format, safe JSON parsing, chunking |
| `core/llm.py` | Provider-agnostic HTTP client (Anthropic, OpenAI, Gemini) |
| `core/verify.py` | **Evidence Gate**: exact or fuzzy match of the quote inside the source |
| `core/flags.py` | Conflicts (same topic, different tech/date), gaps (no owner), recurring risks; stored as ids, never as text naming hidden sources |
| `core/roles.py` | Visibility levels and role filter |
| `core/handover.py` | Review, versions, handover snapshots, role view, acknowledgement |
| `core/plan.py` | Rule-based Day 1 / Week 1 / Month 1 plan, every line cites item ids |
| `core/db.py` | SQLite schema and audit log |
| `ui.py` | Visual layer: CSS, chips, cards, stepper, plan columns, timeline |
| `app.py` | Streamlit screens |

## Key decisions

1. **Filter before generate.** Reader views, plans and flags are built only from items the role may see.
   Flags store ids; text describing a conflict is built per reader and omits anything they cannot see.
2. **The trust-critical parts are plain code**, not AI: redaction, Evidence Gate, role filter, approval rules.
3. **Approved snapshots are immutable.** Editing after approval requires a new handover version.
4. **Unverified items need an explicit human confirmation** before they can be approved.
5. **The AI never writes the action plan.** It is built from approved items only, so nothing is invented.

## Data model (SQLite)

users, sources, redactions (tag + masked preview only), items, item_versions, handovers (snapshot JSON),
acks, audit_log.
