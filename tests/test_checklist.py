"""Departure Checklist: built from real data, ticks, progress, permissions, restricted items, transfers."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import checklist, config, db, extract, ingest, transfer  # noqa: E402


def entries(data, section=None):
    return [e for s in data["sections"] if section in (None, s["key"]) for e in s["entries"]]


class TestChecklist(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        config.DB_PATH = path
        db.use_path(None)
        db.init()
        ingest.load_demo("Riya")
        extract.run_extraction("Riya", provider="offline")

    def test_built_from_real_items_in_all_sections(self):
        d = checklist.build("Karan", "Lead")
        self.assertEqual([s["key"] for s in d["sections"]], ["transfers", "tasks", "decisions", "docs", "deps"])
        self.assertGreater(d["total"], 0)
        self.assertEqual(d["done"], 0)
        self.assertEqual(d["percent"], 0)
        self.assertTrue(entries(d, "transfers") and entries(d, "tasks") and entries(d, "docs"))
        for e in entries(d, "tasks"):
            self.assertEqual(db.one("SELECT owner FROM items WHERE id=?", (e["item_id"],))["owner"], "Karan")
        self.assertEqual(checklist.build("Nobody Here", "Lead")["total"], 0)

    def test_attention_list_is_ordered_and_explained(self):
        d = checklist.build("Karan", "Lead")
        self.assertEqual(len(d["attention"]), d["left"])
        scores = [e["score"] for e in d["attention"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(e["reasons"] for e in d["attention"]))
        self.assertGreater(d["urgent"], 0)
        self.assertTrue(any("No new owner proposed" in r for e in d["attention"] for r in e["reasons"]))

    def test_tick_untick_progress_and_audit(self):
        d = checklist.build("Karan", "Lead")
        t = entries(d, "tasks")[0]
        self.assertTrue(checklist.set_done("Riya", "Lead", "Karan", "tasks", t["ref"], True))
        d2 = checklist.build("Karan", "Lead")
        e = checklist.find(d2, "tasks", t["ref"])
        self.assertTrue(e["done"])
        self.assertEqual(e["done_by"], "Riya")
        self.assertEqual(d2["done"], 1)
        self.assertEqual(d2["left"], d["left"] - 1)
        self.assertEqual(d2["percent"], round(100 / d["total"]))
        self.assertFalse(checklist.set_done("Riya", "Lead", "Karan", "tasks", t["ref"], True))   # no change
        self.assertTrue(db.q("SELECT 1 FROM audit_log WHERE action='checklist_done'"))
        checklist.set_done("Riya", "Lead", "Karan", "tasks", t["ref"], False)
        self.assertEqual(checklist.build("Karan", "Lead")["done"], 0)
        self.assertTrue(db.q("SELECT 1 FROM audit_log WHERE action='checklist_undone'"))

    def test_who_may_change_it(self):
        t = entries(checklist.build("Karan", "Lead"), "tasks")[0]
        with self.assertRaises(PermissionError):
            checklist.set_done("Aman", "Intern", "Karan", "tasks", t["ref"], True)
        with self.assertRaises(PermissionError):
            checklist.set_done("Meera", "Core", "Karan", "tasks", t["ref"], True)
        self.assertTrue(checklist.set_done("Karan", "Core", "Karan", "tasks", t["ref"], True))    # the leaver themselves
        with self.assertRaises(PermissionError):
            checklist.add_custom("Aman", "Intern", "Karan", "docs", "x")
        self.assertEqual(db.q("SELECT COUNT(*) AS n FROM checklist WHERE done=1")[0]["n"], 1)

    def test_transfers_cannot_be_ticked_by_hand_but_complete_with_the_transfer(self):
        d = checklist.build("Karan", "Lead")
        tr = entries(d, "transfers")[0]
        self.assertTrue(tr["locked"])
        with self.assertRaises(ValueError):
            checklist.set_done("Riya", "Lead", "Karan", "transfers", tr["ref"], True)
        task = entries(d, "tasks")[0]
        for e in (tr, task):
            tid = transfer.propose("Riya", "Lead", e["item_id"], "Meera", "leaving")
            transfer.decide("Riya", "Lead", tid, True)
        mid = checklist.build("Karan", "Lead")
        self.assertIn("Waiting for Meera to complete the transfer", checklist.find(mid, "tasks", task["ref"])["reasons"])
        for t in transfer.list_transfers(("approved",), "Karan"):
            transfer.complete("Meera", "Core", t["id"])
        after = checklist.build("Karan", "Lead")
        e = checklist.find(after, "transfers", tr["ref"])
        self.assertTrue(e["done"] and e["auto"])
        self.assertIn("handed to Meera", e["detail"])
        self.assertTrue(checklist.find(after, "tasks", task["ref"])["done"])
        self.assertEqual(after["total"], d["total"])                 # the items moved, the denominator did not shrink
        self.assertEqual(after["done"], 2)
        with self.assertRaises(ValueError):
            checklist.set_done("Riya", "Lead", "Karan", "tasks", task["ref"], False)

    def test_restricted_items_are_hidden_and_not_counted(self):
        lead = checklist.build("Riya", "Lead")
        core = checklist.build("Riya", "Core")
        self.assertGreater(core["restricted"], 0)
        self.assertEqual(core["total"] + core["restricted"], lead["total"])
        text = " ".join(e["label"] + e["detail"] for e in entries(core))
        self.assertNotIn("24 March", text)                            # text of the lead-only sponsor note never shows
        ph = next(e for e in entries(core) if e["restricted"])
        with self.assertRaises(PermissionError):
            checklist.set_done("Riya", "Core", "Riya", ph["section"], ph["ref"], True)

    def test_docs_lines_come_from_technical_topics(self):
        d = checklist.build("Karan", "Lead")
        labels = " ".join(e["label"] for e in entries(d, "docs"))
        self.assertIn("payments", labels)
        for e in entries(d, "docs"):
            self.assertFalse(e["locked"])
            checklist.set_done("Riya", "Lead", "Karan", "docs", e["ref"], True)
        self.assertEqual(checklist.build("Karan", "Lead")["sections"][3]["percent"], 100)

    def test_dependencies_that_name_the_person_are_listed(self):
        sid = db.one("SELECT id FROM sources LIMIT 1")["id"]
        db.x("INSERT INTO items(source_id,type,text,owner,quote,topic,confidence,verify_status,verify_score,visibility,"
             "extractor,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
             (sid, "dependency", "We need Karan for the Razorpay sandbox keys", None, "We need Karan for the Razorpay sandbox keys",
              "payments", 0.6, "verified", 100, "Everyone", "manual", db.now()))
        d = checklist.build("Karan", "Lead")
        dep = next(e for e in entries(d, "deps") if "sandbox keys" in e["label"])
        self.assertIn("nobody owns it", dep["detail"])
        self.assertGreaterEqual(dep["score"], 2)
        checklist.set_done("Riya", "Lead", "Karan", "deps", dep["ref"], True)
        self.assertTrue(checklist.find(checklist.build("Karan", "Lead"), "deps", dep["ref"])["done"])

    def test_custom_lines_and_notes(self):
        rid = checklist.add_custom("Riya", "Lead", "Karan", "docs", "  Share the   runbook link ")
        d = checklist.build("Karan", "Lead")
        e = checklist.find(d, "docs", f"custom:{rid}")
        self.assertEqual(e["label"], "Share the runbook link")
        self.assertTrue(e["custom"])
        checklist.set_done("Riya", "Lead", "Karan", "docs", e["ref"], True)
        checklist.set_note("Riya", "Lead", "Karan", "docs", e["ref"], "x" * 400)
        e = checklist.find(checklist.build("Karan", "Lead"), "docs", e["ref"])
        self.assertTrue(e["done"])
        self.assertEqual(len(e["note"]), 300)
        # a note on a built line does not tick it
        t = entries(d, "tasks")[0]
        checklist.set_note("Riya", "Lead", "Karan", "tasks", t["ref"], "see the wiki")
        t2 = checklist.find(checklist.build("Karan", "Lead"), "tasks", t["ref"])
        self.assertEqual((t2["note"], t2["done"]), ("see the wiki", False))
        for bad in ("", "   ", "y" * 121):
            with self.assertRaises(ValueError):
                checklist.add_custom("Riya", "Lead", "Karan", "docs", bad)
        with self.assertRaises(ValueError):
            checklist.add_custom("Riya", "Lead", "Karan", "nonsense", "x")
        with self.assertRaises(ValueError):
            checklist.delete_custom("Riya", "Lead", "Karan", t["ref"])        # built lines cannot be deleted
        checklist.delete_custom("Riya", "Lead", "Karan", f"custom:{rid}")
        self.assertIsNone(checklist.find(checklist.build("Karan", "Lead"), "docs", f"custom:{rid}"))

    def test_unknown_lines_are_rejected(self):
        with self.assertRaises(ValueError):
            checklist.set_done("Riya", "Lead", "Karan", "tasks", "item:99999", True)
        with self.assertRaises(ValueError):
            checklist.set_done("Riya", "Lead", "Karan", "bogus", "item:1", True)

    def test_one_person_never_sees_anothers_ticks(self):
        t = entries(checklist.build("Karan", "Lead"), "tasks")[0]
        checklist.set_done("Riya", "Lead", "Karan", "tasks", t["ref"], True)
        self.assertEqual(checklist.build("Meera", "Lead")["done"], 0)

    def test_export_and_ready_state_and_reset(self):
        d = checklist.build("Meera", "Lead")
        md = checklist.export_markdown(d)
        self.assertIn("# Departure checklist: Meera", md)
        self.assertIn("- [ ]", md)
        self.assertFalse(d["ready"])
        for e in entries(d):
            if not e["locked"]:
                checklist.set_done("Riya", "Lead", "Meera", e["section"], e["ref"], True)
        self.assertIn("- [x]", checklist.export_markdown(checklist.build("Meera", "Lead")))
        db.reset_all()
        self.assertEqual(db.q("SELECT COUNT(*) AS n FROM checklist")[0]["n"], 0)


if __name__ == "__main__":
    unittest.main()
