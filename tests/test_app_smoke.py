"""Smoke test of the Streamlit screens using a stand-in for streamlit.

This checks OUR code paths end to end (no crashes, correct data shown to each role).
It does not replace opening the real app in a browser once.
"""
import importlib
import os
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class Rerun(Exception):
    pass


class Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __getattr__(self, name):
        return getattr(FAKE, name)


class Fake(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit")
        self.reset()

    def reset(self):
        self.press, self.select, self.text, self.check, self.files, self.out = set(), {}, {}, {}, [], []
        self.session = {}
        self.edit_fn = None

    class _Cfg:
        def __getattr__(self, name):
            return lambda *a, **kw: None

    column_config = _Cfg()

    def data_editor(self, df, **kw):
        self.out.append(df.to_csv())
        return self.edit_fn(df.copy()) if self.edit_fn else df

    @property
    def session_state(self):
        return self.session

    @property
    def sidebar(self):
        return self

    def _rec(self, *a, **kw):
        for x in a:
            if isinstance(x, str):
                self.out.append(x)

    def button(self, label, key=None, **kw):
        return any(label.startswith(p) for p in self.press) or (key in self.press)

    def selectbox(self, label, options, index=0, format_func=None, key=None, **kw):
        options = list(options)
        if format_func:
            for o in options:
                self.out.append(str(format_func(o)))
        v = self.select.get(label)
        return v if v is not None else (options[index] if options else None)

    def radio(self, label, options, **kw):
        options = list(options)
        return self.select.get(label) or options[0]

    def multiselect(self, label, options, default=None, **kw):
        return list(default) if default is not None else []

    def text_input(self, label, value="", **kw):
        return self.text.get(label, value)

    def text_area(self, label, value="", **kw):
        return self.text.get(label, value)

    def checkbox(self, label, value=False, key=None, **kw):
        return self.check.get(label, self.check.get(key, value))

    def file_uploader(self, *a, **kw):
        return self.files

    def columns(self, spec, **kw):
        n = spec if isinstance(spec, int) else len(spec)
        return [Ctx() for _ in range(n)]

    def tabs(self, labels):
        return [Ctx() for _ in labels]

    def expander(self, label="", **kw):
        self.out.append(str(label))
        return Ctx()

    def spinner(self, *a, **kw):
        return Ctx()

    def form(self, *a, **kw):
        return Ctx()

    def form_submit_button(self, label, key=None, **kw):
        return self.button(label, key=key)

    def download_button(self, label, *a, **kw):
        self.out.append(str(label))
        return False

    def dataframe(self, df, **kw):
        self.out.append(df.to_csv())

    def rerun(self):
        raise Rerun()

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return self._rec


FAKE = Fake()
sys.modules["streamlit"] = FAKE


class Upload:
    def __init__(self, name, data):
        self.name, self._d = name, data

    def getvalue(self):
        return self._d


class TestApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core import config
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        config.DB_PATH = path
        cls.app = importlib.import_module("app")

    def run_as(self, user, page=None, press=(), **state):
        FAKE.out.clear()
        FAKE.press = set(press)
        FAKE.select = {"Signed in as (demo login)": user}
        FAKE.select.update(state.get("select", {}))
        if page:
            FAKE.select["Workflow"] = page
        FAKE.text = state.get("text", {})
        FAKE.check = state.get("check", {})
        FAKE.files = state.get("files", [])
        try:
            self.app.main()
        except Rerun:
            pass
        return "\n".join(FAKE.out)

    def test_full_journey(self):
        from core import db, handover
        # Connect
        out = self.run_as("Riya", "1. Connect")
        self.assertIn("No sources yet", out)
        self.run_as("Riya", "1. Connect", press=["Load the demo project"])
        out = self.run_as("Riya", "1. Connect")
        self.assertIn("sponsor_note.txt", out)
        self.assertGreaterEqual(db.q("SELECT COUNT(*) AS n FROM redactions")[0]["n"], 5)
        self.assertNotIn("sk_test_FAKE12345678", " ".join(r["text"] for r in db.q("SELECT text FROM sources")))
        # Upload path with a bad file and a good file
        self.run_as("Riya", "1. Connect", press=["Import files"],
                    files=[Upload("bad.exe", b"x"), Upload("extra_notes.txt", b"Date: 2026-03-20\nWe decided to add dark mode.\n")])
        self.assertTrue(db.one("SELECT 1 AS x FROM sources WHERE name='extra_notes.txt'"))
        # Reconstruct
        out = self.run_as("Riya", "2. Reconstruct and verify", press=["Run extraction"])
        self.assertGreater(db.q("SELECT COUNT(*) AS n FROM items")[0]["n"], 25)
        out = self.run_as("Riya", "2. Reconstruct and verify")
        self.assertIn("Conflicts with item", out)
        self.assertIn("Gap: no owner found", out)
        # Review: bulk approve, manual fake item, approve handover
        self.run_as("Riya", "3. Review and approve", press=["Approve all verified"])
        out = self.run_as("Riya", "3. Review and approve", press=["Add item"],
                          text={"Item text": "Use MongoDB", "Exact quote from the source": "We will use MongoDB for everything"})
        self.assertTrue(db.one("SELECT 1 AS x FROM items WHERE verify_status='unverified' AND extractor='manual'"))
        for it in handover.list_items():
            if it["review_status"] == "pending":
                handover.set_review(it["id"], "approved", "Riya")
        # Core and Intern cannot approve
        out = self.run_as("Aman", "4. Handover")
        self.assertIn("no approved handover yet", out)
        out = self.run_as("Riya", "3. Review and approve", press=["Approve handover and share"])
        self.assertTrue(handover.current_handover())
        # Role views
        intern = self.run_as("Aman")
        self.assertIn("restricted for your role", intern)
        self.assertNotIn("10000 more rupees", intern)
        self.assertNotIn("blue theme", intern)
        self.assertIn("Day 1", intern)
        core = self.run_as("Karan")
        self.assertIn("blue theme", core)
        self.assertNotIn("10000 more rupees", core)
        lead = self.run_as("Riya", "4. Handover")
        self.assertIn("10000 more rupees", lead)
        # Acknowledge, audit
        self.run_as("Aman", press=["I acknowledge receipt"])
        self.assertIsNotNone(handover.acked("Aman"))
        out = self.run_as("Riya", "7. Audit log")
        self.assertIn("acknowledge", out)
        self.assertIn("approve_handover", out)
        # Reset
        self.run_as("Riya", "1. Connect", press=["Reset everything"], check={"I understand this deletes all sources, items, handovers and the audit log": True})
        self.assertEqual(db.q("SELECT COUNT(*) AS n FROM sources")[0]["n"], 0)


    def test_paste_notes_preview_edit_approve_reject_import(self):
        from core import db
        label = "Paste meeting notes, a chat export or anything written (secrets are masked before anything is read or stored)"
        notes = ("Action items:\n- Karan to send the invoice by Friday\n- Renew the hosting plan\n\n"
                 "Open questions:\n- Who owns the payments webhook?\n\nWe decided to move the database to PostgreSQL.\n")
        FAKE.session.pop("paste_draft", None)
        # 1. analyze: shows nothing in the database yet
        self.run_as("Riya", "1. Connect", press=["p_read"], text={label: notes})
        self.assertIn("paste_draft", FAKE.session)
        self.assertEqual(db.q("SELECT COUNT(*) AS n FROM sources WHERE type='pasted_notes'")[0]["n"], 0)
        # 2. the editable preview is drawn with the found rows
        out = self.run_as("Riya", "1. Connect")
        self.assertIn("Nothing is saved yet", out)
        self.assertIn("suggestion, not verified", out)
        self.assertIn("send the invoice", out)
        self.assertIn("Missing owner", out)

        # 3. the user edits one row, rejects another, then imports
        def edit(df):
            i = df.index[df["Item"].str.contains("Renew")][0]
            df.loc[i, "Owner / person"] = "Aman"
            df.loc[i, "Import?"] = "Approve"
            j = df.index[df["Item"].str.contains("PostgreSQL")][0]
            df.loc[j, "Import?"] = "Reject"
            return df
        FAKE.edit_fn = edit
        try:
            self.run_as("Riya", "1. Connect", press=["p_import"])
        finally:
            FAKE.edit_fn = None
        self.assertNotIn("paste_draft", FAKE.session)
        items = db.q("SELECT * FROM items WHERE extractor='paste-preview'")
        self.assertTrue(any(i["owner"] == "Aman" and "Renew" in i["quote"] for i in items))
        self.assertFalse(any("PostgreSQL" in i["quote"] for i in items))
        out = self.run_as("Riya", "1. Connect")
        self.assertIn("Imported", out)
        self.assertEqual(db.one("SELECT extracted FROM sources WHERE type='pasted_notes'")["extracted"], 1)
        # discard leaves nothing behind
        before = db.q("SELECT COUNT(*) AS n FROM sources")[0]["n"]
        self.run_as("Riya", "1. Connect", press=["p_read"], text={label: notes})
        self.run_as("Riya", "1. Connect", press=["p_discard"])
        self.assertNotIn("paste_draft", FAKE.session)
        self.assertEqual(db.q("SELECT COUNT(*) AS n FROM sources")[0]["n"], before)
        self.run_as("Riya", "1. Connect", press=["Reset everything"], check={"I understand this deletes all sources, items, handovers and the audit log": True})

    def test_departure_checklist_screen(self):
        from core import checklist, db
        self.run_as("Riya", "1. Connect", press=["Load the demo project"])
        self.run_as("Riya", "2. Reconstruct and verify", press=["Run extraction"])
        out = self.run_as("Riya", "6. Departure checklist", select={"Who is leaving?": "Karan"})
        self.assertIn("6. Departure checklist", out)
        self.assertIn("What still needs attention", out)
        self.assertIn("Responsibility transfers (0/1)", out)
        self.assertIn("Technical documentation", out)
        self.assertIn("Unresolved dependencies", out)
        self.assertIn("Download checklist (.md)", out)
        task = checklist.build("Karan", "Lead")["sections"][1]["entries"][0]
        key = f"dc_Karan_tasks_{task['ref']}"
        # a Lead ticks a line through the screen
        self.run_as("Riya", "6. Departure checklist", select={"Who is leaving?": "Karan"}, check={key: True})
        self.assertEqual(db.q("SELECT COUNT(*) AS n FROM checklist WHERE done=1")[0]["n"], 1)
        out = self.run_as("Riya", "6. Departure checklist", select={"Who is leaving?": "Karan"})
        self.assertIn("Done by Riya", out)
        # an intern can look, but the screen never changes anything for them
        out = self.run_as("Aman", "6. Departure checklist", select={"Who is leaving?": "Meera"})
        self.assertIn("You can view this checklist", out)
        self.run_as("Aman", "6. Departure checklist", select={"Who is leaving?": "Karan"}, check={f"dc_Karan_tasks_{checklist.build('Karan','Lead')['sections'][1]['entries'][1]['ref']}": True})
        self.assertEqual(db.q("SELECT COUNT(*) AS n FROM checklist WHERE done=1")[0]["n"], 1)
        # the leaver can add a line to their own list
        self.run_as("Karan", "6. Departure checklist", select={"Who is leaving?": "Karan"}, press=["dc_add"],
                    text={"New checklist line (for example: share the runbook link)": "Hand over the sandbox keys"})
        self.assertTrue(db.q("SELECT 1 FROM checklist WHERE custom=1 AND label='Hand over the sandbox keys'"))
        self.run_as("Riya", "1. Connect", press=["Reset everything"], check={"I understand this deletes all sources, items, handovers and the audit log": True})

    def test_startup_screen_shows_once_and_respects_preferences(self):
        from core import themes
        FAKE.session.pop("splash_shown", None)
        out = self.run_as("Riya", "1. Connect")
        self.assertIn("sp-letters", out)                      # first visit: the animation is drawn
        self.assertTrue(FAKE.session.get("splash_shown"))
        out = self.run_as("Riya", "1. Connect")
        self.assertNotIn("sp-letters", out)                   # later reruns never replay it
        FAKE.session.pop("splash_shown", None)
        themes.set_pref("Riya", "motion", True)
        self.assertNotIn("sp-letters", self.run_as("Riya", "1. Connect"))   # reduce motion = no animation
        themes.set_pref("Riya", "motion", False)
        themes.set_pref("Riya", "splash", False)
        self.assertNotIn("sp-letters", self.run_as("Riya", "1. Connect"))   # switched off in Appearance
        themes.reset_prefs("Riya")
        FAKE.session["splash_shown"] = True

    def test_notes_and_appearance_screens(self):
        from core import db, handover, notes, themes
        self.run_as("Riya", "1. Connect", press=["Load the demo project"])
        self.run_as("Riya", "2. Reconstruct and verify", press=["Run extraction"])
        self.run_as("Riya", "3. Review and approve", press=["Approve all verified"])
        for it in handover.list_items():
            if it["review_status"] == "pending" and it["verify_status"] != "unverified":
                handover.set_review(it["id"], "approved", "Riya")
        self.run_as("Riya", "3. Review and approve", press=["Approve handover and share"])
        item = next(i for i in handover.list_items() if i["visibility"] == "Everyone" and i["review_status"] == "approved")
        # open the panel, write a note through the form
        FAKE.session["notes_open"] = True
        out = self.run_as("Aman", "4. Handover", press=["Save note"],
                          text={"Write a note": "Ask Karan for the Razorpay sandbox keys", "Remind me (optional)": "tomorrow"})
        self.assertIn("My notes", out)
        self.assertIn("Your own questions, to-dos and hunches", out)   # notes are a screen of their own now
        self.assertNotIn("4. Handover", out)           # ...so the handover page is not drawn underneath
        n = db.one("SELECT * FROM notes WHERE author='Aman'")
        self.assertIsNotNone(n)
        self.assertEqual(n["visibility"], "me")
        # the board shows the note, and Back closes the screen
        out = self.run_as("Aman", "4. Handover")
        self.assertIn("Ask Karan for the Razorpay", out)
        self.run_as("Aman", "4. Handover", press=["notes_back"])
        self.assertFalse(FAKE.session.get("notes_open"))
        FAKE.session["notes_open"] = False
        # quick note on an item shows as a sticky on that item's card
        self.run_as("Aman", "4. Handover", press=[f"Stick a note on #{item['id']}"],
                    text={"Quick note on this item": "Check this with Riya"})
        out = self.run_as("Aman", "4. Handover")
        self.assertIn("Your note:", out)
        self.assertIn("Check this with Riya", out)
        # another person never sees it
        out = self.run_as("Karan", "4. Handover")
        self.assertNotIn("Check this with Riya", out)
        self.assertNotIn("Ask Karan for the Razorpay", out)
        # notes never enter the handover export
        view = handover.view_for("Aman")
        from core import plan
        md = handover.export_markdown(view, plan.build_plan(view["items"]), "Aman", "Intern")
        self.assertNotIn("Check this with Riya", md)
        self.assertNotIn("Ask Karan for the Razorpay sandbox keys", md)
        # appearance studio: opens, picks a theme, remembered per user
        FAKE.session["notes_open"] = False
        FAKE.session["look_open"] = True
        out = self.run_as("Aman", "4. Handover", press=["use_terminal"],
                          select={})
        self.assertEqual(themes.get_prefs("Aman")["theme"], "terminal")
        self.assertEqual(themes.get_prefs("Karan")["theme"], "notebook")
        self.assertIn("Choose your look", out)
        out = self.run_as("Aman", "4. Handover", press=["look_reset"], select={"Text size": "m"})
        self.assertEqual(themes.get_prefs("Aman")["theme"], "notebook")
        FAKE.session["look_open"] = False


class TestPublicMode(unittest.TestCase):
    """With HT_PUBLIC=1 every visitor gets a private database."""

    def test_two_visitors_never_see_each_other(self):
        import shutil
        from core import config, db
        old_env = os.environ.get("HT_PUBLIC")
        os.environ["HT_PUBLIC"] = "1"
        ws_dir = str(config.BASE / "data" / "workspaces")
        try:
            FAKE.reset()
            app = importlib.import_module("app")
            try:
                importlib.reload(app)
            except Rerun:
                pass

            def visit(session, press=()):
                FAKE.out.clear()
                FAKE.session = session
                FAKE.press = set(press)
                FAKE.select = {"Signed in as (demo login)": "Riya", "Workflow": "1. Connect"}
                FAKE.text, FAKE.check, FAKE.files = {}, {}, []
                try:
                    app.main()
                except Rerun:
                    pass
                return db.q("SELECT COUNT(*) AS n FROM sources")[0]["n"]

            a, b = {}, {}
            self.assertEqual(visit(a), 0)
            self.assertGreater(visit(a, ["Load the demo project"]), 0)
            self.assertEqual(visit(b), 0)            # visitor B sees an empty workspace
            self.assertNotEqual(a["ws"], b["ws"])
            self.assertGreater(visit(a), 0)           # visitor A's data is still there
            self.assertEqual(app.provider_for_session(), "offline")
        finally:
            if old_env is None:
                os.environ.pop("HT_PUBLIC", None)
            else:
                os.environ["HT_PUBLIC"] = old_env
            db.use_path(None)
            shutil.rmtree(ws_dir, ignore_errors=True)
            FAKE.reset()
            try:
                importlib.reload(importlib.import_module("app"))
            except Rerun:
                pass
            db.use_path(None)


if __name__ == "__main__":
    unittest.main()
