"""Readiness score: eight-part breakdown, explanations, role filtering, and that it changes nothing."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import checklist, db, handover, readiness, transfer  # noqa: E402
from tests.test_core import Fresh  # noqa: E402
import ui  # noqa: E402


class TestReadinessBreakdown(Fresh):
    def test_empty_workspace(self):
        r = readiness.readiness()
        self.assertEqual((r["score"], r["breakdown"]), (0, []))
        self.assertIn("Import", r["todo"][0])

    def test_weights_sum_to_100_and_points_add_up(self):
        self.assertEqual(sum(readiness.WEIGHTS.values()), 100)
        self.demo()
        r = readiness.readiness("Lead")
        self.assertEqual(len(r["breakdown"]), 8)
        self.assertEqual(r["score"], round(sum(p["points"] for p in r["breakdown"])))
        for p in r["breakdown"]:
            self.assertLessEqual(p["points"], p["weight"])
        self.assertEqual(set(r["parts"]), {p["label"] for p in r["breakdown"]})

    def test_each_part_moves_with_real_work(self):
        self.demo()
        before = {p["key"]: p["pct"] for p in readiness.readiness("Lead")["breakdown"]}
        handover.approve_all_verified("Riya")
        after = {p["key"]: p["pct"] for p in readiness.readiness("Lead")["breakdown"]}
        self.assertGreater(after["review"], before["review"])
        self.assertEqual(after["evidence"], before["evidence"])      # approving does not create proof
        # a transfer in flight earns partial credit; completing it earns full credit
        who, item = next((p, r) for p in transfer.owners() for r in transfer.responsibilities(p)
                         if checklist.TYPE_SECTION.get(r["type"]) == "transfers")
        db.x("INSERT OR IGNORE INTO users(name, role) VALUES ('Zed','Lead')")
        pct = lambda: {p["key"]: p["pct"] for p in readiness.readiness("Lead")["breakdown"]}["transfers"]  # noqa: E731
        t0 = pct()                                   # nobody marked as leaving: 0
        tid = transfer.propose("Riya", "Lead", item["id"], "Aman")
        t1 = pct()
        transfer.decide("Zed", "Lead", tid, True)
        t2 = pct()
        transfer.complete("Riya", "Lead", tid)
        t3 = pct()
        self.assertEqual(t0, 0)
        self.assertTrue(0 < t1 < t2 < t3, (t1, t2, t3))

    def test_ownership_and_docs_react(self):
        self.demo()
        r = {p["key"]: p for p in readiness.readiness("Lead")["breakdown"]}
        gaps = db.q("SELECT id FROM items WHERE type IN ('next_action','deadline','owner') AND (owner IS NULL OR owner='')")
        self.assertTrue(gaps)
        for g in gaps:
            db.x("UPDATE items SET owner='Karan' WHERE id=?", (g["id"],))
        r2 = {p["key"]: p for p in readiness.readiness("Lead")["breakdown"]}
        self.assertLess(r["ownership"]["pct"], 100)
        self.assertEqual(r2["ownership"]["pct"], 100)
        self.assertEqual(r2["ownership"]["actions"], [])

    def test_improve_lists_biggest_loss_first_and_todo_matches(self):
        self.demo()
        r = readiness.readiness("Lead")
        lost = [i["lost"] for i in r["improve"]]
        self.assertEqual(lost, sorted(lost, reverse=True))
        self.assertTrue(r["todo"] and len(r["todo"]) <= 5)

    def test_unverified_items_do_not_count_as_proof(self):
        self.demo()
        db.x("UPDATE items SET verify_status='unverified'")
        r = {p["key"]: p for p in readiness.readiness("Lead")["breakdown"]}
        self.assertEqual(r["evidence"]["pct"], 0)
        self.assertIn("not found in the source", r["evidence"]["actions"][0]["text"])

    def test_restricted_items_are_counted_not_named(self):
        self.demo()
        lead_ids = {i["id"] for i in db.q("SELECT id FROM items WHERE visibility='Lead'")}
        self.assertTrue(lead_ids)
        intern = readiness.readiness("Intern")
        lead = readiness.readiness("Lead")
        self.assertEqual(intern["score"], lead["score"])            # same score for everyone
        listed = {n for p in intern["breakdown"] for a in p["actions"] for n in a["ids"]}
        self.assertFalse(listed & lead_ids)
        self.assertTrue(any(a["hidden"] for p in intern["breakdown"] for a in p["actions"]))
        blob = repr(intern)
        for i in db.q("SELECT text FROM items WHERE visibility='Lead'"):
            self.assertNotIn(i["text"][:40], blob)
        for fragment in ("Conflicts with", "item #"):                # flag text built for a Lead never reaches a smaller role
            self.assertNotIn(fragment, blob)
        self.assertTrue({n for p in lead["breakdown"] for a in p["actions"] for n in a["ids"]} & lead_ids)

    def test_read_only_no_audit_or_data_change(self):
        self.demo()
        tables = ("audit_log", "items", "checklist", "transfers", "item_versions")
        snap = {t: db.q(f"SELECT * FROM {t}") for t in tables}
        readiness.readiness("Lead")
        self.assertEqual(snap, {t: db.q(f"SELECT * FROM {t}") for t in tables})

    def test_html_is_escaped(self):
        rd = {"score": 50, "band": "<b>x</b>", "breakdown": [{"label": "<script>", "status": "Weak", "pct": 10, "points": 1,
              "weight": 15, "detail": "<i>d</i>", "actions": [{"text": "<img src=x>", "where": "w", "ids": [1], "more": 0, "hidden": 2}]}]}
        out = ui.readiness_html(rd)
        self.assertNotIn("<script>", out)
        self.assertNotIn("<img", out)
        self.assertIn("2 restricted item(s) not listed", out)


if __name__ == "__main__":
    unittest.main()
