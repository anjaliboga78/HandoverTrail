# HandoverTrail

Turns scattered project activity (meeting notes, chats, task lists, GitHub issues and commits) into a
**verified, human-approved, role-appropriate handover** for the person taking over a project.

Problem statement: *Prevent Critical Knowledge From Leaving With People.*

## The five steps (what a judge can do end to end)

| Step | Screen | What happens |
|---|---|---|
| 1 Connect | Connect | Upload files or connect a GitHub repo. Every source gets a visibility level. Keys, passwords, emails and phone numbers are masked **before** storage or any AI call. |
| 2 Reconstruct | Reconstruct and verify | Decisions, owners, blockers, risks, dependencies, contacts, next actions and open questions are extracted, with a timeline. |
| 3 Verify | Reconstruct and verify | The **Evidence Gate** checks that every quote really exists in its source. Items are Verified, Approximate or Unverified. Conflicts, gaps and recurring problems are flagged. |
| 4 Review | Review and approve | A Lead approves, edits or rejects each item (versioned), then approves the handover. |
| 5 Handover | Handover | The incoming person sees only what their role may see: action plan (Day 1 / Week 1 / Month 1), timeline, items, evidence. They acknowledge receipt. Everything is audit-logged. |

## Run it

```bash
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

No API key is needed: the default **offline extractor** is rule-based and works on the demo data.
To use a language model, copy `.env.example` to `.env`, set `LLM_PROVIDER` and the matching key.
If a key is missing or the AI call fails, the app tells you and falls back to the offline extractor for that source.

## Judge walk-through (about 3 minutes)

1. Sign in as **Riya (Lead)** > *1. Connect* > **Load the demo project**.
2. *2. Reconstruct and verify* > **Run extraction**. See conflicts (MySQL vs PostgreSQL, 10 vs 24 March),
   gaps (no owner for payments), and the recurring server crash. Pick an item to see its quote highlighted in the source.
3. *3. Review and approve* > **Approve all verified items...**, then resolve a conflict by hand. Open
   *Add an item by hand* and type an invented quote: the gate marks it **Unverified**. Click **Approve handover and share**.
4. Switch to **Aman (Intern)**: the sponsor note and chat are gone everywhere (plan, timeline, flags). Acknowledge receipt.
5. Switch to **Karan (Core)**: sees the chat but not the lead-only sponsor note. Back as Riya: *7. Audit log*.

## New in v7

- **Status flow** shown in the sidebar: Draft > Under review > Approved > Shared (first non-Lead opens it) > Acknowledged.
- **Who viewed** the handover is logged (once per person per version) and shown in the Audit log.
- **Withheld items**: a restricted reader sees a placeholder (item number and type, never the text) and who to ask.
- **Prompt-injection defence**: source text is marked as untrusted data in the model prompt; lines that look like commands to an AI are
  flagged on the Connect screen and in the audit log; and the Evidence Gate still blocks any item without a real quote.
- **Readiness score** (0-100, eight measured parts: 15 human review, 15 verified evidence, 15 documentation completeness, 15 task ownership, 15 responsibility transfers, 10 checklist items done, 10 dependencies and conflicts resolved, 5 receipt acknowledged). The Review screen shows points per part and the next steps, biggest loss first. Restricted items are counted, never named.
- **PDF Handover Report** (Handover screen): project overview, the departing member's responsibilities and new owners, important decisions, pending tasks, readiness score and an onboarding plan. It is built for the signed-in role only (restricted items are removed first and only counted), is masked once more, and each generation is written to the audit log.
- **Who is leaving**: pick a person to see everything they are the named owner of, and what is still unreviewed or unverified.
- **One-page summary** download (open it, press Ctrl+P, Save as PDF) next to the Markdown export.
- **Paste your notes** (v9, smart import) and a **sample picker** (load only some demo files) on the Connect screen.
  Paste text, press *Find tasks, decisions and deadlines*, and review an **editable preview** before anything is stored:
  - It finds **tasks** (with owner and due date), **decisions**, **deadlines**, **people** to contact, **missing owners** ("nobody owns...", "who will...", tasks with no name) and **open questions**. It understands headings such as *Action items:* and *Decisions:*, bullets, `[ ]` check boxes, chat lines and phrases like "Karan said he will...".
  - Each row says Approve, Review (decide later, not imported) or Reject. Edit the kind, item, owner or due date in place; the quote stays read-only because it is the proof.
  - Secrets are masked first. Only approved rows are imported, each still checked by the Evidence Gate, and they wait as *pending* for a Lead to review in step 3. Your edits are kept in each item's version history.
  - Works with no AI key (rule-based reader). With an AI provider configured, the masked text is read by that model instead and the same preview applies.
  - *Add as plain source (no preview)* keeps the old behaviour. New item type: **Deadline**.

## Departure Checklist (v10)

Screen **6. Departure checklist** (everyone can open it; a Lead or the leaving person can change it): pick who is leaving and see what is left.
- Five sections, **built from your real items and transfers every time** (nothing invented): **Responsibility transfers**, **Pending tasks**, **Important decisions**, **Technical documentation** (one line per technical topic they own: database, payments, deployment, access) and **Unresolved dependencies** (dependencies, blockers, open questions and "nobody owns it" lines that name them).
- **Tick lines complete**, untick, add a note (a link, a name) or add your own line. Every tick is in the audit log with who and when.
- **Responsibility transfers cannot be ticked by hand**: they finish when the transfer is completed on screen 5, because a tick would not change who owns the item. A task that is transferred counts as done too.
- **Progress**: percent done overall and per section, plus **What still needs attention**, ranked: no new owner proposed, conflicts, unverified proof, waiting for approval, not yet reviewed.
- Restricted items show only as "Restricted item #id (type)" and are left out of the numbers. **Download checklist (.md)** gives a copy.
- Code: `core/checklist.py`, tests in `tests/test_checklist.py`. The Audit log is now screen **7**.

## Responsibility Transfer (v8)

Screen **5. Transfer responsibilities** (Lead): pick who is leaving and see every task and responsibility they own, with its proof.
- Give each one a new owner (or assign all unassigned items to one person). Each becomes a **transfer**: *Waiting for approval* >
  *Approved, waiting for the new owner* > *Completed*, or *Rejected* / *Cancelled*.
- **Approval gate**: only a Lead approves; if another Lead exists, you cannot approve your own proposal. A transfer cannot be
  completed before it is approved, and only the new owner or a Lead can complete it.
- Completing a transfer changes the item's owner (saved as an item version). The proof quote is never changed.
  Approve a new handover version afterwards so readers see the change.
- Tabs: Responsibilities, Pending, Completed, History (every step with who and when). A progress bar shows how much has moved.
- The new owner sees "Responsibilities moving to you" on their Handover screen, only for items their role may see.
- Code: `core/transfer.py`, tests in `tests/test_transfer.py`. Audit log records propose, approve, reject, complete and cancel.

## Start-up screen (v6)

When the app opens, the logo arrives in four short scenes (about 6.5 seconds, pure CSS, no JavaScript): **sources spiral in**
(Meeting notes, Chat, Tasks, GitHub), **five dots roll in** (the five steps), **letters fly in** (the name assembles), then
**the taped logo card lands and the tagline fades in** (no sticky notes: that scene was removed to keep the screen calm).
It plays once per visit, matches the active theme, and can be skipped with a click. Turn it off in Appearance
(*Play the start-up animation*) or with *Reduce tilt and motion*. Code: `splash.py`.
To change the length, edit the start times in `splash.py` (every scene is a block of CSS with its own start time) and keep
`TOTAL_SECONDS` equal to the fade-out time (`spOut`) plus 0.5 s.

## Themes and My notes (v3)

**Twenty themes** (Notebook, Clean, Midnight, Chalkboard, Sunrise, Ocean, Lavender, Easy read, Trail map, Blueprint, Pop,
Terminal, plus new: Forest, Sakura, Coffee, Mint, Newsprint, Graphite, Synthwave, Aurora). Switch from *Quick look* in the sidebar, or open **Appearance** for live preview tiles plus: accent colour,
writing style, text size, density, sticky notes or flat cards, high contrast, reduce tilt and motion, paper pattern on/off,
*Surprise me*, and *Midnight automatically from 7 pm to 6 am*. Choices are saved per signed-in person in the workspace
database. Code: `core/themes.py` (themes are plain data) and `styles.py` (all rules use CSS variables).

**My notes** (sidebar button, opens a full screen of its own: composer on the left, sticky-note board on the right with
search, type filter and *Hide done*; *Back to the app* returns you to where you were):
- Types: To-do, Question, Idea, Heads-up, I learned. Sticky colours. Pin, mark done, edit, delete (author only).
- Visibility: *Only me* (default), *My team*, *Leads only* (an Intern can use this to ask a Lead).
- Link a note to an item: it appears as a small sticky on that item's card. You can only link to items you may see, and a
  note about a restricted item is invisible to people who cannot see that item.
- Reminders in plain words (`tomorrow`, `in 3 days`, `friday`, `12 Nov`); due and overdue notes show a banner and a *Due* filter.
- Quiet warnings: "Item #22 was edited after you wrote this", "has a conflict", "was rejected".
- **Notes are not evidence.** They never enter a handover or its export. A Lead can *promote* a note only with an exact quote
  from a source; the app suggests matching lines, and the quote must pass the Evidence Gate. The new item still needs normal review.
- Secrets and personal data in notes are masked before saving. The audit log records that a note was made, shared, promoted or
  deleted, never its text. Your notes can be downloaded as Markdown.

## Docs

- `docs/SETUP.md`: step-by-step laptop setup, GitHub and online deployment
- `docs/HOW_IT_WORKS.md`: what each screen and module does
- `docs/ARCHITECTURE.md`: data flow and key decisions

## Tests

```bash
python -m unittest discover -s tests -v      # or: pytest
```

The tests cover redaction, the Evidence Gate, permissions (an Intern never receives restricted items or flags),
approval rules, version history, acknowledgement, and a full walk through every screen.

## Public link

Set `HT_PUBLIC=1` on the host: every visitor gets a private temporary workspace and the AI key cannot be used by strangers. See `docs/SETUP.md`.

## Known limitations (honest list)

- Works on exported text, CSV and GitHub data, not live chat platforms.
- The Evidence Gate proves a quote **exists**, not that its meaning was understood. Human review is required.
- The offline extractor is rule-based and tuned for plain-English notes; the language-model extractor is more flexible.
- Roles are a demo login (no passwords/SSO). Production would use real authentication.
- Tested on small synthetic data, mainly in English.
- Planned for Round 3 (not built yet): cited Q&A, knowledge-risk radar with a pre-departure checklist.
- Prompt-injection checks are pattern-based; they warn a human and the Evidence Gate is the real safeguard.

## Disclosure (AI, libraries, data)

- AI assistance: an AI assistant (Claude) helped write and structure this code and the documents. The team reviewed and ran it, and the automated tests pass.
- Language model for Round 2 (disclosed): **Anthropic Claude (Sonnet) via the Anthropic API**, used only when `LLM_PROVIDER=anthropic` and a key is set, always after redaction. OpenAI and Gemini are optional alternatives. The demo works fully offline with no model.
- Libraries: Streamlit, pandas, requests, python-dotenv, rapidfuzz (all open source).
- Data: all demo data is synthetic and written for this project. No real or confidential data is used.
