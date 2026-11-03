"""Themes and Appearance choices: data is complete, saved per person, and can never inject CSS."""
import datetime as dt
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db, themes


def fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    db.use_path(path)
    db.init()


class TestThemes(unittest.TestCase):
    def setUp(self):
        fresh_db()

    def test_twenty_themes_in_the_planned_order(self):
        self.assertEqual([themes.THEMES[k]["name"] for k in themes.THEME_ORDER],
                         ["Notebook", "Clean", "Midnight", "Chalkboard", "Sunrise", "Ocean", "Lavender",
                          "Easy read", "Trail map", "Blueprint", "Pop", "Terminal",
                          "Forest", "Sakura", "Coffee", "Mint", "Newsprint", "Graphite", "Synthwave", "Aurora"])

    def test_every_theme_defines_every_variable_it_overrides_and_builds_css(self):
        for key in themes.THEME_ORDER:
            for acc in ["theme", *themes.ACCENTS]:
                v, _ = themes.theme_vars(key, acc)
                self.assertTrue(set(themes.BASE) <= set(v), key)
                self.assertIn(v["hand"], themes.FONTS.values())
            p = dict(themes.DEFAULTS, theme=key)
            css = themes.css_for(p)
            self.assertTrue(css.startswith("<style>") and css.endswith("</style>"))
            self.assertEqual(css.count("{"), css.count("}"), key)
        self.assertEqual(themes.gallery_css().count("{"), themes.gallery_css().count("}"))

    def test_choices_are_saved_per_person(self):
        self.assertTrue(themes.set_pref("Riya", "theme", "midnight"))
        self.assertFalse(themes.set_pref("Riya", "theme", "midnight"))
        self.assertEqual(themes.get_prefs("Riya")["theme"], "midnight")
        self.assertEqual(themes.get_prefs("Aman")["theme"], "notebook")
        themes.set_pref("Riya", "contrast", True)
        self.assertEqual(themes.get_prefs("Riya")["contrast"], "1")
        themes.reset_prefs("Riya")
        self.assertEqual(themes.get_prefs("Riya"), themes.DEFAULTS)

    def test_unknown_values_are_rejected_so_nothing_can_reach_the_stylesheet(self):
        for key, val in [("theme", "x;}body{display:none"), ("accent", "#fff"), ("nope", "1"), ("size", "xl")]:
            with self.assertRaises(ValueError):
                themes.set_pref("Riya", key, val)
        db.x("INSERT INTO prefs(user_name,key,value) VALUES ('Riya','theme','evil}')")
        self.assertEqual(themes.get_prefs("Riya")["theme"], "notebook")

    def test_options_change_the_output(self):
        base = themes.css_for(dict(themes.DEFAULTS))
        self.assertIn("font-size:18px", themes.css_for(dict(themes.DEFAULTS, size="l")))
        self.assertIn("font-size:14px", themes.css_for(dict(themes.DEFAULTS, size="s")))
        self.assertNotEqual(base, themes.css_for(dict(themes.DEFAULTS, accent="coral")))
        self.assertIn("#ee6a55", themes.css_for(dict(themes.DEFAULTS, accent="coral")))
        self.assertIn("--bgimg:none", themes.css_for(dict(themes.DEFAULTS, dots="0")))
        self.assertIn("--tiltk:0", themes.css_for(dict(themes.DEFAULTS, motion="1")))
        self.assertIn("animation:none", themes.css_for(dict(themes.DEFAULTS, motion="1")))
        self.assertIn("border-left:7px", themes.css_for(dict(themes.DEFAULTS, items="flat")))
        self.assertNotIn("border-left:7px", base)
        self.assertIn("--hand:'Inter'", themes.css_for(dict(themes.DEFAULTS, writing="simple")))
        self.assertIn(".stApp .card{padding:10px", themes.css_for(dict(themes.DEFAULTS, density="compact")))

    def test_auto_night_switches_to_midnight(self):
        p = dict(themes.DEFAULTS, auto_night="1")
        self.assertEqual(themes.effective_theme(p, dt.datetime(2026, 11, 3, 21, 0)), "midnight")
        self.assertEqual(themes.effective_theme(p, dt.datetime(2026, 11, 3, 3, 0)), "midnight")
        self.assertEqual(themes.effective_theme(p, dt.datetime(2026, 11, 3, 12, 0)), "notebook")
        self.assertEqual(themes.effective_theme(dict(themes.DEFAULTS), dt.datetime(2026, 11, 3, 22, 0)), "notebook")

    def test_surprise_picks_a_different_theme(self):
        self.assertNotEqual(themes.surprise("Riya"), "notebook")


if __name__ == "__main__":
    unittest.main()
