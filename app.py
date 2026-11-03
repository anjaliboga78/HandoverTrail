"""HandoverTrail - turn scattered project activity into a verified, role-appropriate handover.

Run with:  streamlit run app.py
"""
import os
import re
import uuid
from collections import Counter

import pandas as pd
import streamlit as st

import splash
import ui
from core import checklist, config, db, extract, flags, handover, ingest, llm, notes, paste, plan, readiness, report, roles, safety, themes, transfer
from ui import STATUS_TEXT, type_label

st.set_page_config(page_title="HandoverTrail", page_icon=str(config.BASE / "assets" / "icon.png"), layout="wide")

BADGE = {"verified": ":green[Verified]", "approximate": ":orange[Approximate]", "unverified": ":red[Unverified]"}
PAGES_LEAD = ["1. Connect", "2. Reconstruct and verify", "3. Review and approve", "4. Handover", "5. Transfer responsibilities", "6. Departure checklist", "7. Audit log"]
PAGES_OTHER = ["4. Handover", "6. Departure checklist"]
SUBTITLE = "Rebuild what a leaving teammate knew, prove it with sources, and hand it over safely."


# ------------------------------------------------------------------ helpers
PUBLIC = os.environ.get("HT_PUBLIC") == "1"  # public deployment: private workspace per visitor


def setup_workspace() -> None:
    """In public mode every visitor gets a private, temporary database. Locally there is one shared file."""
    if PUBLIC:
        ws_dir = str(config.BASE / "data" / "workspaces")
        if "ws" not in st.session_state:
            st.session_state["ws"] = uuid.uuid4().hex[:12]
            db.cleanup_workspaces(ws_dir, 24)
        db.use_path(os.path.join(ws_dir, st.session_state["ws"] + ".db"))
    db.init()


def provider_for_session() -> str:
    """Public visitors use the free offline extractor unless the owner explicitly allows the paid/keyed model."""
    if PUBLIC and os.environ.get("HT_PUBLIC_LLM") != "1":
        return "offline"
    return config.llm_provider()


def html(s: str) -> None:
    st.markdown(s, unsafe_allow_html=True)


def items_by_id(items: list) -> dict:
    return {i["id"]: i for i in items}


def flag_text(item: dict, lookup: dict, role: str) -> str:
    return " | ".join(flags.describe(item, lookup, role))


def summary_counts(items: list) -> dict:
    c = Counter(i["verify_status"] for i in items)
    return {"total": len(items), "verified": c.get("verified", 0), "approximate": c.get("approximate", 0),
            "unverified": c.get("unverified", 0), "conflicts": sum(1 for i in items if i["is_conflict"]),
            "gaps": sum(1 for i in items if i["is_gap"]), "recurring": sum(1 for i in items if i["is_recurring"])}


def show_metrics(counts: dict) -> None:
    cols = st.columns(6)
    cols[0].metric("Items", counts["total"])
    cols[1].metric("Verified", counts["verified"])
    cols[2].metric("Approximate", counts["approximate"])
    cols[3].metric("Unverified", counts["unverified"])
    cols[4].metric("Conflicts", counts["conflicts"])
    cols[5].metric("Gaps", counts["gaps"])


def progress_state() -> tuple:
    has_src = bool(db.one("SELECT 1 AS x FROM sources"))
    has_items = bool(db.one("SELECT 1 AS x FROM items"))
    has_appr = bool(db.one("SELECT 1 AS x FROM items WHERE review_status='approved'"))
    has_ho = bool(handover.current_handover())
    done = {"Connect": has_src, "Reconstruct": has_items, "Verify": has_items, "Review": has_appr and has_ho,
            "Handover": has_ho and bool(db.one("SELECT 1 AS x FROM acks"))}
    current = next((n for n in ["Connect", "Reconstruct", "Verify", "Review", "Handover"] if not done[n]), "Handover")
    return done, current


def paste_box(user: str) -> None:
    """Paste your notes: read them, show an editable preview, import only what a person approves."""
    draft = st.session_state.get("paste_draft")
    if not draft:
        pname = st.text_input("Name for these notes", value="Pasted notes", key="p_name")
        ptext = st.text_area("Paste meeting notes, a chat export or anything written (secrets are masked before anything is read or stored)",
                             height=160, key="p_text")
        pc1, pc2 = st.columns(2)
        pvis = pc1.selectbox("Who may see it?", list(config.LEVELS), index=0, key="p_vis")
        pdate = pc2.text_input("Date (optional, YYYY-MM-DD)", key="p_date")
        b1, b2 = st.columns(2)
        read = b1.button("Find tasks, decisions and deadlines", key="p_read")
        plain = b2.button("Add as plain source (no preview)", key="p_plain")
        if (read or plain) and pdate and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", pdate):
            st.error("Use the date format YYYY-MM-DD.")
        elif read:
            try:
                with st.spinner("Reading your notes..."):
                    d = paste.analyze(pname, ptext, pvis, pdate or None, provider_for_session())
                st.session_state["paste_draft"] = d
                st.session_state["paste_v"] = st.session_state.get("paste_v", 0) + 1
                st.rerun()
            except ValueError as e:
                st.error(str(e))
        elif plain:
            try:
                ingest.add_pasted(pname, ptext, pvis, pdate or None, user)
                st.success("Added as a plain source. Run extraction on the next screen.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
        return

    rows = draft["rows"]
    st.markdown(f"**Preview of \"{draft['name']}\"** (visible to {draft['visibility']}). Nothing is saved yet.")
    st.caption(f"Read by: {draft['reader']}. Secrets masked: {draft['masked']}. Every row below is a suggestion, not verified, "
               "until you approve it. Approved rows still have to pass the Evidence Gate (the quote must be in your text) "
               "and wait for a Lead's review in step 3.")
    for w in draft["warnings"]:
        st.warning(w)
    if not rows:
        st.info("Nothing that looks like a task, decision, deadline, person or open question was found. "
                "You can discard this and try other text, or add it as a plain source.")
        c1, c2 = st.columns(2)
        if c1.button("Discard", key="p_discard0"):
            st.session_state.pop("paste_draft", None)
            st.rerun()
        if c2.button("Add as plain source instead", key="p_plain0"):
            ingest.add_pasted(draft["name"], draft["text"], draft["visibility"], draft["date"], user)
            st.session_state.pop("paste_draft", None)
            st.success("Added as a plain source. Run extraction on the next screen.")
            st.rerun()
        return

    found = paste.summary(rows)
    st.write("Found: " + ", ".join(f"{n} {k.lower()}" for k, n in found.items()))
    if draft["people"]:
        st.write("People named: " + ", ".join(f"{k} ({n})" for k, n in sorted(draft["people"].items())))
    st.caption("Pick Approve, Review (decide later, not imported) or Reject in the first column. "
               "Click any cell to edit the kind, item, owner or due date. The quote is read-only: it is the proof.")

    table = pd.DataFrame(paste.rows_to_table(rows))
    edited = st.data_editor(
        table, hide_index=True, use_container_width=True, num_rows="fixed",
        key=f"paste_editor_{st.session_state.get('paste_v', 0)}",
        disabled=["Heads-up", "Quote from your notes"],
        column_config={
            "Import?": st.column_config.SelectboxColumn("Import?", options=paste.STATUS_OPTIONS, required=True, width="small"),
            "Kind": st.column_config.SelectboxColumn("Kind", options=paste.KIND_OPTIONS, required=True, width="small"),
            "Item": st.column_config.TextColumn("Item", width="large", required=True),
            "Owner / person": st.column_config.TextColumn("Owner / person", width="small"),
            "Due": st.column_config.TextColumn("Due", width="small"),
            "Heads-up": st.column_config.TextColumn("Heads-up", width="medium"),
            "Quote from your notes": st.column_config.TextColumn("Quote from your notes", width="large"),
        })
    try:
        current = paste.apply_table(rows, edited.to_dict("records") if edited is not None else paste.rows_to_table(rows))
    except ValueError:
        current = rows
    for kind, msg in paste.live_checks(current):
        (st.error if kind == "error" else st.warning)(msg)
    cnt = paste.counts(current)
    st.caption(f"{cnt['Approve']} to import, {cnt['Review']} left for later, {cnt['Reject']} rejected.")

    def keep_edits(new_rows: list) -> None:
        draft["rows"] = new_rows
        st.session_state["paste_v"] = st.session_state.get("paste_v", 0) + 1
        st.rerun()

    b = st.columns(4)
    if b[0].button("Approve all clean rows", key="p_ok_clean"):
        keep_edits(paste.set_all(current, "Approve", only_clean=True))
    if b[1].button("Approve all", key="p_ok_all"):
        keep_edits(paste.set_all(current, "Approve"))
    if b[2].button("Reject all", key="p_no_all"):
        keep_edits(paste.set_all(current, "Reject"))
    if b[3].button("Discard this preview", key="p_discard"):
        st.session_state.pop("paste_draft", None)
        st.rerun()
    errors = [m for k, m in paste.live_checks(current) if k == "error"]
    if st.button(f"Import {cnt['Approve']} approved item(s)", key="p_import", type="primary", disabled=not cnt["Approve"] or bool(errors)):
        try:
            res = paste.import_approved(draft, current, user)
            st.session_state.pop("paste_draft", None)
            st.session_state["paste_done"] = (f"Imported {res['imported']} item(s) ({res['edited']} edited by you). "
                                              f"{res['rejected']} rejected, {res['left_out']} left out. "
                                              "They wait for review in step 3; nothing is in the handover until a Lead approves it.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))


# ------------------------------------------------------------------ 1. Connect
def page_connect(user: str) -> None:
    st.header("1. Connect your sources")
    st.write("Bring in only material you are allowed to use. Secrets and personal data are masked "
             "**before** anything is stored or sent to an AI service, and every source gets a visibility level.")

    if st.session_state.get("paste_done"):
        st.success(st.session_state.pop("paste_done"))
    has_sources = bool(db.one("SELECT 1 AS x FROM sources"))
    if not has_sources:
        html("<div class='start'><h3>Start here</h3>Load the demo project to see the whole workflow in a minute: "
             "a made-up club app with planted conflicts, gaps, secrets and a lead-only note. "
             "Or upload your own files below.</div>")
        if st.button("Load the demo project"):
            n = ingest.load_demo(user)
            st.success(f"Loaded {n} demo sources.")
            st.rerun()

    with st.expander("Sample picker: load only some demo files"):
        picks = st.multiselect("Demo files", ingest.demo_file_names(), key="demo_pick")
        if st.button("Load the chosen demo files") and picks:
            st.success(f"Loaded {ingest.load_demo_files(picks, user)} source(s).")
            st.rerun()
    with st.expander("Paste your notes", expanded=bool(st.session_state.get("paste_draft"))):
        paste_box(user)

    left, right = st.columns(2)
    with left:
        st.subheader("Upload files")
        files = st.file_uploader("Meeting notes, chat exports, task lists (.txt .md .csv) or GitHub JSON",
                                 type=["txt", "md", "csv", "json"], accept_multiple_files=True)
        vis = st.selectbox("Who may see these sources?", list(config.LEVELS), index=0,
                           help="Everyone: all roles. Core: Core members and Leads. Lead: Leads only.")
        date_txt = st.text_input("Source date (optional, YYYY-MM-DD)", value="")
        if st.button("Import files"):
            if date_txt and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_txt):
                st.error("Use the date format YYYY-MM-DD.")
            elif not files:
                st.warning("Choose at least one file first.")
            else:
                done = 0
                for f in files:
                    try:
                        done += len(ingest.ingest_upload(f.name, f.getvalue(), vis, date_txt or None, user))
                    except ValueError as e:
                        st.error(str(e))
                if done:
                    st.success(f"Imported {done} source(s).")
    with right:
        st.subheader("Connect a GitHub repository")
        repo = st.text_input("Repository (owner/name)", value="")
        token = st.text_input("GitHub token (optional, read-only)", value="", type="password")
        gvis = st.selectbox("Visibility", list(config.LEVELS), index=0, key="gvis")
        if st.button("Import from GitHub"):
            try:
                n = ingest.import_github(repo.strip(), token.strip() or None, gvis, user)
                st.success(f"Imported {n} source(s) from {repo}.")
            except (ValueError, RuntimeError) as e:
                st.error(str(e))
        if has_sources:
            st.subheader("Demo project")
            st.caption("Already loaded. Use Reset below for a clean start.")

    sources = db.q("SELECT id, name, type, source_date, visibility, redaction_count, extracted FROM sources ORDER BY id")
    st.subheader(f"Sources ({len(sources)})")
    if sources:
        df = pd.DataFrame(sources).rename(columns={
            "name": "Source", "type": "Type", "source_date": "Date", "visibility": "Visible to",
            "redaction_count": "Secrets masked", "extracted": "Processed"})
        df["Processed"] = df["Processed"].map({0: "no", 1: "yes"})
        st.dataframe(df, use_container_width=True, hide_index=True)
        flagged = []
        for sr in db.q("SELECT name, text FROM sources"):
            for ln, line in safety.find_injection(sr["text"]):
                flagged.append({"Source": sr["name"], "Line": ln, "Text": line})
        if flagged:
            st.warning("Some lines look like instructions aimed at an AI. They are treated as plain data and cannot "
                       "change the result, and every item still has to pass the Evidence Gate. Check them anyway.")
            st.dataframe(pd.DataFrame(flagged), use_container_width=True, hide_index=True)
        with st.expander("What was masked (the originals are never stored)"):
            red = db.q("SELECT s.name AS source, r.tag, r.preview FROM redactions r JOIN sources s ON s.id=r.source_id")
            if red:
                st.dataframe(pd.DataFrame(red), use_container_width=True, hide_index=True)
            else:
                st.caption("Nothing needed masking.")
    else:
        st.info("No sources yet. Upload files or load the demo project.")

    with st.expander("Danger zone"):
        sure = st.checkbox("I understand this deletes all sources, items, handovers and the audit log")
        if st.button("Reset everything") and sure:
            db.reset_all()
            db.log(user, "reset", "all data")
            st.success("All data deleted.")
            st.rerun()


# ------------------------------------------------------------------ 2. Reconstruct and verify
def page_reconstruct(user: str, role: str) -> None:
    st.header("2. Reconstruct and verify")
    provider = provider_for_session()
    if provider == "offline":
        st.info("Extractor: **offline rule-based demo extractor** (no API key needed). "
                "Set LLM_PROVIDER and an API key in .env to use a language model. "
                "Either way, every item must pass the Evidence Gate.")
    elif llm.available(provider):
        st.info(f"Extractor: **{provider}** language model. Every item must pass the Evidence Gate.")
    else:
        st.warning(f"LLM_PROVIDER is '{provider}' but no API key was found, so the offline extractor will be used.")

    pending = db.q("SELECT COUNT(*) AS n FROM sources WHERE extracted=0")[0]["n"]
    c1, c2 = st.columns(2)
    if c1.button(f"Run extraction ({pending} new source(s))"):
        if pending == 0:
            st.warning("Nothing new to process.")
        else:
            with st.spinner("Reading sources and checking every quote..."):
                result = extract.run_extraction(user, provider=provider)
            for w in result["warnings"]:
                st.warning(w)
            st.success(f"Found {result['items']} items in {result['sources']} source(s).")
    again = c2.checkbox("Re-run everything (this clears all reviews, except items you approved from pasted notes)")
    if again and c2.button("Re-run for all sources"):
        with st.spinner("Re-running..."):
            result = extract.run_extraction(user, provider=provider, force=True)
        st.success(f"Found {result['items']} items.")

    items = handover.list_items()
    if not items:
        st.info("No items yet. Import sources, then run extraction.")
        return
    lookup = items_by_id(items)
    counts = summary_counts(items)
    show_metrics(counts)
    html(ui.status_bars(counts))
    st.caption("Verified = the quote was found exactly. Approximate = tiny wording difference. "
               "Unverified = the quote was not found, so it is never treated as fact.")

    types = st.multiselect("Show types", config.ITEM_TYPES, default=config.ITEM_TYPES, format_func=type_label)
    only_flag = st.checkbox("Only items with a flag (conflict, gap, recurring, unverified)")
    shown = [i for i in items if i["type"] in types and (not only_flag or flag_text(i, lookup, "Lead"))]
    st.caption(f"Showing {len(shown)} of {len(items)} items")
    nmap = notes.by_item(user, role)
    for i in shown:
        html(ui.item_card(i, lookup, "Lead", show_visibility=True, notes=nmap.get(i["id"]), viewer=user))
    with st.expander("Table view"):
        rows = [{"#": i["id"], "Type": type_label(i["type"]), "Item": i["text"], "Owner": i["owner"] or "-",
                 "Evidence": STATUS_TEXT[i["verify_status"]], "Flags": flag_text(i, lookup, "Lead") or "-",
                 "Source": i["source_name"], "Date": i["item_date"] or "-", "Visible to": i["visibility"]} for i in shown]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("Inspect the evidence")
    options = [i["id"] for i in items]
    pick = st.selectbox("Choose an item", options,
                        format_func=lambda n: f"#{n}  {type_label(lookup[n]['type'])}: {lookup[n]['text'][:80]}")
    it = lookup[pick]
    st.markdown(f"**{it['text']}**  \n{BADGE[it['verify_status']]} (match {it['verify_score']:.0f}%)  "
                f"| source: `{it['source_name']}` | extractor: {it['extractor']}")
    st.caption("Quote the item claims as proof (highlighted in the source below):")
    src = db.one("SELECT text FROM sources WHERE id=?", (it["source_id"],))
    html(ui.evidence_html(src["text"], it["quote"]))

    with st.expander("Timeline of decisions, risks and open questions"):
        html(ui.timeline_html(handover.timeline(
            [i for i in items if i["type"] in ("decision", "risk", "blocker", "open_question")])))


# ------------------------------------------------------------------ 3. Review and approve
def page_review(user: str, role: str) -> None:
    st.header("3. Review and approve")
    st.write("Nothing is shared until a Lead approves it. Approve, edit or reject each item. "
             "Every change is saved as a version.")
    items = handover.list_items()
    if not items:
        st.info("No items yet. Run extraction first.")
        return
    lookup = items_by_id(items)
    c = Counter(i["review_status"] for i in items)
    m = st.columns(4)
    m[0].metric("Pending", c.get("pending", 0))
    m[1].metric("Approved", c.get("approved", 0))
    m[2].metric("Rejected", c.get("rejected", 0))
    m[3].metric("Items", len(items))

    rd = readiness.readiness(role)
    html(ui.notice(f"Handover readiness: {rd['score']}/100 ({rd['band']}). Status: {readiness.status_flow()}."))
    with st.expander("Score breakdown: what is holding the score back", expanded=True):
        html(ui.readiness_html(rd))
        st.caption("Score = 15 human review + 15 verified evidence + 15 documentation + 15 task ownership + "
                   "15 responsibility transfers + 10 checklist + 10 dependencies and conflicts + 5 receipt acknowledged. "
                   "Restricted items are counted, never listed.")
    with st.expander("Who is leaving?"):
        people = readiness.leaving_people()
        if people:
            who = st.selectbox("Who is leaving?", people, key="leaver")
            ls = readiness.leaving_summary(who)
            st.write(f"**{who}** is named owner of **{len(ls['owned'])}** item(s); "
                     f"**{len(ls['sole'])}** are decisions, ownerships, blockers, risks or dependencies that only they are named on. "
                     f"{ls['unreviewed']} not yet reviewed, {ls['unverified']} unverified, mentioned in {ls['mentions']} other item(s).")
            if ls["owned"]:
                st.dataframe(pd.DataFrame([{"#": i["id"], "Type": type_label(i["type"]), "Item": i["text"],
                                            "Evidence": STATUS_TEXT[i["verify_status"]], "Review": i["review_status"]}
                                           for i in ls["owned"]]), use_container_width=True, hide_index=True)
            st.caption("Owners come from the sources. Ask them to confirm these before they go.")

    if st.button("Approve all verified items that have no conflict"):
        n = handover.approve_all_verified(user)
        st.success(f"Approved {n} item(s). Conflicts and unverified items still need a human decision.")
        st.rerun()

    nmap = notes.by_item(user, role)
    view = st.radio("Show", ["pending", "approved", "rejected", "all"], horizontal=True)
    shown = [i for i in items if view == "all" or i["review_status"] == view]
    st.caption(f"{len(shown)} item(s)")
    for i in shown:
        label = (f"#{i['id']} [{type_label(i['type'])}] {i['text'][:90]}  "
                 f"({STATUS_TEXT[i['verify_status']]}, {i['review_status']})")
        with st.expander(label):
            html(ui.item_card(i, lookup, role, show_visibility=True, notes=nmap.get(i["id"]), viewer=user))
            st.caption("Proof quote in its source:")
            src = db.one("SELECT text FROM sources WHERE id=?", (i["source_id"],))
            html(ui.evidence_html(src["text"], i["quote"]))
            new_text = st.text_area("Item text (edit if needed)", value=i["text"], key=f"txt{i['id']}")
            checked = True
            if i["verify_status"] == "unverified":
                checked = st.checkbox("I checked the source myself and this is correct", key=f"chk{i['id']}")
            b = st.columns(4)
            if b[0].button("Approve", key=f"ap{i['id']}"):
                if checked:
                    handover.set_review(i["id"], "approved", user, new_text)
                    st.rerun()
                else:
                    st.error("Tick the box to confirm you checked this unverified item.")
            if b[1].button("Reject", key=f"rj{i['id']}"):
                handover.set_review(i["id"], "rejected", user, new_text)
                st.rerun()
            if b[2].button("Back to pending", key=f"pd{i['id']}"):
                handover.set_review(i["id"], "pending", user, new_text)
                st.rerun()
            hist = db.q("SELECT action, old_text, new_text, changed_by, changed_at FROM item_versions "
                        "WHERE item_id=? ORDER BY id DESC", (i["id"],))
            if hist:
                st.caption("Version history")
                st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)

    with st.expander("Add an item by hand (it still has to pass the Evidence Gate)"):
        srcs = db.q("SELECT id, name FROM sources ORDER BY id")
        sid = st.selectbox("Source", [s["id"] for s in srcs],
                           format_func=lambda n: next(s["name"] for s in srcs if s["id"] == n))
        typ = st.selectbox("Type", config.ITEM_TYPES, format_func=type_label, key="mtype")
        txt = st.text_input("Item text", key="mtext")
        quote = st.text_input("Exact quote from the source", key="mquote")
        owner = st.text_input("Owner (optional)", key="mowner")
        if st.button("Add item"):
            try:
                r = extract.add_manual_item(sid, typ, txt, quote, owner, user)
                if r["status"] == "unverified":
                    st.warning("Added, but the quote was not found in the source, so it is marked Unverified.")
                else:
                    st.success(f"Added as {STATUS_TEXT[r['status']]}.")
            except ValueError as e:
                st.error(str(e))

    st.divider()
    st.subheader("Approve the handover")
    approved = c.get("approved", 0)
    last = handover.current_handover()
    st.write(f"{approved} approved item(s). " +
             (f"Current version: v{last['version']} approved by {last['approved_by']}." if last else "No version approved yet."))
    if role != "Lead":
        st.info("Only a Lead can approve and share a handover.")
    elif st.button("Approve handover and share"):
        try:
            handover.approve_handover(user, role)
            st.success("Handover approved. Switch to another user to see their role-based view.")
            st.rerun()
        except (ValueError, PermissionError) as e:
            st.error(str(e))
    hs = db.q("SELECT version, approved_by, approved_at FROM handovers ORDER BY version DESC")
    if hs:
        st.caption("Handover versions")
        st.dataframe(pd.DataFrame(hs), use_container_width=True, hide_index=True)


# ------------------------------------------------------------------ 4. Handover
def page_handover(user: str, role: str) -> None:
    st.header("4. Handover")
    view = handover.view_for(role)
    if not view:
        st.info("There is no approved handover yet. A Lead must review and approve it first.")
        return
    st.write(f"**Handover v{view['version']}** approved by {view['approved_by']} on {view['approved_at']}. "
             f"You are viewing it as **{user} ({role})**.")
    if view["restricted"]:
        html(ui.notice(f"{view['restricted']} item(s) are restricted for your role. "
                       f"Ask {view['approved_by']} if you need access."))
    handover.log_view(user, view["version"])
    inc = transfer.incoming(user, role)
    if inc:
        with st.expander(f"Responsibilities moving to you ({len(inc)})", expanded=True):
            st.dataframe(pd.DataFrame([{"Item": f"#{t['item_id']} {t['text'][:80]}", "From": t["from_owner"],
                                        "Status": transfer.LABEL[t["status"]]} for t in inc]),
                         use_container_width=True, hide_index=True)
    items, lookup = view["items"], view["all_items"]
    show_metrics(summary_counts(items))
    if view["withheld"]:
        with st.expander(f"{len(view['withheld'])} withheld item(s): who to ask"):
            for w in view["withheld"]:
                st.write(f"- Item #{w['id']} ({type_label(w['type'])}): restricted for your role. "
                         f"Ask **{view['approved_by']}** (the Lead who approved this handover).")

    nmap = notes.by_item(user, role)
    t1, t2, t3, t4 = st.tabs(["Action plan", "Timeline", "Everything we know", "Evidence"])
    with t1:
        cols = st.columns(3)
        for col, block in zip(cols, ui.plan_columns(plan.build_plan(items))):
            with col:
                html(block)
        st.download_button("Download this handover (Markdown)",
                           data=handover.export_markdown(view, plan.build_plan(items), user, role),
                           file_name=f"handover_v{view['version']}_{role.lower()}.md", mime="text/markdown")
        st.markdown("**PDF Handover Report**")
        who_pdf = st.selectbox("Departing member", report.people_for(role) or ["(none)"], key="rep_who")
        if st.button("Generate PDF report", key="rep_go") and who_pdf != "(none)":
            try:
                st.session_state["rep_pdf"] = (who_pdf, report.generate(user, role, who_pdf))
            except (ValueError, PermissionError) as e:
                st.error(str(e))
        got = st.session_state.get("rep_pdf")
        if got and got[0] == who_pdf:
            st.download_button("Download PDF report", data=got[1], file_name=f"handover_report_v{view['version']}_{who_pdf.lower().replace(' ', '_')}.pdf",
                               mime="application/pdf", key="rep_dl")
        rd = readiness.readiness(role)
        if role == "Lead":
            with st.expander(f"Handover readiness: {rd['score']}/100 ({rd['band']})"):
                html(ui.readiness_html(rd))
        st.download_button("One-page summary (open, then print to PDF)",
                           data=handover.one_pager_html(view, plan.build_plan(items), user, role, rd),
                           file_name=f"handover_v{view['version']}_{role.lower()}_one_page.html", mime="text/html")
        st.divider()
        done = handover.acked(user)
        if done:
            st.success(f"You acknowledged this handover on {done['acknowledged_at']}.")
        elif st.button("I acknowledge receipt of this handover"):
            handover.acknowledge(user)
            st.rerun()
    with t2:
        html(ui.timeline_html(handover.timeline(items)))
    with t3:
        for typ in config.ITEM_TYPES:
            group = [i for i in items if i["type"] == typ]
            if not group:
                continue
            st.subheader(type_label(typ))
            for i in group:
                html(ui.item_card(i, lookup, role, notes=nmap.get(i["id"]), viewer=user))
                with st.expander(f"Show proof for #{i['id']}"):
                    src = db.one("SELECT text FROM sources WHERE id=?", (i["source_id"],))
                    html(ui.evidence_html(src["text"], i["quote"]))
                    quick_note(user, role, i["id"])
    with t4:
        rows = [{"#": i["id"], "Item": i["text"], "Quote (proof)": i["quote"], "Source": i["source_name"],
                 "Date": i["source_date"] or "-", "Evidence": STATUS_TEXT[i["verify_status"]]} for i in items]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ------------------------------------------------------------------ 5. Transfer responsibilities
def _names() -> list:
    return [u["name"] for u in db.q("SELECT name FROM users ORDER BY id")]


def page_transfer(user: str, role: str) -> None:
    st.header("5. Transfer responsibilities")
    st.write("Pick the person who is leaving, give every responsibility they own a new owner, and a Lead approves each "
             "transfer before it is finalized. Nothing changes until a transfer is completed, and every step is kept in the history.")
    people = transfer.owners()
    if not people:
        st.info("No owners found yet. Import sources and run extraction first.")
        return
    who = st.selectbox("Who is leaving?", people, key="tr_who")
    pr = transfer.progress(who)
    m = st.columns(5)
    m[0].metric("Responsibilities", pr["total"])
    m[1].metric("Not started", pr["not_started"])
    m[2].metric("Waiting approval", pr["awaiting_approval"])
    m[3].metric("Waiting new owner", pr["awaiting_new_owner"])
    m[4].metric("Completed", pr["completed"])
    st.progress(pr["percent"] / 100, text=f"{pr['percent']}% of {who}'s responsibilities transferred")
    if pr["total"] and pr["percent"] == 100:
        st.success(f"Everything {who} owned has a new owner. Approve a new handover version so readers see it.")
    elif pr["completed"]:
        st.caption("Completed transfers change the item owner. Approve a new handover version (screen 3) to share them.")

    names = [n for n in _names() if n.lower() != who.lower()]
    t_res, t_pend, t_done, t_hist = st.tabs(["Responsibilities", "Pending", "Completed", "History"])

    with t_res:
        resp = transfer.responsibilities(who)
        if not resp:
            st.caption("Nothing left that is owned by this person.")
        free = [r for r in resp if not r["transfer"]]
        if free:
            with st.expander(f"Assign all {len(free)} unassigned items to one person"):
                bulk = st.selectbox("New owner", names, key="tr_bulk")
                if st.button("Propose all", key="tr_bulk_go"):
                    n = 0
                    for r in free:
                        try:
                            transfer.propose(user, role, r["id"], bulk, "Bulk assignment")
                            n += 1
                        except (ValueError, PermissionError) as e:
                            st.error(f"#{r['id']}: {e}")
                    flash(f"{n} transfer(s) proposed")
                    st.rerun()
        for r in resp:
            with st.container(border=True):
                st.markdown(f"**#{r['id']} {type_label(r['type'])}**: {r['text']}  \n"
                            f"{BADGE[r['verify_status']]} | source: `{r['source_name']}` | {r['item_date'] or 'undated'}")
                t = r["transfer"]
                if t:
                    st.info(f"{transfer.LABEL[t['status']]}: {t['from_owner']} to **{t['to_owner']}** "
                            f"(proposed by {t['proposed_by']})")
                else:
                    c1, c2 = st.columns([2, 3])
                    to = c1.selectbox("New owner", [*names, "Someone else..."], key=f"tr_to{r['id']}")
                    other = c1.text_input("Name", key=f"tr_ot{r['id']}") if to == "Someone else..." else ""
                    why = c2.text_input("Reason or note (optional)", key=f"tr_why{r['id']}")
                    if st.button("Propose transfer", key=f"tr_go{r['id']}"):
                        try:
                            transfer.propose(user, role, r["id"], other if to == "Someone else..." else to, why)
                            flash(f"Transfer proposed for item #{r['id']}")
                            st.rerun()
                        except (ValueError, PermissionError) as e:
                            st.error(str(e))

    with t_pend:
        pend = transfer.list_transfers(("proposed", "approved"), who)
        if not pend:
            st.caption("No transfers are waiting.")
        for t in pend:
            with st.container(border=True):
                st.markdown(f"**#{t['item_id']}** {t['text']}  \n{t['from_owner']} to **{t['to_owner']}**: "
                            f"{transfer.LABEL[t['status']]} (proposed by {t['proposed_by']}, {t['proposed_at']})")
                if t["reason"]:
                    st.caption(f"Reason: {t['reason']}")
                b = st.columns(3)
                if t["status"] == "proposed":
                    if b[0].button("Approve", key=f"ta{t['id']}"):
                        try:
                            transfer.decide(user, role, t["id"], True)
                            st.rerun()
                        except (ValueError, PermissionError) as e:
                            st.error(str(e))
                    if b[1].button("Reject", key=f"tj{t['id']}"):
                        try:
                            transfer.decide(user, role, t["id"], False)
                            st.rerun()
                        except (ValueError, PermissionError) as e:
                            st.error(str(e))
                else:
                    if b[0].button("Mark as completed", key=f"tc{t['id']}"):
                        try:
                            transfer.complete(user, role, t["id"])
                            flash(f"Item #{t['item_id']} now belongs to {t['to_owner']}")
                            st.rerun()
                        except (ValueError, PermissionError) as e:
                            st.error(str(e))
                if b[2].button("Cancel transfer", key=f"tx{t['id']}"):
                    try:
                        transfer.cancel(user, role, t["id"])
                        st.rerun()
                    except (ValueError, PermissionError) as e:
                        st.error(str(e))
        waiting = [t for t in pend if t["status"] == "proposed"]
        if len(waiting) > 1 and st.button(f"Approve all {len(waiting)} waiting", key="tr_appall"):
            for t in waiting:
                try:
                    transfer.decide(user, role, t["id"], True, "Bulk approval")
                except (ValueError, PermissionError) as e:
                    st.error(str(e))
                    break
            st.rerun()

    with t_done:
        rows = transfer.list_transfers(("completed",), who)
        if rows:
            st.dataframe(pd.DataFrame([{"Item": f"#{t['item_id']} {t['text'][:70]}", "From": t["from_owner"],
                                        "To": t["to_owner"], "Approved by": t["decided_by"],
                                        "Completed by": t["completed_by"], "Completed at": t["completed_at"]}
                                       for t in rows]), use_container_width=True, hide_index=True)
        else:
            st.caption("No completed transfers yet.")

    with t_hist:
        allt = transfer.list_transfers(None, who)
        if not allt:
            st.caption("No history yet.")
        for t in allt:
            with st.expander(f"#{t['item_id']} {t['from_owner']} to {t['to_owner']}: {transfer.LABEL[t['status']]}"):
                st.dataframe(pd.DataFrame(transfer.history(t["id"])), use_container_width=True, hide_index=True)


# ------------------------------------------------------------------ 6. Departure checklist
def page_checklist(user: str, role: str) -> None:
    st.header("6. Departure checklist")
    st.write("Everything a leaving person still has to close: responsibility transfers, pending tasks, important decisions, "
             "technical documentation and unresolved dependencies. The list is built from your real items and transfers, "
             "so it is never invented. Tick lines as they are done and watch the progress.")
    names = checklist.people()
    if not names:
        st.info("No owners found yet. Import sources and run extraction first.")
        return
    start = names.index(user) if (role != "Lead" and user in names) else 0
    who = st.selectbox("Who is leaving?", names, index=start, key="dc_who")
    data = checklist.build(who, role)
    editable = checklist.can_edit(user, role, who)

    m = st.columns(4)
    m[0].metric("Done", f"{data['done']} of {data['total']}")
    m[1].metric("Left", data["left"])
    m[2].metric("Need attention", data["urgent"])
    m[3].metric("Restricted", data["restricted"])
    st.progress(data["percent"] / 100, text=f"{data['percent']}% of {who}'s checklist done")
    if data["restricted"]:
        st.caption(f"{data['restricted']} restricted item(s) are left out of these numbers. A Lead can see them.")
    if not data["total"]:
        st.info(f"Nothing found for {who} yet. Add a line below, or import more sources.")
    elif data["ready"]:
        st.success(f"Everything on {who}'s checklist is done.")
    if not editable:
        st.caption(f"You can view this checklist. Only a Lead or {who} can tick or add lines.")

    if data["attention"]:
        st.subheader("What still needs attention")
        for e in data["attention"][:8]:
            st.markdown(f"- **{checklist.TITLE[e['section']]}**: {e['label'][:110]}  \n  {'; '.join(e['reasons'])}")
        if len(data["attention"]) > 8:
            st.caption(f"{len(data['attention']) - 8} more open line(s) are in the sections below.")

    for sec in data["sections"]:
        label = f"{sec['title']} ({sec['done']}/{sec['total']})"
        with st.expander(label, expanded=sec["done"] < sec["total"]):
            if not sec["entries"]:
                st.caption("Nothing found for this person in this section.")
            for e in sec["entries"]:
                if e["restricted"]:
                    st.caption(f"{e['label']}: {e['detail']}")
                    continue
                key = f"dc_{who}_{sec['key']}_{e['ref']}"
                locked = e["locked"] or e["auto"] or not editable
                val = st.checkbox(e["label"][:140], value=e["done"], key=key, disabled=locked)
                if e["done"]:
                    who_done = f"Done by {e['done_by']} on {(e['done_at'] or '')[:10]}." if e["done_by"] else "Done."
                    st.caption(f"{who_done} {e['detail']}")
                else:
                    st.caption(f"{e['detail']}  \nNeeds: {'; '.join(e['reasons'])}")
                if e["locked"] and not e["done"]:
                    st.caption(e["locked_reason"])
                if e["note"]:
                    st.caption(f"Note: {e['note']}")
                if val != e["done"] and not locked:
                    try:
                        checklist.set_done(user, role, who, sec["key"], e["ref"], val)
                    except (ValueError, PermissionError) as err:
                        st.error(str(err))
                    else:
                        flash(("Ticked: " if val else "Unticked: ") + e["label"][:60])
                        st.rerun()
                if e["custom"] and editable and st.button("Remove this line", key=f"dc_rm_{e['ref']}"):
                    checklist.delete_custom(user, role, who, e["ref"])
                    st.rerun()

    if editable:
        with st.expander("Add a line or a note"):
            sec_key = st.selectbox("Section", [k for k, _ in checklist.SECTIONS], format_func=lambda k: checklist.TITLE[k], key="dc_sec")
            text = st.text_input("New checklist line (for example: share the runbook link)", key="dc_new")
            if st.button("Add line", key="dc_add"):
                try:
                    checklist.add_custom(user, role, who, sec_key, text)
                    flash("Line added")
                    st.rerun()
                except (ValueError, PermissionError) as err:
                    st.error(str(err))
            live = [(s["key"], e) for s in data["sections"] for e in s["entries"] if not e["restricted"]]
            if live:
                pick = st.selectbox("Add a note to", range(len(live)), format_func=lambda n: live[n][1]["label"][:80], key="dc_pick")
                note = st.text_input("Note (a link, a name, where it lives)", key="dc_note")
                if st.button("Save note", key="dc_savenote"):
                    try:
                        checklist.set_note(user, role, who, live[pick][0], live[pick][1]["ref"], note)
                        flash("Note saved")
                        st.rerun()
                    except (ValueError, PermissionError) as err:
                        st.error(str(err))
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", who).strip("-") or "person"
    st.download_button("Download checklist (.md)", data=checklist.export_markdown(data),
                       file_name=f"departure-checklist-{safe}.md", mime="text/markdown", key="dc_dl")


# ------------------------------------------------------------------ 7. Audit log
def page_audit() -> None:
    st.header("7. Audit log")
    rows = db.q("SELECT at AS time, user_name AS user, action, target, detail FROM audit_log ORDER BY id DESC LIMIT 500")
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("Nothing recorded yet.")
    acks = db.q("SELECT a.user_name AS user, h.version AS handover_version, a.acknowledged_at AS time "
                "FROM acks a JOIN handovers h ON h.id=a.handover_id ORDER BY a.id DESC")
    st.subheader("Who viewed the handover")
    vw = handover.viewers()
    if vw:
        st.dataframe(pd.DataFrame(vw), use_container_width=True, hide_index=True)
    else:
        st.caption("No one has opened the handover yet.")
    st.subheader("Acknowledgements")
    if acks:
        st.dataframe(pd.DataFrame(acks), use_container_width=True, hide_index=True)
    else:
        st.caption("No one has acknowledged a handover yet.")


# ------------------------------------------------------------------ notes
def flash(msg: str) -> None:
    """Show a short message on the next screen (a rerun would otherwise wipe it)."""
    st.session_state["flash"] = msg


def quick_note(user: str, role: str, item_id: int) -> None:
    with st.form(f"qf{item_id}", clear_on_submit=True):
        text = st.text_input("Quick note on this item", key=f"qt{item_id}", placeholder="Only you see it until you share it")
        if st.form_submit_button(f"Stick a note on #{item_id}"):
            try:
                notes.create(user, role, text, "todo", "auto", "me", item_id)
                flash(f"Note stuck on item #{item_id}")
                st.rerun()
            except ValueError as e:
                st.error(str(e))


def _item_label(i: dict) -> str:
    return f"#{i['id']} {type_label(i['type'])}: {i['text'][:48]}"


def new_note_form(user: str, role: str) -> None:
    items = notes.linkable_items(role)
    by_id = {i["id"]: i for i in items}
    with st.form("new_note", clear_on_submit=True):
        body = st.text_area("Write a note", placeholder="Ask Karan for the Razorpay sandbox keys", max_chars=notes.MAX_LEN)
        c1, c2 = st.columns(2)
        kind = c1.selectbox("Note type", list(notes.KINDS), format_func=lambda k: notes.KINDS[k])
        vis = c2.selectbox("Who can see this note", list(notes.VIS), format_func=lambda v: notes.VIS[v])
        color = st.radio("Sticky colour", ["auto", *notes.COLORS], format_func=str.capitalize, horizontal=True)
        link = st.selectbox("Link to an item", [None, *by_id], format_func=lambda n: "Not linked" if n is None else _item_label(by_id[n]))
        remind = st.text_input("Remind me (optional)", placeholder="tomorrow, in 3 days, friday, 12 Nov")
        if st.form_submit_button("Save note"):
            try:
                notes.create(user, role, body, kind, color, vis, link, remind)
                flash("Note saved" + (" and shared" if vis != "me" else ""))
                st.rerun()
            except ValueError as e:
                st.error(str(e))


def promote_form(n: dict, user: str, role: str) -> None:
    sources = [s for s in db.q("SELECT id, name, visibility FROM sources ORDER BY id") if roles.can_see(role, s["visibility"])]
    if not sources:
        st.caption("Add sources first. A promoted note needs proof from a source.")
        return
    sugg = notes.suggest_quotes(n["body"], role)
    labels = [f"{s['source_name']}: {s['line'][:70]} ({s['score']}% match)" for s in sugg] + ["I will type my own quote"]
    pick = st.selectbox("Suggested proof", list(range(len(labels))), format_func=lambda k: labels[k], key=f"sg{n['id']}")
    chosen = sugg[pick] if pick < len(sugg) else None
    ids = [s["id"] for s in sources]
    names = {s["id"]: s["name"] for s in sources}
    sid = st.selectbox("Proof is in this source", ids, index=ids.index(chosen["source_id"]) if chosen else 0,
                       format_func=lambda k: names[k], key=f"ps{n['id']}_{pick}")
    quote = st.text_input("Exact quote from the source", value=chosen["line"] if chosen else "", key=f"pq{n['id']}_{pick}")
    types = list(config.ITEM_TYPES)
    typ = st.selectbox("Becomes this kind of item", types, index=types.index(notes.KIND_TO_TYPE[n["kind"]]),
                       format_func=type_label, key=f"pt{n['id']}")
    if st.button("Promote to item", key=f"pr{n['id']}"):
        try:
            iid = notes.promote(n["id"], user, role, sid, typ, quote)
            flash(f"Promoted to item #{iid}. It still needs review before it joins the handover.")
            st.rerun()
        except (ValueError, PermissionError) as e:
            st.error(str(e))


def note_actions(n: dict, user: str, role: str) -> None:
    nid = n["id"]
    if n["author"] == user:
        b = st.columns(2)
        if b[0].button("Unpin" if n["pinned"] else "Pin", key=f"pin{nid}"):
            notes.set_pin(nid, user, not n["pinned"])
            st.rerun()
        if b[1].button("Reopen" if n["done"] else "Done", key=f"dn{nid}"):
            notes.set_done(nid, user, not n["done"])
            st.rerun()
        if not n["promoted_item_id"]:
            with st.expander("Edit or delete"):
                txt = st.text_area("Note text", value=n["body"], key=f"et{nid}", max_chars=notes.MAX_LEN)
                vis = st.selectbox("Visible to", list(notes.VIS), index=list(notes.VIS).index(n["visibility"]),
                                   format_func=lambda v: notes.VIS[v], key=f"ev{nid}")
                if st.button("Save changes", key=f"es{nid}"):
                    try:
                        notes.edit(nid, user, txt, vis)
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                sure = st.checkbox("Yes, delete this note", key=f"ec{nid}")
                if st.button("Delete note", key=f"del{nid}") and sure:
                    notes.delete(nid, user)
                    st.rerun()
    if role == "Lead" and not n["promoted_item_id"]:
        with st.expander("Promote to a handover item (needs proof)"):
            promote_form(n, user, role)


def notes_page(user: str, role: str) -> None:
    """My notes as a full screen of its own: a composer on the left, a sticky-note board on the right."""
    top = st.columns([5, 1.4])
    with top[0]:
        html("<div class='pn-title'>My notes</div>")
        html("<div class='pn-sub'>Your own questions, to-dos and hunches. Private until you choose to share them.</div>")
    with top[1]:
        if st.button("Back to the app", key="notes_back"):
            st.session_state["notes_open"] = False
            st.rerun()
    s = notes.stats(user, role)
    m = st.columns(4)
    m[0].metric("Open", s["open"])
    m[1].metric("Due", s["due"])
    m[2].metric("Shared with you", s["shared"])
    m[3].metric("Done", s["done"])

    left, right = st.columns([1, 2.2])
    with left:
        html("<div class='pn-h'>New note</div>")
        new_note_form(user, role)
        html(ui.NOTES_RULE)
        st.download_button("Download my notes (Markdown)", data=notes.export_markdown(user, role),
                           file_name="my_notes.md", mime="text/markdown")
    with right:
        labels = {"all": "All", "mine": "Mine", "shared": "Shared", "pinned": "Pinned", "due": "Due"}
        scope = st.radio("Show notes", list(notes.SCOPES), format_func=lambda k: labels[k], horizontal=True, key="notes_scope")
        f1, f2, f3 = st.columns([2.2, 1.4, 1.2])
        query = f1.text_input("Search notes", key="notes_q", placeholder="Search by word, person or type")
        kind = f2.selectbox("Note type filter", ["all", *notes.KINDS], format_func=lambda k: "All types" if k == "all" else notes.KINDS[k],
                            key="notes_kind")
        hide_done = f3.checkbox("Hide done", key="notes_hide_done")
        rows = notes.list_for(user, role, scope, query, kind=kind, show_done=not hide_done)
        st.caption(f"{len(rows)} note(s)")
        if not rows:
            html(ui.notes_empty(scope != "all" or bool(query) or kind != "all"))
        board = st.columns(2)
        for pos, n in enumerate(rows):
            with board[pos % 2]:
                html(ui.note_card(n, user, notes.signals(n)))
                note_actions(n, user, role)


# ------------------------------------------------------------------ appearance
ACCENT_LABEL = {"theme": "Theme's own", "teal": "Teal", "indigo": "Indigo", "coral": "Coral", "green": "Green", "amber": "Amber"}
WRITING_LABEL = {"theme": "Theme's own", "handwritten": "Handwritten", "classic": "Classic", "simple": "Simple"}
SIZE_LABEL = {"s": "Small", "m": "Medium", "l": "Large"}
DENSITY_LABEL = {"cozy": "Cozy", "compact": "Compact"}
ITEMS_LABEL = {"theme": "Theme's own", "sticky": "Sticky notes", "flat": "Flat cards"}


def _choose(user: str, prefs: dict, key: str, label: str, names: dict) -> None:
    opts = list(names)
    v = st.radio(label, opts, index=opts.index(prefs[key]), format_func=lambda o: names[o], horizontal=True)
    if v != prefs[key]:
        themes.set_pref(user, key, v)
        st.rerun()


def _toggle(user: str, prefs: dict, key: str, label: str) -> None:
    v = st.checkbox(label, value=prefs[key] == "1")
    if v != (prefs[key] == "1"):
        themes.set_pref(user, key, v)
        st.rerun()


def page_appearance(user: str, prefs: dict) -> None:
    st.header("Choose your look")
    st.caption(f"{len(themes.THEME_ORDER)} themes. Switch any time from the sidebar. Your choices are remembered for your account.")
    html(themes.gallery_css())
    keys = themes.THEME_ORDER
    for start in range(0, len(keys), 4):
        for col, key in zip(st.columns(4), keys[start:start + 4]):
            with col:
                html(ui.theme_preview(key, key == prefs["theme"]))
                if st.button("Use " + themes.THEMES[key]["name"], key=f"use_{key}", disabled=key == prefs["theme"]):
                    themes.set_pref(user, "theme", key)
                    st.rerun()
    st.divider()
    st.subheader("Make it yours")
    left, right = st.columns(2)
    with left:
        html(ui.swatches())
        _choose(user, prefs, "accent", "Accent colour", ACCENT_LABEL)
        _choose(user, prefs, "writing", "Writing style", WRITING_LABEL)
        _choose(user, prefs, "items", "Items look like", ITEMS_LABEL)
    with right:
        _choose(user, prefs, "size", "Text size", SIZE_LABEL)
        _choose(user, prefs, "density", "Density", DENSITY_LABEL)
        _toggle(user, prefs, "contrast", "High contrast text and borders")
        _toggle(user, prefs, "motion", "Reduce tilt and motion")
        _toggle(user, prefs, "dots", "Show the paper pattern in the background")
        _toggle(user, prefs, "splash", "Play the start-up animation when the app opens (once per visit)")
        _toggle(user, prefs, "auto_night", "Switch to Midnight automatically from 7 pm to 6 am")
    b = st.columns(3)
    if b[0].button("Surprise me", key="look_surprise"):
        themes.surprise(user)
        st.rerun()
    if b[1].button("Reset to default", key="look_reset"):
        themes.reset_prefs(user)
        st.rerun()
    if b[2].button("Done", key="look_done"):
        st.session_state["look_open"] = False
        st.rerun()


# ------------------------------------------------------------------ main
def route(page: str, user: str, role: str) -> None:
    if page.startswith("1"):
        page_connect(user)
    elif page.startswith("2"):
        page_reconstruct(user, role)
    elif page.startswith("3"):
        page_review(user, role)
    elif page.startswith("4"):
        page_handover(user, role)
    elif page.startswith("5"):
        page_transfer(user, role)
    elif page.startswith("6"):
        page_checklist(user, role)
    else:
        page_audit()


def main() -> None:
    setup_workspace()
    users = db.q("SELECT name, role FROM users ORDER BY id")
    names = [u["name"] for u in users]
    st.sidebar.markdown(ui.sidebar_logo(), unsafe_allow_html=True)
    user = st.sidebar.selectbox("Signed in as (demo login)", names, key="user_name")
    role = next(u["role"] for u in users if u["name"] == user)
    prefs = themes.get_prefs(user)
    html(ui.CSS)
    html(themes.css_for(prefs))
    if prefs["splash"] == "1" and prefs["motion"] == "0" and not st.session_state.get("splash_shown"):
        st.session_state["splash_shown"] = True   # once per visit: later clicks never replay it
        html(splash.markup())
    st.sidebar.markdown(ui.name_tag(user, role), unsafe_allow_html=True)
    if st.session_state.get("last_user") != user:
        db.log(user, "switch_user", role)
        st.session_state["last_user"] = user

    notes_open = bool(st.session_state.get("notes_open"))
    look_open = bool(st.session_state.get("look_open"))
    if st.sidebar.button("Back to the app" if notes_open else f"My notes ({notes.count_open(user, role)})", key="btn_notes"):
        st.session_state["notes_open"] = not notes_open
        st.session_state["look_open"] = False
        st.rerun()
    if st.sidebar.button("Back to the app" if look_open else "Appearance", key="btn_look"):
        st.session_state["look_open"] = not look_open
        st.session_state["notes_open"] = False
        st.rerun()
    keys = themes.THEME_ORDER
    quick = st.sidebar.selectbox("Quick look", keys, index=keys.index(prefs["theme"]), format_func=lambda k: themes.THEMES[k]["name"])
    if quick != prefs["theme"]:
        themes.set_pref(user, "theme", quick)
        st.rerun()

    pages = PAGES_LEAD if role == "Lead" else PAGES_OTHER
    page = st.sidebar.radio("Workflow", pages, key=f"nav_{role}")
    st.sidebar.divider()
    st.sidebar.caption(f"Handover status: **{readiness.status_flow()}**  \n" + " > ".join(readiness.FLOW))
    st.sidebar.caption("Restricted items are removed before any view or plan is built for you.")
    if PUBLIC:
        st.sidebar.info("Your workspace is private to this browser session and deleted after 24 hours. "
                        "Use only made-up or permitted data.")

    msg = st.session_state.pop("flash", None)
    if msg:
        st.toast(msg)
    html(ui.hero("HandoverTrail", SUBTITLE, user, role))
    if look_open:
        page_appearance(user, prefs)
    elif notes_open:
        notes_page(user, role)
    else:
        done, current = progress_state()
        html(ui.stepper(done, current))
        late = notes.due(user, role)
        if late:
            over = sum(1 for n in late if n["remind_on"] < notes.today().isoformat())
            html(ui.reminder_banner(over, len(late) - over))
        route(page, user, role)
    html(ui.footer())


main()
