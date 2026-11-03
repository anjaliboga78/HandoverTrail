"""Responsibility Transfer: propose > approve > complete, permissions, history, progress."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import db, extract, ingest, transfer  # noqa: E402
from test_core import Fresh  # noqa: E402


class T(Fresh):
    def setUp(self):
        db.use_path(None)
        super().setUp()
        ingest.load_demo("Riya")
        extract.run_extraction("Riya", provider="offline")
        self.who = next(o for o in transfer.owners() if len(transfer.responsibilities(o)) >= 1)
        self.item = transfer.responsibilities(self.who)[0]["id"]
        self.new = next(u["name"] for u in db.q("SELECT name FROM users") if u["name"].lower() != self.who.lower())

    def test_lists_only_that_persons_items(self):
        for r in transfer.responsibilities(self.who):
            self.assertEqual(r["owner"].lower().strip(), self.who.lower())

    def test_full_flow_changes_owner_only_at_completion(self):
        tid = transfer.propose("Riya", "Lead", self.item, self.new, "leaving")
        self.assertEqual(db.one("SELECT owner FROM items WHERE id=?", (self.item,))["owner"].lower(), self.who.lower())
        with self.assertRaises(ValueError):          # cannot finalize before approval
            transfer.complete("Riya", "Lead", tid)
        transfer.decide("Riya", "Lead", tid, True)
        self.assertEqual(db.one("SELECT owner FROM items WHERE id=?", (self.item,))["owner"].lower(), self.who.lower())
        transfer.complete("Riya", "Lead", tid)
        self.assertEqual(db.one("SELECT owner FROM items WHERE id=?", (self.item,))["owner"], self.new)
        self.assertEqual([e["event"] for e in transfer.history(tid)], ["proposed", "approved", "completed"])
        self.assertTrue(db.one("SELECT 1 AS x FROM item_versions WHERE item_id=? AND action='owner_transfer'", (self.item,)))
        self.assertTrue(db.one("SELECT 1 AS x FROM audit_log WHERE action='transfer_complete'"))

    def test_permissions(self):
        with self.assertRaises(PermissionError):
            transfer.propose("Aman", "Intern", self.item, self.new)
        tid = transfer.propose("Riya", "Lead", self.item, self.new)
        with self.assertRaises(PermissionError):
            transfer.decide("Karan", "Core", tid, True)
        transfer.decide("Riya", "Lead", tid, True)
        with self.assertRaises(PermissionError):     # an unrelated person cannot complete it
            transfer.complete("Aman" if self.new != "Aman" else "Meera", "Intern", tid)
        transfer.complete(self.new, "Core", tid)     # the new owner can

    def test_second_lead_must_approve_own_proposal(self):
        db.x("INSERT INTO users(name, role) VALUES ('Zed','Lead')")
        tid = transfer.propose("Riya", "Lead", self.item, self.new)
        with self.assertRaises(PermissionError):
            transfer.decide("Riya", "Lead", tid, True)
        transfer.decide("Zed", "Lead", tid, True)

    def test_validation(self):
        with self.assertRaises(ValueError):
            transfer.propose("Riya", "Lead", self.item, "  ")
        with self.assertRaises(ValueError):
            transfer.propose("Riya", "Lead", self.item, self.who)
        transfer.propose("Riya", "Lead", self.item, self.new)
        with self.assertRaises(ValueError):          # no duplicate active transfer
            transfer.propose("Riya", "Lead", self.item, "Someone")

    def test_reject_and_cancel_keep_history_and_owner(self):
        tid = transfer.propose("Riya", "Lead", self.item, self.new)
        transfer.decide("Riya", "Lead", tid, False, "not right")
        self.assertEqual(transfer.list_transfers(("rejected",))[0]["id"], tid)
        t2 = transfer.propose("Riya", "Lead", self.item, self.new)   # allowed again after rejection
        transfer.cancel("Riya", "Lead", t2)
        self.assertEqual(db.one("SELECT owner FROM items WHERE id=?", (self.item,))["owner"].lower(), self.who.lower())
        self.assertEqual(len(transfer.list_transfers(None, self.who)), 2)

    def test_progress_and_incoming(self):
        before = transfer.progress(self.who)
        self.assertEqual(before["completed"], 0)
        tid = transfer.propose("Riya", "Lead", self.item, self.new)
        self.assertEqual(transfer.progress(self.who)["awaiting_approval"], 1)
        transfer.decide("Riya", "Lead", tid, True)
        transfer.complete("Riya", "Lead", tid)
        after = transfer.progress(self.who)
        self.assertEqual(after["completed"], 1)
        self.assertEqual(after["total"], before["total"])
        self.assertTrue(transfer.incoming(self.new, "Lead"))

    def test_incoming_respects_visibility(self):
        db.x("UPDATE items SET visibility='Lead' WHERE id=?", (self.item,))
        tid = transfer.propose("Riya", "Lead", self.item, "Priya Test")
        self.assertEqual(transfer.incoming("Priya Test", "Intern"), [])
        self.assertEqual(len(transfer.incoming("Priya Test", "Lead")), 1)


if __name__ == "__main__":
    unittest.main()
