"""Notes: private by default, role-safe, never evidence unless a Lead promotes one with proof."""
import datetime as dt
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db, extract, handover, ingest, notes

REF = dt.date(2026, 11, 3)


def fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    db.use_path(path)
    db.init()


def approved_project():
    ingest.load_demo("Riya")
    extract.run_extraction("Riya", provider="offline")
    for it in handover.list_items():
        if it["verify_status"] != "unverified":
            handover.set_review(it["id"], "approved", "Riya")
    handover.approve_handover("Riya", "Lead")


class TestWhen(unittest.TestCase):
    def test_natural_dates(self):
        p = lambda t: notes.parse_when(t, REF)
        self.assertIsNone(p(""))
        self.assertEqual(p("today"), "2026-11-03")
        self.assertEqual(p("tomorrow"), "2026-11-04")
        self.assertEqual(p("in 3 days"), "2026-11-06")
        self.assertEqual(p("+2d"), "2026-11-05")
        self.assertEqual(p("in 1 week"), "2026-11-10")
        self.assertEqual(p("friday"), "2026-11-06")
        self.assertEqual(p("tuesday"), "2026-11-10")      # never "today": the next one
        self.assertEqual(p("12 Nov"), "2026-11-12")
        self.assertEqual(p("1 Nov"), "2027-11-01")        # already passed this year
        self.assertEqual(p("12 November 2026"), "2026-11-12")
        self.assertEqual(p("2026-11-12"), "2026-11-12")
        for bad in ("someday", "31 Feb", "2026-02-30"):
            with self.assertRaises(ValueError):
                p(bad)

    def test_labels(self):
        self.assertEqual(notes.when_label("2026-11-03", REF), ("Due today", "due"))
        self.assertEqual(notes.when_label("2026-11-01", REF), ("Overdue 2 days", "over"))
        self.assertEqual(notes.when_label("2026-11-04", REF), ("Tomorrow", "later"))
        self.assertEqual(notes.when_label(None, REF), ("", ""))


class TestNotes(unittest.TestCase):
    def setUp(self):
        fresh_db()
        approved_project()
        self.items = handover.list_items()
        self.open_item = next(i for i in self.items if i["visibility"] == "Everyone")
        self.lead_item = next(i for i in self.items if i["visibility"] == "Lead")

    def test_private_by_default_and_sharing_rules(self):
        a = notes.create("Aman", "Intern", "my private question", "question")
        t = notes.create("Aman", "Intern", "for the team", "idea", visibility="team")
        l = notes.create("Aman", "Intern", "for leads only", "headsup", visibility="leads")
        ids = lambda user, role, scope="all": {n["id"] for n in notes.list_for(user, role, scope)}
        self.assertEqual(ids("Aman", "Intern"), {a, t, l})
        self.assertEqual(ids("Karan", "Core"), {t})                  # Core sees team only
        self.assertEqual(ids("Riya", "Lead"), {t, l})                # a Lead also gets "leads only"
        self.assertNotIn(a, ids("Riya", "Lead"))                     # nobody sees "only me"
        self.assertEqual(ids("Riya", "Lead", "shared"), {t, l})
        self.assertEqual(ids("Aman", "Intern", "shared"), set())     # your own notes are not "shared with you"

    def test_secrets_are_masked_and_audit_log_never_holds_text(self):
        nid = notes.create("Riya", "Lead", "login is password: hunter2 and mail a@b.com")
        body = db.one("SELECT body FROM notes WHERE id=?", (nid,))["body"]
        self.assertNotIn("hunter2", body)
        self.assertNotIn("a@b.com", body)
        log = " ".join(f"{r['target']} {r['detail']}" for r in db.q("SELECT * FROM audit_log WHERE action='note_create'"))
        self.assertNotIn("hunter2", log)
        self.assertIn("secrets masked", log)

    def test_linking_is_limited_to_items_you_may_see(self):
        notes.create("Riya", "Lead", "about the sponsor", link_item_id=self.lead_item["id"])
        with self.assertRaises(ValueError):
            notes.create("Aman", "Intern", "sneaky", link_item_id=self.lead_item["id"])
        n = notes.create("Riya", "Lead", "visible to team but about a lead-only item", visibility="team",
                         link_item_id=self.lead_item["id"])
        self.assertNotIn(n, {x["id"] for x in notes.list_for("Aman", "Intern")})
        self.assertNotIn(n, {x["id"] for x in notes.list_for("Karan", "Core")})
        ok = notes.create("Riya", "Lead", "fine to share", visibility="team", link_item_id=self.open_item["id"])
        self.assertIn(ok, {x["id"] for x in notes.list_for("Aman", "Intern")})
        self.assertIn(ok, [n["id"] for n in notes.by_item("Aman", "Intern").get(self.open_item["id"], [])])

    def test_validation(self):
        for kwargs in ({"body": ""}, {"body": "x" * 601}, {"body": "ok", "kind": "nope"}, {"body": "ok", "visibility": "all"},
                       {"body": "ok", "color": "purple"}, {"body": "ok", "remind_text": "someday"}):
            with self.assertRaises(ValueError):
                notes.create("Riya", "Lead", **kwargs)

    def test_only_the_author_can_change_a_note(self):
        nid = notes.create("Aman", "Intern", "mine", visibility="team")
        for fn in (lambda: notes.edit(nid, "Karan", "hacked"), lambda: notes.set_pin(nid, "Karan", True),
                   lambda: notes.set_done(nid, "Karan", True), lambda: notes.delete(nid, "Karan")):
            with self.assertRaises(PermissionError):
                fn()
        notes.set_pin(nid, "Aman", True)
        notes.set_done(nid, "Aman", True)
        notes.edit(nid, "Aman", "mine, edited", "me")
        self.assertEqual(notes.list_for("Karan", "Core"), [])        # moved back to private
        notes.delete(nid, "Aman")
        self.assertEqual(notes.list_for("Aman", "Intern"), [])

    def test_reminders_pin_order_and_search(self):
        a = notes.create("Riya", "Lead", "old thing", remind_text="today")
        b = notes.create("Riya", "Lead", "pinned thing")
        c = notes.create("Riya", "Lead", "plain Razorpay thing")
        notes.set_pin(b, "Riya", True)
        order = [n["id"] for n in notes.list_for("Riya", "Lead", ref=dt.date.today())]
        self.assertEqual(order[0], b)                                # pinned first
        self.assertEqual(order[1], a)                                # then due
        self.assertEqual([n["id"] for n in notes.due("Riya", "Lead")], [a])
        self.assertEqual([n["id"] for n in notes.list_for("Riya", "Lead", query="razorpay")], [c])
        notes.set_done(a, "Riya", True)
        self.assertEqual(notes.due("Riya", "Lead"), [])
        self.assertEqual(notes.stats("Riya", "Lead")["open"], 2)

    def test_board_filters_by_type_and_hides_done(self):
        a = notes.create("Aman", "Intern", "Fix the login page", "todo")
        notes.create("Aman", "Intern", "Why is the sponsor late?", "question")
        notes.set_done(a, "Aman", True)
        kinds = lambda **kw: sorted(n["kind"] for n in notes.list_for("Aman", "Intern", **kw))
        self.assertEqual(kinds(), ["question", "todo"])
        self.assertEqual(kinds(kind="question"), ["question"])
        self.assertEqual(kinds(show_done=False), ["question"])
        self.assertEqual(kinds(kind="todo", show_done=False), [])
        self.assertEqual(notes.stats("Aman", "Intern")["done"], 1)

    def test_signals_when_the_linked_item_moves(self):
        nid = notes.create("Riya", "Lead", "check this", link_item_id=self.open_item["id"])
        n = db.one("SELECT * FROM notes WHERE id=?", (nid,))
        self.assertFalse([s for s in notes.signals(n) if "edited" in s])
        db.x("UPDATE notes SET created_at='2000-01-01T00:00:00' WHERE id=?", (nid,))
        handover.set_review(self.open_item["id"], "approved", "Riya", "Edited wording of this item")
        n = db.one("SELECT * FROM notes WHERE id=?", (nid,))
        self.assertTrue([s for s in notes.signals(n) if "edited" in s])

    def test_promotion_needs_a_lead_and_an_exact_quote(self):
        nid = notes.create("Aman", "Intern", "We switched to PostgreSQL for JSON support", "idea", visibility="team")
        src = db.one("SELECT id, text FROM sources WHERE name LIKE 'meeting_05%'")
        sug = notes.suggest_quotes("We switched to PostgreSQL for JSON support", "Lead")
        self.assertTrue(sug and "PostgreSQL" in sug[0]["line"])
        with self.assertRaises(PermissionError):
            notes.promote(nid, "Aman", "Intern", src["id"], "decision", sug[0]["line"])
        with self.assertRaises(ValueError):                            # invented quote stays a note
            notes.promote(nid, "Riya", "Lead", src["id"], "decision", "We will use MongoDB for everything")
        before = db.q("SELECT COUNT(*) AS n FROM items")[0]["n"]
        self.assertEqual(db.q("SELECT COUNT(*) AS n FROM items")[0]["n"], before)
        iid = notes.promote(nid, "Riya", "Lead", sug[0]["source_id"], "decision", sug[0]["line"])
        item = db.one("SELECT * FROM items WHERE id=?", (iid,))
        self.assertEqual(item["review_status"], "pending")            # still needs the normal review
        self.assertIn(item["verify_status"], ("verified", "approximate"))
        self.assertEqual(db.one("SELECT promoted_item_id AS p FROM notes WHERE id=?", (nid,))["p"], iid)
        with self.assertRaises(ValueError):
            notes.promote(nid, "Riya", "Lead", sug[0]["source_id"], "decision", sug[0]["line"])
        with self.assertRaises(ValueError):                            # author cannot edit a promoted note
            notes.edit(nid, "Aman", "changed")

    def test_quote_suggestions_respect_source_visibility(self):
        secret = db.one("SELECT id, text FROM sources WHERE visibility='Lead'")
        line = next(l for l in secret["text"].splitlines() if len(l) > 25)
        self.assertTrue(notes.suggest_quotes(line, "Lead", min_score=80))
        self.assertFalse(notes.suggest_quotes(line, "Intern", min_score=80))

    def test_export_is_only_your_notes_and_says_it_is_not_evidence(self):
        notes.create("Riya", "Lead", "mine one", "todo")
        notes.create("Aman", "Intern", "theirs", "todo", visibility="team")
        md = notes.export_markdown("Riya", "Lead")
        self.assertIn("mine one", md)
        self.assertNotIn("theirs", md)
        self.assertIn("not evidence", md)

    def test_reset_everything_clears_notes_but_keeps_looks(self):
        from core import themes
        notes.create("Riya", "Lead", "x")
        themes.set_pref("Riya", "theme", "pop")
        db.reset_all()
        self.assertEqual(db.q("SELECT COUNT(*) AS n FROM notes")[0]["n"], 0)
        self.assertEqual(themes.get_prefs("Riya")["theme"], "pop")


if __name__ == "__main__":
    unittest.main()
