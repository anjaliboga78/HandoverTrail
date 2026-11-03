"""Automated tests for the trust-critical parts: redaction, Evidence Gate, permissions, approval.

Run with:  python -m unittest discover -s tests -v      (or: pytest)
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import config, db, extract, flags, handover, ingest, plan, roles  # noqa: E402
from core.redact import redact  # noqa: E402
from core.verify import verify, highlight_html  # noqa: E402


class Fresh(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        config.DB_PATH = path
        db.init()

    def tearDown(self):
        try:
            os.remove(config.DB_PATH)
        except OSError:
            pass

    def demo(self):
        ingest.load_demo("Riya")
        return extract.run_extraction("Riya", provider="offline")


class TestRedaction(unittest.TestCase):
    def test_masks_key_password_email_phone(self):
        text = "key sk_test_FAKE12345678 and password is hunter2 mail a.b@club.org call 9876543210"
        clean, found = redact(text)
        for secret in ("sk_test_FAKE12345678", "hunter2", "a.b@club.org", "9876543210"):
            self.assertNotIn(secret, clean)
        self.assertEqual({t for t, _ in found}, {"KEY", "PASSWORD", "EMAIL", "PHONE"})

    def test_previews_never_contain_full_secret(self):
        _, found = redact("password: supersecret99")
        self.assertTrue(all("supersecret99" not in p for _, p in found))

    def test_plain_text_untouched(self):
        t = "We decided to use PostgreSQL on 24 March."
        self.assertEqual(redact(t)[0], t)


class TestEvidenceGate(unittest.TestCase):
    SRC = "Karan: ok, let's move to PostgreSQL for JSON support.\nRiya agreed."

    def test_exact_quote_verified(self):
        self.assertEqual(verify("let's move to PostgreSQL for JSON support", self.SRC)[0], "verified")

    def test_whitespace_and_case_tolerated(self):
        self.assertEqual(verify("LET'S  move to postgresql\nfor json support", self.SRC)[0], "verified")

    def test_tiny_difference_is_approximate(self):
        self.assertEqual(verify("let's move to PostgreSQL for JSON suport", self.SRC)[0], "approximate")

    def test_invented_quote_unverified(self):
        self.assertEqual(verify("we will use MongoDB for everything", self.SRC)[0], "unverified")

    def test_empty_or_trivial_quote_unverified(self):
        self.assertEqual(verify("", self.SRC)[0], "unverified")
        self.assertEqual(verify("ok", self.SRC)[0], "unverified")

    def test_highlight_escapes_html(self):
        out = highlight_html("<script>x</script> hello world", "hello world")
        self.assertNotIn("<script>", out)
        self.assertIn("<mark>hello world</mark>", out)


class TestIngest(Fresh):
    def test_csv_becomes_quotable_sentences(self):
        ids = ingest.ingest_upload("t.csv", b"id,title,owner,status,due,notes\nT-1,Pay,,blocked,2026-03-01,x\n", "Everyone")
        text = db.one("SELECT text FROM sources WHERE id=?", (ids[0],))["text"]
        self.assertIn("Task T-1: Pay. Owner: none. Status: blocked.", text)

    def test_secret_masked_before_storage(self):
        ingest.ingest_upload("chat.txt", b"[2026-01-01 10:00] Karan: key is sk_test_ABCDEFGH1234 ok", "Core")
        row = db.one("SELECT text, redaction_count FROM sources")
        self.assertNotIn("sk_test_ABCDEFGH1234", row["text"])
        self.assertEqual(row["redaction_count"], 1)

    def test_bad_inputs_raise_clear_errors(self):
        with self.assertRaises(ValueError):
            ingest.ingest_upload("x.exe", b"abc", "Everyone")
        with self.assertRaises(ValueError):
            ingest.ingest_upload("x.json", b"{not json", "Everyone")
        with self.assertRaises(ValueError):
            ingest.ingest_upload("x.txt", b"   ", "Everyone")
        with self.assertRaises(ValueError):
            ingest.add_source("a", "document", "text", "Nobody")

    def test_github_json_shapes(self):
        issues = b'[{"number": 3, "title": "Bug", "state": "open", "user": {"login": "a"}, "created_at": "2026-01-02T00:00:00Z", "body": "It crashes."}]'
        ids = ingest.ingest_upload("i.json", issues, "Everyone")
        self.assertEqual(len(ids), 1)
        commits = b'[{"sha": "abc", "commit": {"author": {"name": "Karan", "date": "2026-01-02T00:00:00Z"}, "message": "fix thing"}}]'
        self.assertEqual(len(ingest.ingest_upload("c.json", commits, "Everyone")), 1)

    def test_github_repo_name_validated(self):
        with self.assertRaises(ValueError):
            ingest.fetch_github("not a repo")


class TestPipeline(Fresh):
    def test_demo_extracts_items_all_verified_offline(self):
        r = self.demo()
        self.assertGreaterEqual(r["items"], 25)
        statuses = {i["verify_status"] for i in handover.list_items()}
        self.assertEqual(statuses, {"verified"})

    def test_every_quote_exists_in_its_source(self):
        self.demo()
        for it in handover.list_items():
            src = db.one("SELECT text FROM sources WHERE id=?", (it["source_id"],))
            self.assertEqual(verify(it["quote"], src["text"])[0], "verified", it["text"])

    def test_planted_conflicts_gaps_and_recurring_found(self):
        self.demo()
        items = handover.list_items()
        conflicts = [i for i in items if i["is_conflict"]]
        texts = " ".join(i["text"] for i in conflicts)
        self.assertIn("MySQL", texts)
        self.assertIn("PostgreSQL", texts)
        self.assertIn("10 March", texts)
        self.assertIn("24 March", texts)
        self.assertTrue(any("payment integration" in i["text"].lower() for i in items if i["is_gap"]))
        rec = [i for i in items if i["is_recurring"]]
        self.assertGreaterEqual(len(rec), 3)
        self.assertTrue(all(i["type"] == "risk" for i in rec))

    def test_plan_groups_recurring_problem_into_one_line(self):
        self.demo()
        for it in handover.list_items():
            handover.set_review(it["id"], "approved", "Riya")
        handover.approve_handover("Riya", "Lead")
        p = plan.build_plan(handover.view_for("Lead")["items"])
        rec = [l for l in p["Week 1"] if "recurring problem" in l["text"]]
        self.assertEqual(len(rec), 1)
        self.assertGreaterEqual(len(rec[0]["ids"]), 3)

    def test_extraction_is_not_repeated(self):
        self.demo()
        again = extract.run_extraction("Riya", provider="offline")
        self.assertEqual(again["items"], 0)

    def test_missing_api_key_falls_back_with_warning(self):
        ingest.load_demo("Riya")
        os.environ.pop("ANTHROPIC_API_KEY", None)
        r = extract.run_extraction("Riya", provider="anthropic")
        self.assertGreater(r["items"], 0)
        self.assertTrue(r["warnings"])

    def test_manual_fake_quote_is_unverified(self):
        self.demo()
        sid = db.one("SELECT id FROM sources WHERE name LIKE 'meeting_01%'")["id"]
        r = extract.add_manual_item(sid, "decision", "Use MongoDB", "We will use MongoDB for everything", "Riya", "Riya")
        self.assertEqual(r["status"], "unverified")


class TestParseJson(unittest.TestCase):
    def test_parses_fenced_json_and_drops_bad_types(self):
        raw = '```json\n[{"type":"decision","text":"Use X","quote":"we use X now","owner":null,"confidence":2},' \
              '{"type":"gossip","text":"nope","quote":"nope"}]\n```'
        out = extract.parse_json_list(raw)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["confidence"], 1.0)
        self.assertIsNone(out[0]["owner"])

    def test_garbage_raises(self):
        with self.assertRaises(extract.ExtractionError):
            extract.parse_json_list("sorry, I cannot do that")
        with self.assertRaises(extract.ExtractionError):
            extract.parse_json_list("[{broken")


class TestPermissions(Fresh):
    def approve_everything(self):
        self.demo()
        for it in handover.list_items():
            handover.set_review(it["id"], "approved", "Riya")
        return handover.approve_handover("Riya", "Lead")

    def test_role_levels(self):
        self.assertTrue(roles.can_see("Lead", "Lead"))
        self.assertTrue(roles.can_see("Core", "Core"))
        self.assertFalse(roles.can_see("Core", "Lead"))
        self.assertFalse(roles.can_see("Intern", "Core"))
        self.assertTrue(roles.can_see("Intern", "Everyone"))

    def test_intern_never_receives_restricted_items(self):
        self.approve_everything()
        v = handover.view_for("Intern")
        self.assertTrue(v["restricted"] > 0)
        self.assertTrue(all(i["visibility"] == "Everyone" for i in v["items"]))
        blob = " ".join(i["text"] + i["quote"] for i in v["items"])
        self.assertNotIn("10000 more rupees", blob)
        self.assertNotIn("blue theme", blob)

    def test_core_sees_chat_but_not_lead_note(self):
        self.approve_everything()
        v = handover.view_for("Core")
        blob = " ".join(i["text"] for i in v["items"])
        self.assertIn("blue theme", blob)
        self.assertNotIn("10000 more rupees", blob)

    def test_flags_never_name_hidden_sources(self):
        self.approve_everything()
        v = handover.view_for("Intern")
        for i in v["items"]:
            for line in flags.describe(i, v["all_items"], "Intern"):
                self.assertNotIn("sponsor", line.lower())

    def test_plan_for_intern_has_no_restricted_text(self):
        self.approve_everything()
        v = handover.view_for("Intern")
        p = plan.build_plan(v["items"])
        text = " ".join(l["text"] for b in p.values() for l in b)
        self.assertNotIn("10000", text)
        self.assertTrue(any(p.values()))


class TestApprovalAndAck(Fresh):
    def test_only_lead_can_approve(self):
        self.demo()
        handover.set_review(handover.list_items()[0]["id"], "approved", "Riya")
        with self.assertRaises(PermissionError):
            handover.approve_handover("Aman", "Intern")
        with self.assertRaises(PermissionError):
            handover.approve_handover("Karan", "Core")

    def test_cannot_approve_empty_handover(self):
        self.demo()
        with self.assertRaises(ValueError):
            handover.approve_handover("Riya", "Lead")

    def test_no_handover_visible_before_approval(self):
        self.demo()
        self.assertIsNone(handover.view_for("Intern"))

    def test_edit_creates_version_and_new_handover_version(self):
        self.demo()
        it = handover.list_items()[0]
        handover.set_review(it["id"], "approved", "Riya", new_text="Edited wording for the item")
        hist = db.q("SELECT action FROM item_versions WHERE item_id=?", (it["id"],))
        self.assertEqual({h["action"] for h in hist}, {"edit", "approved"})
        h1 = handover.approve_handover("Riya", "Lead")
        h2 = handover.approve_handover("Riya", "Lead")
        self.assertNotEqual(h1, h2)
        self.assertEqual(handover.current_handover()["version"], 2)

    def test_rejected_items_not_in_handover(self):
        self.demo()
        items = handover.list_items()
        handover.set_review(items[0]["id"], "approved", "Riya")
        handover.set_review(items[1]["id"], "rejected", "Riya")
        handover.approve_handover("Riya", "Lead")
        ids = {i["id"] for i in handover.current_handover()["items"]}
        self.assertIn(items[0]["id"], ids)
        self.assertNotIn(items[1]["id"], ids)

    def test_bulk_approve_skips_conflicts(self):
        self.demo()
        n = handover.approve_all_verified("Riya")
        self.assertGreater(n, 0)
        for it in handover.list_items():
            if it["is_conflict"]:
                self.assertEqual(it["review_status"], "pending")

    def test_acknowledge_once_and_audited(self):
        self.demo()
        handover.set_review(handover.list_items()[0]["id"], "approved", "Riya")
        handover.approve_handover("Riya", "Lead")
        self.assertTrue(handover.acknowledge("Aman"))
        self.assertFalse(handover.acknowledge("Aman"))
        self.assertIsNotNone(handover.acked("Aman"))
        actions = {r["action"] for r in db.q("SELECT action FROM audit_log")}
        self.assertTrue({"import_source", "extract", "approve_handover", "acknowledge"} <= actions)

    def test_ack_without_handover_raises(self):
        with self.assertRaises(ValueError):
            handover.acknowledge("Aman")


class TestPublicReadiness(Fresh):
    def test_upload_size_limit(self):
        with self.assertRaises(ValueError):
            ingest.ingest_upload("big.txt", b"a" * (ingest.MAX_UPLOAD_BYTES + 1), "Everyone")

    def test_export_respects_role_and_includes_proof(self):
        self.demo()
        for it in handover.list_items():
            handover.set_review(it["id"], "approved", "Riya")
        handover.approve_handover("Riya", "Lead")
        v = handover.view_for("Intern")
        md = handover.export_markdown(v, plan.build_plan(v["items"]), "Aman", "Intern")
        self.assertIn("Action plan", md)
        self.assertIn("Proof (", md)
        self.assertIn("restricted for this role", md)
        self.assertNotIn("10000 more rupees", md)
        self.assertNotIn("blue theme", md)

    def test_cleanup_removes_only_old_workspaces(self):
        import time
        folder = tempfile.mkdtemp()
        old, new = os.path.join(folder, "old.db"), os.path.join(folder, "new.db")
        for p in (old, new):
            open(p, "w").close()
        past = time.time() - 48 * 3600
        os.utime(old, (past, past))
        self.assertEqual(db.cleanup_workspaces(folder, 24), 1)
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(new))


class TestLLMClient(unittest.TestCase):
    def test_retries_on_rate_limit_then_succeeds(self):
        from unittest import mock
        from core import llm

        class R:
            def __init__(self, code, body=None):
                self.status_code, self._b = code, body or {}

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise llm.requests.HTTPError("bad")

            def json(self):
                return self._b

        ok = R(200, {"candidates": [{"content": {"parts": [{"text": "[]"}]}}]})
        os.environ["GEMINI_API_KEY"] = "test"
        with mock.patch.object(llm.requests, "post", side_effect=[R(429), ok]) as post, \
                mock.patch.object(llm.time, "sleep"):
            self.assertEqual(llm.complete("s", "u", provider="gemini"), "[]")
            self.assertEqual(post.call_count, 2)
        os.environ.pop("GEMINI_API_KEY", None)

    def test_network_failure_becomes_friendly_error(self):
        from unittest import mock
        from core import llm
        os.environ["GEMINI_API_KEY"] = "test"
        with mock.patch.object(llm.requests, "post", side_effect=llm.requests.ConnectionError()):
            with self.assertRaises(llm.LLMError):
                llm.complete("s", "u", provider="gemini")
        os.environ.pop("GEMINI_API_KEY", None)


if __name__ == "__main__":
    unittest.main()
