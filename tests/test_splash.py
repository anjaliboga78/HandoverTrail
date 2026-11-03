"""Start-up screen: pure CSS, once per session, skippable, off when motion is reduced."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import splash
from core import themes


class TestSplash(unittest.TestCase):
    def test_markup_has_the_scenes_but_no_sticky_notes_and_no_script(self):
        m = splash.markup()
        for part in ("sp-orb", "sp-dot", "sp-letters", "sp-logo", "Meeting notes", "GitHub", "<summary"):
            self.assertIn(part, m)
        self.assertNotIn("sp-notes", m)
        self.assertNotIn("spSlap ", splash.CSS)
        self.assertNotIn("<script", m.lower())
        self.assertEqual(m.count("sp-chip' style"), 4)
        self.assertEqual(m.count("<i class='sp-dot'"), 5)
        self.assertEqual(m.count("<span"), len(splash.WORD))
        self.assertEqual(m.count("{"), m.count("}"))

    def test_total_length_is_between_six_and_seven_seconds(self):
        self.assertTrue(6 <= splash.TOTAL_SECONDS <= 7)
        self.assertIn("spOut .5s 6s", splash.CSS)   # overlay starts fading at 6 s
        self.assertLessEqual(6 + .5, splash.TOTAL_SECONDS + .1)

    def test_logo_and_tagline_arrive_before_the_screen_fades(self):
        # logo lands at 4.3 s (0.55 s long), tagline at 5 s (0.6 s long), both well before the fade at 6 s
        self.assertIn("spSlap2 .55s 4.3s", splash.CSS)
        self.assertIn("spIn .6s 5s", splash.CSS)
        self.assertLess(4.3 + .55, 6)
        self.assertLess(5 + .6, 6)

    def test_motion_off_returns_nothing(self):
        self.assertEqual(splash.markup(user_motion_off=True), "")

    def test_preference_is_valid_and_saved(self):
        self.assertEqual(themes.DEFAULTS["splash"], "1")
        self.assertEqual(themes.CHOICES["splash"], {"0", "1"})
        with self.assertRaises(ValueError):
            themes.set_pref("Riya", "splash", "maybe")


if __name__ == "__main__":
    unittest.main()
