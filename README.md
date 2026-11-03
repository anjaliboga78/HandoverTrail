# HandoverTrail

**Turn scattered project activity into structured, verified, and actionable team handovers.**

HandoverTrail is an intelligent project knowledge reconstruction and handover platform designed to prevent critical project knowledge from being lost when a team member leaves or changes responsibilities.

It collects information from meeting notes, chat exports, task lists, and GitHub activity, then reconstructs project context, identifies missing information and conflicts, and creates a structured handover for the incoming team member.

---

## The Problem

When a team member leaves a project, important knowledge often leaves with them.

- Important decisions are scattered across meetings and chats.
- Tasks may have missing or unclear owners.
- Technical information is difficult to locate.
- Pending responsibilities can be forgotten.
- Incoming members struggle to understand the project's history.

**HandoverTrail helps solve this problem by turning scattered project activity into a verified and organized handover.**

---

## How It Works

HandoverTrail follows five main steps:

| Step | Process | Description |
|---|---|---|
| 1 | Connect | Import meeting notes, chat exports, task lists, CSV files, or GitHub activity. |
| 2 | Reconstruct | Extract decisions, tasks, owners, blockers, risks, dependencies, and deadlines. |
| 3 | Verify | Check evidence, identify conflicting information, and detect missing details. |
| 4 | Review | Allow project leads to review, edit, approve, or reject extracted information. |
| 5 | Handover | Generate role-appropriate handovers with responsibilities, timelines, and action plans. |

---

## Key Features

### 1. Multiple Data Sources
- Upload TXT, Markdown, and CSV files.
- Import GitHub issues and commits.
- Paste meeting notes and project discussions.
- Load sample project data for demonstrations.
- Control source visibility using Lead, Core, and Everyone access levels.

### 2. Project Knowledge Reconstruction
Automatically identifies:
- Important decisions
- Tasks and deadlines
- Task owners
- Project blockers
- Risks and dependencies
- People to contact
- Missing owners
- Open questions

### 3. Evidence Verification
- Checks whether extracted information is supported by the original source.
- Classifies information as Verified, Approximate, or Unverified.
- Detects conflicting decisions and project information.
- Preserves evidence quotes for human review.
- Prevents unsupported information from being treated as verified.

### 4. Human Review and Approval
- Leads can approve, edit, or reject extracted information.
- Maintains item version history.
- Supports handover approval before sharing.
- Records important actions in the audit log.

### 5. Responsibility Transfer
- Identify responsibilities belonging to a departing member.
- Assign new owners.
- Propose, approve, reject, or cancel transfers.
- Track transfer progress.
- Allow the new owner to complete approved transfers.

### 6. Departure Checklist
- Automatically builds a checklist from project information.
- Tracks pending tasks and responsibility transfers.
- Highlights unresolved dependencies and conflicts.
- Shows completion progress.
- Supports notes and downloadable Markdown checklists.

### 7. Smart Handover Readiness Score
Provides a score out of 100 based on:
- Human review
- Verified evidence
- Documentation completeness
- Task ownership
- Responsibility transfers
- Checklist completion
- Resolved dependencies and conflicts
- Handover acknowledgement

### 8. Role-Based Handover
- Different visibility for Lead, Core, and Intern roles.
- Restricted information is not exposed to unauthorized users.
- Includes action plans for Day 1, Week 1, and Month 1.
- Supports acknowledgement of received handovers.

### 9. PDF Handover Report
Generate a structured PDF containing:
- Project overview
- Responsibilities and new owners
- Important decisions
- Pending tasks
- Readiness score
- Onboarding plan

### 10. Additional Features
- Project audit log
- Prompt-injection warning checks
- Sensitive information masking
- Multiple application themes
- Appearance customization
- Personal notes and reminders
- Markdown exports
- Animated startup screen

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Main application logic |
| Streamlit | User interface |
| SQLite | Local data storage |
| Pandas | Data processing |
| RapidFuzz | Text matching |
| Requests | API communication |
| Gemini / Anthropic / OpenAI APIs | Optional language-model extraction |
| ReportLab | PDF report generation |
| Pytest / unittest | Testing |

The application also includes a built-in rule-based offline extractor, allowing the core demonstration to work without an AI API key.

---

## Project Structure

```text
HandoverTrail/
│
├── app.py
├── splash.py
├── styles.py
│
├── core/
│   ├── config.py
│   ├── llm.py
│   ├── checklist.py
│   ├── transfer.py
│   └── ...
│
├── assets/
├── data/
├── docs/
├── tests/
├── ui/
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/anjaliboga78/HandoverTrail.git
cd HandoverTrail
```

### 2. Create a virtual environment

**Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**Linux / macOS:**

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables (optional)

Create a copy of `.env.example` named `.env`.

Choose a provider and configure the required API key and model settings.

Supported providers:

- `offline`
- `gemini`
- `anthropic`
- `openai`

The offline extractor works without an API key.

**Important:** Never upload your `.env` file or expose API keys publicly.

### 5. Run the application

```bash
streamlit run app.py
```

The application will open in your browser.

---

## Demo Walkthrough

To explore the application:

1. Sign in as **Riya (Lead)**.
2. Open Connect and load the demo project.
3. Run extraction and inspect reconstructed project information.
4. Review evidence, conflicts, missing owners, and unresolved questions.
5. Approve verified items and resolve conflicts.
6. Transfer responsibilities to new owners.
7. Review the departure checklist and readiness score.
8. Generate the PDF handover report.
9. Switch between Lead, Core, and Intern roles to explore access restrictions.
10. Review the audit log.

The demo uses fictional project data.

---

## Testing

Run the test suite using:

```bash
python -m unittest discover -s tests -v
```

Alternatively:

```bash
pytest
```

Tests cover important application areas such as evidence verification, redaction, permissions, approval rules, version history, transfers, and checklist functionality.

---

## Current Limitations

- The application primarily works with uploaded or exported project data rather than live chat-platform synchronization.
- The Evidence Gate verifies that supporting quotes exist; it does not guarantee that their meaning is correct.
- Human review is necessary before important information is approved.
- The offline extractor is rule-based and primarily designed for plain-English project information.
- Current role-based access is a demonstration system, not production-grade authentication with passwords or SSO.
- The application has primarily been tested with small synthetic datasets.
- Prompt-injection detection uses pattern-based warnings and should not be considered a complete security solution.

---

## Future Improvements

Potential improvements include:

- Interactive project knowledge graph
- AI-powered risk detection
- Knowledge search with evidence-backed answers
- Change impact analysis
- Knowledge decay detection
- Handover simulation for incoming members
- Live GitHub synchronization
- Slack and Google Drive integrations
- Production-grade authentication and workspace isolation

---

## AI and Development Disclosure

AI tools were used to assist with parts of the development, code generation, debugging, and documentation. The project was assembled, configured, and tested as an application.

The application supports optional language-model providers through environment configuration. The actual provider and model depend on the project's `.env` settings.

The core offline extraction workflow does not require an AI API.

All demonstration project data is fictional and created for this application.

---

## Project Information

**Project:** HandoverTrail  
**Category:** Project Knowledge Management / Team Handover  
**Repository:** [GitHub - HandoverTrail](https://github.com/anjaliboga78/HandoverTrail)

**Core Idea:**

Preserve project knowledge, identify risks, and make team transitions more reliable.

---

*Built to make sure important project knowledge doesn't leave when people do.*
