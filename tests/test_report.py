"""PDF Handover Report: content, role filtering, masking, audit log."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db, handover, report, transfer  # noqa: E402
from tests.test_core import Fresh  # noqa: E402


def pdf_text(pdf: bytes, tmp: str = "") -> str:
    """All text in the PDF, read with pypdf (pure Python, works on Windows, Mac and Linux)."""
    from pypdf import PdfReader
    import io
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)


class TestReport(Fresh):
    def ready(self):
        self.demo()
        handover.approve_all_verified("Riya")
        handover.approve_handover("Riya", "Lead")

    def test_needs_an_approved_handover_and_a_person(self):
        self.demo()
        with self.assertRaises(ValueError):
            report.build_data("Riya", "Lead", "Karan")
        self.ready()
        with self.assertRaises(ValueError):
            report.build_data("Riya", "Lead", " ")

    def test_pdf_has_every_section(self):
        self.ready()
        pdf = report.generate("Riya", "Lead", "Karan")
        self.assertTrue(pdf.startswith(b"%PDF"))
        text = pdf_text(pdf, config_tmp())
        for part in ("Project overview", "responsibilities and new owners", "Important decisions", "Pending tasks",
                     "Handover readiness", "Onboarding plan", "Day 1", "Week 1", "Month 1", "Karan", "/100"):
            self.assertIn(part, text)

    def test_new_owner_appears_after_a_transfer(self):
        self.ready()
        item = next(r for r in transfer.responsibilities("Karan"))
        db.x("INSERT OR IGNORE INTO users(name, role) VALUES ('Zed','Lead')")
        tid = transfer.propose("Riya", "Lead", item["id"], "Meera")
        d = report.build_data("Riya", "Lead", "Karan")
        row = next(r for r in d["resp"] if r["id"] == item["id"])
        self.assertEqual((row["new_owner"], row["state"]), ("Meera", "proposed"))
        transfer.decide("Zed", "Lead", tid, True)
        transfer.complete("Riya", "Lead", tid)
        d = report.build_data("Riya", "Lead", "Karan")
        self.assertEqual(d["resp_done"], 1)

    def test_restricted_text_never_reaches_a_smaller_role(self):
        self.ready()
        restricted = db.q("SELECT i.text, s.name AS src FROM items i JOIN sources s ON s.id=i.source_id WHERE i.visibility='Lead'")
        self.assertTrue(restricted)
        self.assertNotEqual(report.build_data("Aman", "Intern", "Karan")["overview"]["restricted"], 0)
        for who, role in (("Aman", "Intern"), ("Karan", "Core")):
            vis = {"Intern": ("Lead", "Core"), "Core": ("Lead",)}[role]
            hidden = db.q(f"SELECT i.text, s.name AS src FROM items i JOIN sources s ON s.id=i.source_id "
                          f"WHERE i.visibility IN ({','.join('?' * len(vis))})", vis)
            pdf = report.generate(who, role, "Karan")
            text = " ".join(pdf_text(pdf, config_tmp()).split())
            for h in hidden:
                self.assertNotIn(" ".join(h["text"].split())[:40], text)
                self.assertNotIn(h["src"], text)
            self.assertIn("restricted for your role", text)

    def test_secrets_are_masked_in_the_pdf(self):
        self.ready()
        d = report.build_data("Riya", "Lead", "Karan")
        d["decisions"].append({"id": 999, "text": "key sk_test_FAKE12345678 mail a.b@club.org password is hunter2",
                               "owner": "-", "date": "x", "evidence": "verified", "flags": []})
        text = pdf_text(report.render_pdf(d), config_tmp())
        for secret in ("sk_test_FAKE12345678", "a.b@club.org", "hunter2"):
            self.assertNotIn(secret, text)

    def test_markup_in_data_is_not_interpreted(self):
        self.ready()
        d = report.build_data("Riya", "Lead", "Karan")
        d["decisions"].append({"id": 998, "text": "<b>bold</b> & <font size=40>big</font> ₹ 5", "owner": "-", "date": "x",
                               "evidence": "verified", "flags": []})
        text = pdf_text(report.render_pdf(d), config_tmp())
        self.assertIn("<b>bold</b> &", text)

    def test_generation_is_audited_without_content(self):
        self.ready()
        report.generate("Aman", "Intern", "Karan")
        row = db.one("SELECT * FROM audit_log WHERE action='generate_report'")
        self.assertEqual(row["user_name"], "Aman")
        self.assertIn("person=Karan", row["detail"])
        self.assertNotIn("Karan will", row["detail"])


def config_tmp() -> str:
    import tempfile
    return tempfile.mktemp(suffix="rep")


if __name__ == "__main__":
    unittest.main()
