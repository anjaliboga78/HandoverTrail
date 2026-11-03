"""Twenty themes plus the Appearance options (accent, writing style, text size, density, item look, accessibility).

Everything is plain data: a theme is a dict of CSS variables. The CSS is generated here, and only from fixed
choices (never from user text), so nothing a person types can reach the stylesheet.

Preferences are saved per signed-in user in the workspace database (table `prefs`).
"""
from __future__ import annotations
import datetime as dt
import random

from . import db

# --------------------------------------------------------------------------- fonts
FONTS = {
    "Caveat": "'Caveat','Segoe Print','Comic Sans MS',cursive",
    "Lora": "'Lora',Georgia,'Times New Roman',serif",
    "Inter": "'Inter',system-ui,'Segoe UI',Roboto,Arial,sans-serif",
    "Kalam": "'Kalam','Caveat','Segoe Print',cursive",
    "Lexend": "'Lexend','Atkinson Hyperlegible',Verdana,sans-serif",
    "Nunito": "'Nunito','Inter',system-ui,sans-serif",
    "Space Grotesk": "'Space Grotesk','Inter',system-ui,sans-serif",
    "IBM Plex Mono": "'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace",
}
# Headings were designed for a tall handwriting font; other fonts need smaller sizes.
FONT_SCALE = {"Caveat": 1.0, "Kalam": 0.82, "Lora": 0.72, "Inter": 0.66, "Lexend": 0.64, "Nunito": 0.68,
              "Space Grotesk": 0.66, "IBM Plex Mono": 0.6}
FONT_IMPORT = ("https://fonts.googleapis.com/css2?family=Caveat:wght@600;700&family=Kalam:wght@400;700"
               "&family=Lora:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@400;600;700"
               "&family=Lexend:wght@400;600&family=Nunito:wght@400;600;700&family=Space+Grotesk:wght@500;700"
               "&family=IBM+Plex+Mono:wght@400;600&display=swap")

# --------------------------------------------------------------------------- base (= Notebook)
BASE = {
    "paper": "#fbf7ea", "paper2": "#f3ecd2", "line": "#e2d9b8", "card": "#fffef8", "ink": "#101046",
    "muted": "#4a4c70", "teal": "#24baa2", "tealD": "#0b7a68", "red": "#c0392b", "onacc": "#101046",
    "onred": "#fff", "dot": "#d6cca8", "hl": "#ffe066", "chipbg": "#fff", "numbg": "#fff",
    "yellow": "#fff0a6", "green": "#d6f2df", "blue": "#d3e6ff", "pink": "#ffd8df", "lav": "#e6dcff",
    "peach": "#ffe2cc", "lime": "#e6f1c6", "cyan": "#cdeef3",
    "btnbg": "var(--ink)", "btnfg": "#fff", "btnbd": "2px solid var(--ink)", "btnsh": "3px 3px 0 var(--teal)",
    "btnr": "10px", "cardr": "4px", "cardbd": "0 solid transparent", "cardsh": "4px 5px 0 rgba(16,16,70,.10)",
    "panelbd": "1.5px solid var(--line)", "panelsh": "3px 3px 0 var(--line)",
    "tiltk": "1", "tape": "1", "bgimg": "radial-gradient(var(--dot) 1.1px, transparent 1.3px)",
    "bgsize": "24px 24px", "marginc": "rgba(192,57,43,.38)", "padl": "4.2rem", "dst": "dashed",
    "sidebd": "2px dashed #cfc293", "hdeco": "underline wavy var(--red)", "lh": "1.5", "ls": "0",
}

ACCENTS = {  # name: (accent, darker accent for text on light themes)
    "teal": ("#24baa2", "#0b7a68"), "indigo": ("#6b63e8", "#4339b8"), "coral": ("#ee6a55", "#b43a27"),
    "green": ("#43a047", "#2a7330"), "amber": ("#e0a000", "#8a6200"),
}

_FLATTINT = {"yellow": "#fff9db", "green": "#e6f7ee", "blue": "#e8f1ff", "pink": "#ffeaf0", "lav": "#f0ebff",
             "peach": "#fff0e4", "lime": "#f0f7dc", "cyan": "#e3f5f8"}


THEMES = {
    "notebook": {"name": "Notebook", "desc": "Cream paper, sticky notes and handwriting, like your plan document.",
                 "hand": "Caveat", "body": "Lora", "dark": False, "flat": False, "vars": {}},
    "clean": {"name": "Clean", "desc": "Light, flat and quiet. Best for long reading and projectors.",
              "hand": "Inter", "body": "Inter", "dark": False, "flat": True,
              "vars": {**_FLATTINT, "paper": "#f6f7fb", "paper2": "#eceff6", "line": "#dfe2ec", "card": "#ffffff",
                       "ink": "#1b2340", "muted": "#5b6280", "teal": "#0f9a85", "tealD": "#0b7a68",
                       "red": "var(--tealD)", "btnbg": "var(--tealD)", "btnbd": "2px solid var(--tealD)",
                       "btnsh": "none", "btnr": "8px", "cardr": "10px", "cardbd": "1px solid var(--line)",
                       "cardsh": "0 1px 3px rgba(20,30,60,.08)", "panelsh": "0 1px 3px rgba(20,30,60,.08)",
                       "tiltk": "0", "tape": "0", "bgimg": "none", "marginc": "transparent", "padl": "2.2rem",
                       "dst": "solid", "sidebd": "1px solid var(--line)", "hdeco": "none"}},
    "midnight": {"name": "Midnight", "desc": "Dark navy with teal. Easy on the eyes at night.",
                 "hand": "Inter", "body": "Inter", "dark": True, "flat": True,
                 "vars": {"paper": "#0d0f2b", "paper2": "#12143a", "line": "#2b2e66", "card": "#1a1c45",
                          "ink": "#eef0ff", "muted": "#a5a9d6", "teal": "#2fe0c3", "tealD": "#2fe0c3",
                          "red": "#ff9a8a", "onacc": "#06122e", "onred": "#0d0f2b", "chipbg": "#262a63",
                          "numbg": "#1a1c45", "hl": "#6b5d00", "yellow": "#2d2b55", "green": "#1b3a46",
                          "blue": "#1f2d5e", "pink": "#402a4e", "lav": "#33295e", "peach": "#3b2f4d",
                          "lime": "#22404a", "cyan": "#1a3a52", "btnbg": "var(--teal)", "btnfg": "var(--onacc)",
                          "btnbd": "2px solid var(--teal)", "btnsh": "none", "btnr": "10px", "cardr": "10px",
                          "cardbd": "1px solid var(--line)", "cardsh": "none", "panelsh": "none",
                          "tiltk": "0", "tape": "0", "bgimg": "none", "marginc": "transparent", "padl": "2.2rem",
                          "dst": "solid", "sidebd": "1px solid var(--line)", "hdeco": "none"}},
    "chalkboard": {"name": "Chalkboard", "desc": "Green board with chalk writing. The playful one for demos.",
                   "hand": "Kalam", "body": "Kalam", "dark": True, "flat": False,
                   "vars": {"paper": "#24422f", "paper2": "#1d3626", "line": "rgba(255,255,255,.4)",
                            "card": "rgba(255,255,255,.05)", "ink": "#f3f1e6", "muted": "#cfd8c8", "teal": "#ffd25a",
                            "tealD": "#ffd25a", "red": "#ff9aa8", "onacc": "#24422f", "onred": "#24422f",
                            "chipbg": "rgba(255,255,255,.1)", "numbg": "rgba(255,255,255,.08)", "hl": "#7a6a10",
                            "yellow": "rgba(255,210,90,.14)", "green": "rgba(150,230,170,.14)",
                            "blue": "rgba(150,200,255,.14)", "pink": "rgba(255,150,170,.16)",
                            "lav": "rgba(200,170,255,.15)", "peach": "rgba(255,190,140,.15)",
                            "lime": "rgba(200,230,120,.14)", "cyan": "rgba(130,225,235,.14)",
                            "btnbg": "transparent", "btnfg": "var(--teal)", "btnbd": "2px dashed var(--teal)",
                            "btnsh": "none", "btnr": "12px", "cardr": "6px", "cardbd": "2px dashed rgba(255,255,255,.55)",
                            "cardsh": "none", "panelbd": "2px dashed rgba(255,255,255,.45)", "panelsh": "none",
                            "tape": "0", "bgimg": "radial-gradient(ellipse at 20% 8%, rgba(255,255,255,.07), transparent 55%)",
                            "bgsize": "auto", "marginc": "transparent", "padl": "2.2rem",
                            "sidebd": "2px dashed rgba(255,255,255,.35)", "hdeco": "underline dashed var(--teal)"}},
    "sunrise": {"name": "Sunrise", "desc": "Warm peach and coral. Friendly and bright.",
                "hand": "Nunito", "body": "Nunito", "dark": False, "flat": True,
                "vars": {"paper": "#fff1e3", "paper2": "#ffe4cc", "line": "#f6cfb4", "card": "#ffffff",
                         "ink": "#3a2018", "muted": "#7a5446", "teal": "#e5533d", "tealD": "#c2402c",
                         "red": "var(--tealD)", "yellow": "#fff3d6", "green": "#e8f6e4", "blue": "#e6f0fb",
                         "pink": "#ffe3e0", "lav": "#f3e8fb", "peach": "#ffe6d2", "lime": "#f0f5d6",
                         "cyan": "#def2f1", "btnbg": "var(--tealD)", "btnbd": "2px solid var(--tealD)",
                         "btnsh": "none", "btnr": "999px", "cardr": "14px", "cardbd": "1.5px solid var(--line)",
                         "cardsh": "0 4px 14px rgba(200,90,50,.12)", "panelsh": "0 4px 14px rgba(200,90,50,.12)",
                         "tiltk": "0", "tape": "0", "bgimg": "none", "marginc": "transparent", "padl": "2.2rem",
                         "dst": "solid", "sidebd": "1px solid var(--line)", "hdeco": "none"}},
    "ocean": {"name": "Ocean", "desc": "Cool blues. Calm for long review sessions.",
              "hand": "Nunito", "body": "Nunito", "dark": False, "flat": True,
              "vars": {"paper": "#eaf5fb", "paper2": "#d9edf7", "line": "#b9dcec", "card": "#ffffff",
                       "ink": "#0d2b3e", "muted": "#44667a", "teal": "#1d93b8", "tealD": "#0b6a8a",
                       "red": "var(--tealD)", "yellow": "#fff7dc", "green": "#e2f5ee", "blue": "#e0f0fb",
                       "pink": "#fde8ee", "lav": "#ece8fb", "peach": "#fdeee2", "lime": "#eef6dc",
                       "cyan": "#dcf3f6", "btnbg": "var(--tealD)", "btnbd": "2px solid var(--tealD)",
                       "btnsh": "none", "btnr": "8px", "cardr": "8px", "cardbd": "1.5px solid var(--line)",
                       "cardsh": "none", "panelsh": "none", "tiltk": "0", "tape": "0", "bgimg": "none",
                       "marginc": "transparent", "padl": "2.2rem", "dst": "solid",
                       "sidebd": "1px solid var(--line)", "hdeco": "none"}},
    "lavender": {"name": "Lavender", "desc": "Soft purple with rounded cards. Gentle and modern.",
                 "hand": "Nunito", "body": "Nunito", "dark": False, "flat": True,
                 "vars": {"paper": "#f3effc", "paper2": "#e8e0f8", "line": "#d7cbf0", "card": "#ffffff",
                          "ink": "#2a1f55", "muted": "#6a5f95", "teal": "#8a63e0", "tealD": "#6b46c9",
                          "red": "var(--tealD)", "yellow": "#fff6dc", "green": "#e6f6ee", "blue": "#e6eeff",
                          "pink": "#fde9f2", "lav": "#efe8ff", "peach": "#fdeee6", "lime": "#f0f6dd",
                          "cyan": "#e0f3f8", "btnbg": "var(--tealD)", "btnbd": "2px solid var(--tealD)",
                          "btnsh": "none", "btnr": "999px", "cardr": "18px", "cardbd": "1px solid var(--line)",
                          "cardsh": "0 6px 18px rgba(107,70,201,.14)", "panelsh": "0 6px 18px rgba(107,70,201,.14)",
                          "tiltk": "0", "tape": "0", "bgimg": "none", "marginc": "transparent", "padl": "2.2rem",
                          "dst": "solid", "sidebd": "1px solid var(--line)", "hdeco": "none"}},
    "easyread": {"name": "Easy read", "desc": "A very readable typeface with extra spacing. Easier on tired eyes.",
                 "hand": "Lexend", "body": "Lexend", "dark": False, "flat": True,
                 "vars": {"paper": "#f9f4ea", "paper2": "#f0e9d9", "line": "#ded3bc", "card": "#fffdf8",
                          "ink": "#1d1d1b", "muted": "#4a4a45", "teal": "#2b6cb0", "tealD": "#1f5a96",
                          "red": "var(--tealD)", "yellow": "#fff8e0", "green": "#e8f5ea", "blue": "#e7f0fa",
                          "pink": "#fbebee", "lav": "#efeafa", "peach": "#fbeee2", "lime": "#f0f5df",
                          "cyan": "#e1f2f4", "btnbg": "var(--tealD)", "btnbd": "2px solid var(--tealD)",
                          "btnsh": "none", "btnr": "6px", "cardr": "4px", "cardbd": "1.5px solid var(--line)",
                          "cardsh": "none", "panelsh": "none", "tiltk": "0", "tape": "0", "bgimg": "none",
                          "marginc": "transparent", "padl": "2.2rem", "dst": "solid",
                          "sidebd": "1px solid var(--line)", "hdeco": "none", "lh": "1.85", "ls": ".02em"}},
    "trailmap": {"name": "Trail map", "desc": "Parchment with contour lines and a dotted trail. Fits the name.",
                 "hand": "Lora", "body": "Lora", "dark": False, "flat": False,
                 "vars": {"paper": "#efe3c8", "paper2": "#e4d4b0", "line": "#cdb88a", "card": "#fbf3df",
                          "ink": "#3a2a12", "muted": "#6b5535", "teal": "#4a7c3a", "tealD": "#2f5d2a",
                          "red": "#c2631f", "onacc": "#f7efd8", "yellow": "#fbf0c8", "green": "#e2efd2",
                          "blue": "#dfe9ee", "pink": "#f6dcd0", "lav": "#e9e2ea", "peach": "#f7e0c4",
                          "lime": "#e8efc6", "cyan": "#dae8dd", "btnbg": "var(--tealD)", "btnfg": "#f7efd8",
                          "btnbd": "2px solid var(--tealD)", "btnsh": "2px 2px 0 rgba(58,42,18,.35)",
                          "btnr": "8px", "cardr": "6px", "cardbd": "1.5px solid var(--line)",
                          "cardsh": "2px 3px 0 rgba(58,42,18,.14)", "tiltk": ".5", "tape": "0",
                          "bgimg": ("repeating-radial-gradient(circle at 82% 18%, transparent 0 26px, rgba(140,110,60,.2) 27px 28px),"
                                    "repeating-radial-gradient(circle at 8% 88%, transparent 0 34px, rgba(140,110,60,.16) 35px 36px)"),
                          "bgsize": "auto", "marginc": "transparent", "padl": "2.2rem", "sidebd": "2px solid var(--line)",
                          "hdeco": "underline dotted var(--red)"}},
    "blueprint": {"name": "Blueprint", "desc": "Blue drawing paper with white grid lines. For the builder in you.",
                  "hand": "IBM Plex Mono", "body": "IBM Plex Mono", "dark": True, "flat": False,
                  "vars": {"paper": "#123a73", "paper2": "#0e2e5c", "line": "rgba(255,255,255,.55)",
                           "card": "rgba(255,255,255,.04)", "ink": "#eaf4ff", "muted": "#a9c4e6", "teal": "#7fe3ff",
                           "tealD": "#7fe3ff", "red": "#ffd36b", "onacc": "#0e2e5c", "onred": "#0e2e5c",
                           "chipbg": "rgba(255,255,255,.1)", "numbg": "rgba(255,255,255,.06)", "hl": "#2b5da8",
                           "yellow": "rgba(255,255,255,.05)", "green": "rgba(127,227,255,.08)",
                           "blue": "rgba(255,255,255,.08)", "pink": "rgba(255,211,107,.09)",
                           "lav": "rgba(200,190,255,.09)", "peach": "rgba(255,190,140,.09)",
                           "lime": "rgba(190,255,190,.08)", "cyan": "rgba(127,227,255,.1)",
                           "btnbg": "transparent", "btnfg": "var(--teal)", "btnbd": "1.5px solid var(--teal)",
                           "btnsh": "none", "btnr": "0", "cardr": "0", "cardbd": "1.5px solid rgba(255,255,255,.7)",
                           "cardsh": "none", "panelbd": "1.5px solid rgba(255,255,255,.6)", "panelsh": "none",
                           "tiltk": "0", "tape": "0", "bgimg": ("linear-gradient(rgba(255,255,255,.08) 1px, transparent 1px),"
                                                                 "linear-gradient(90deg, rgba(255,255,255,.08) 1px, transparent 1px)"),
                           "bgsize": "24px 24px", "marginc": "transparent", "padl": "2.2rem", "dst": "solid",
                           "sidebd": "1px solid rgba(255,255,255,.5)", "hdeco": "none"}},
    "pop": {"name": "Pop", "desc": "Bold colours, thick outlines, hard shadows. Loud and fun.",
            "hand": "Space Grotesk", "body": "Space Grotesk", "dark": False, "flat": False,
            "vars": {"paper": "#ffe24d", "paper2": "#ffd21f", "line": "#000", "card": "#ffffff", "ink": "#000",
                     "muted": "#222", "teal": "#ff5fa2", "tealD": "#d6307c", "red": "#d6307c", "onacc": "#000",
                     "dot": "#e6b800", "yellow": "#ffffff", "green": "#b6f2c6", "blue": "#bcd7ff",
                     "pink": "#ffb3d1", "lav": "#d9c7ff", "peach": "#ffc89a", "lime": "#d8f27a", "cyan": "#a8ecf5",
                     "btnbg": "var(--teal)", "btnfg": "#000", "btnbd": "3px solid #000", "btnsh": "4px 4px 0 #000",
                     "btnr": "12px", "cardr": "12px", "cardbd": "3px solid #000", "cardsh": "5px 5px 0 #000",
                     "panelbd": "3px solid #000", "panelsh": "5px 5px 0 #000", "tiltk": ".6", "tape": "0",
                     "bgimg": "none", "marginc": "transparent", "padl": "2.2rem", "dst": "solid",
                     "sidebd": "3px solid #000", "hdeco": "none"}},
    "terminal": {"name": "Terminal", "desc": "Green text on black, like a command line. For developers.",
                 "hand": "IBM Plex Mono", "body": "IBM Plex Mono", "dark": True, "flat": True,
                 "vars": {"paper": "#050a05", "paper2": "#0a120a", "line": "#1f4d28", "card": "#0a140a",
                          "ink": "#8dff9b", "muted": "#5fbf6f", "teal": "#8dff9b", "tealD": "#8dff9b",
                          "red": "#ffb454", "onacc": "#04100a", "onred": "#04100a", "chipbg": "#0f2412",
                          "numbg": "#0a140a", "hl": "#1d5a28", "yellow": "#141a07", "green": "#0a1a0d",
                          "blue": "#08151c", "pink": "#1a0d12", "lav": "#120d1c", "peach": "#1a1207",
                          "lime": "#101a07", "cyan": "#07171a", "btnbg": "var(--teal)", "btnfg": "var(--onacc)",
                          "btnbd": "1px solid var(--teal)", "btnsh": "none", "btnr": "0", "cardr": "0",
                          "cardbd": "1px solid var(--line)", "cardsh": "none", "panelsh": "none",
                          "tiltk": "0", "tape": "0", "bgimg": "none", "marginc": "transparent", "padl": "2.2rem",
                          "dst": "solid", "sidebd": "1px solid var(--line)", "hdeco": "none"}},

    "forest": {"name": "Forest", "desc": "Mossy greens and warm paper. Calm, like a walk on the trail.",
               "hand": "Lora", "body": "Lora", "dark": False, "flat": True,
               "vars": {**_FLATTINT, "paper": "#eaf2e4", "paper2": "#dbe9d2", "line": "#bdd3b0", "card": "#fbfdf8",
                        "ink": "#17301f", "muted": "#43624c", "teal": "#3f8f55", "tealD": "#276b3b",
                        "red": "var(--tealD)", "btnbg": "var(--tealD)", "btnbd": "2px solid var(--tealD)",
                        "btnsh": "2px 2px 0 rgba(23,48,31,.25)", "btnr": "8px", "cardr": "10px",
                        "cardbd": "1.5px solid var(--line)", "cardsh": "0 2px 6px rgba(23,48,31,.08)",
                        "panelsh": "0 2px 6px rgba(23,48,31,.08)", "tiltk": "0", "tape": "0", "bgimg": "none",
                        "marginc": "transparent", "padl": "2.2rem", "dst": "solid",
                        "sidebd": "1px solid var(--line)", "hdeco": "none"}},
    "sakura": {"name": "Sakura", "desc": "Soft blossom pink with rounded shapes. Light and cheerful.",
               "hand": "Nunito", "body": "Nunito", "dark": False, "flat": True,
               "vars": {"paper": "#fff0f4", "paper2": "#ffe0e8", "line": "#f6c6d3", "card": "#ffffff",
                        "ink": "#4a1d2f", "muted": "#8a5468", "teal": "#e0507c", "tealD": "#b8305a",
                        "red": "var(--tealD)", "yellow": "#fff4d9", "green": "#e8f6ec", "blue": "#e8f0fc",
                        "pink": "#ffe1ea", "lav": "#f2e8fb", "peach": "#ffe8dc", "lime": "#f1f6dc",
                        "cyan": "#e0f3f6", "btnbg": "var(--tealD)", "btnbd": "2px solid var(--tealD)",
                        "btnsh": "none", "btnr": "999px", "cardr": "16px", "cardbd": "1.5px solid var(--line)",
                        "cardsh": "0 5px 16px rgba(184,48,90,.12)", "panelsh": "0 5px 16px rgba(184,48,90,.12)",
                        "tiltk": "0", "tape": "0", "bgimg": "none", "marginc": "transparent", "padl": "2.2rem",
                        "dst": "solid", "sidebd": "1px solid var(--line)", "hdeco": "none"}},
    "coffee": {"name": "Coffee", "desc": "Latte cream and espresso brown. Warm and cosy.",
               "hand": "Lora", "body": "Lora", "dark": False, "flat": True,
               "vars": {"paper": "#f3e9dc", "paper2": "#e8d8c3", "line": "#d3bda0", "card": "#fffaf2",
                        "ink": "#35210f", "muted": "#6d5239", "teal": "#a8663a", "tealD": "#8a4e26",
                        "red": "var(--tealD)", "yellow": "#fbefcf", "green": "#e6efd9", "blue": "#e3ebf0",
                        "pink": "#f5ddd3", "lav": "#ebe3ea", "peach": "#f6e0c8", "lime": "#eaf0cc",
                        "cyan": "#dde9e4", "btnbg": "var(--tealD)", "btnbd": "2px solid var(--tealD)",
                        "btnsh": "2px 2px 0 rgba(53,33,15,.3)", "btnr": "8px", "cardr": "8px",
                        "cardbd": "1.5px solid var(--line)", "cardsh": "0 2px 6px rgba(53,33,15,.1)",
                        "panelsh": "0 2px 6px rgba(53,33,15,.1)", "tiltk": "0", "tape": "0", "bgimg": "none",
                        "marginc": "transparent", "padl": "2.2rem", "dst": "solid",
                        "sidebd": "1px solid var(--line)", "hdeco": "none"}},
    "mint": {"name": "Mint", "desc": "Fresh white and mint. Crisp and modern.",
             "hand": "Lexend", "body": "Lexend", "dark": False, "flat": True,
             "vars": {**_FLATTINT, "paper": "#effaf6", "paper2": "#dcf3ea", "line": "#bfe5d6", "card": "#ffffff",
                      "ink": "#0f2e27", "muted": "#3f6a5e", "teal": "#16a384", "tealD": "#0b7a62",
                      "red": "var(--tealD)", "btnbg": "var(--tealD)", "btnbd": "2px solid var(--tealD)",
                      "btnsh": "none", "btnr": "10px", "cardr": "12px", "cardbd": "1.5px solid var(--line)",
                      "cardsh": "0 3px 10px rgba(11,122,98,.08)", "panelsh": "0 3px 10px rgba(11,122,98,.08)",
                      "tiltk": "0", "tape": "0", "bgimg": "none", "marginc": "transparent", "padl": "2.2rem",
                      "dst": "solid", "sidebd": "1px solid var(--line)", "hdeco": "none"}},
    "newsprint": {"name": "Newsprint", "desc": "Black ink on newspaper white with thin rules. Serious and editorial.",
                  "hand": "Lora", "body": "Lora", "dark": False, "flat": True,
                  "vars": {"paper": "#f7f5f0", "paper2": "#ebe8e0", "line": "#bdb8ab", "card": "#ffffff",
                           "ink": "#111111", "muted": "#4d4a43", "teal": "#b3261e", "tealD": "#a01f18",
                           "red": "#a01f18", "yellow": "#f4f0e2", "green": "#eef1e8", "blue": "#eceff2",
                           "pink": "#f3ebe8", "lav": "#efecf0", "peach": "#f3ece3", "lime": "#eff0e2",
                           "cyan": "#e9eeed", "btnbg": "var(--ink)", "btnbd": "1.5px solid var(--ink)",
                           "btnsh": "none", "btnr": "0", "cardr": "0", "cardbd": "1px solid var(--ink)",
                           "cardsh": "none", "panelbd": "1px solid var(--ink)", "panelsh": "none",
                           "tiltk": "0", "tape": "0", "bgimg": "none", "marginc": "transparent", "padl": "2.2rem",
                           "dst": "solid", "sidebd": "1px solid var(--ink)", "hdeco": "none"}},
    "graphite": {"name": "Graphite", "desc": "Neutral dark grey with an amber glow. Focused and distraction-free.",
                 "hand": "Inter", "body": "Inter", "dark": True, "flat": True,
                 "vars": {"paper": "#17181b", "paper2": "#1f2024", "line": "#34363c", "card": "#232529",
                          "ink": "#ececee", "muted": "#a2a4ab", "teal": "#ffb454", "tealD": "#ffb454",
                          "red": "#ffb454", "onacc": "#1a1206", "onred": "#1a1206", "chipbg": "#2d2f35",
                          "numbg": "#232529", "hl": "#6b4d10", "yellow": "#2f2b1d", "green": "#1f2e26",
                          "blue": "#1f2a3a", "pink": "#38262c", "lav": "#2c2638", "peach": "#382b21",
                          "lime": "#272e1c", "cyan": "#1c2e33", "btnbg": "var(--teal)", "btnfg": "var(--onacc)",
                          "btnbd": "2px solid var(--teal)", "btnsh": "none", "btnr": "8px", "cardr": "8px",
                          "cardbd": "1px solid var(--line)", "cardsh": "none", "panelsh": "none",
                          "tiltk": "0", "tape": "0", "bgimg": "none", "marginc": "transparent", "padl": "2.2rem",
                          "dst": "solid", "sidebd": "1px solid var(--line)", "hdeco": "none"}},
    "synthwave": {"name": "Synthwave", "desc": "Night-city purple with neon pink and cyan. Bold and glowing.",
                  "hand": "Space Grotesk", "body": "Space Grotesk", "dark": True, "flat": True,
                  "vars": {"paper": "#1a1033", "paper2": "#22153f", "line": "#4a2f7a", "card": "#2a1a4d",
                           "ink": "#f6ecff", "muted": "#c3add9", "teal": "#ff4fd8", "tealD": "#ff4fd8",
                           "red": "#4df3ff", "onacc": "#1a0a2e", "onred": "#1a0a2e", "chipbg": "#38235f",
                           "numbg": "#2a1a4d", "hl": "#6a2a7a", "yellow": "#3a2a5c", "green": "#1d3a52",
                           "blue": "#26306a", "pink": "#4b2160", "lav": "#3b2a7a", "peach": "#4a2a5a",
                           "lime": "#1f3a5a", "cyan": "#18405a", "btnbg": "var(--teal)", "btnfg": "var(--onacc)",
                           "btnbd": "2px solid var(--teal)", "btnsh": "0 0 14px rgba(255,79,216,.55)",
                           "btnr": "10px", "cardr": "10px", "cardbd": "1px solid var(--line)",
                           "cardsh": "0 0 0 1px rgba(77,243,255,.15)", "panelsh": "0 0 18px rgba(255,79,216,.2)",
                           "tiltk": "0", "tape": "0",
                           "bgimg": "linear-gradient(180deg, transparent 60%, rgba(255,79,216,.12) 100%)",
                           "bgsize": "auto", "marginc": "transparent", "padl": "2.2rem", "dst": "solid",
                           "sidebd": "1px solid var(--line)", "hdeco": "none"}},
    "aurora": {"name": "Aurora", "desc": "Deep teal night with green and violet light. Quiet and a little magical.",
               "hand": "Nunito", "body": "Nunito", "dark": True, "flat": True,
               "vars": {"paper": "#0b1d2a", "paper2": "#10293a", "line": "#25506a", "card": "#143246",
                        "ink": "#e8f7f4", "muted": "#9fc4c4", "teal": "#5df0b5", "tealD": "#5df0b5",
                        "red": "#b9a3ff", "onacc": "#062018", "onred": "#0b1d2a", "chipbg": "#1b4259",
                        "numbg": "#143246", "hl": "#2a6a5a", "yellow": "#2a3d3a", "green": "#14463f",
                        "blue": "#173e63", "pink": "#3b3560", "lav": "#2e3a6e", "peach": "#33403f",
                        "lime": "#1b4a3d", "cyan": "#124a5a", "btnbg": "var(--teal)", "btnfg": "var(--onacc)",
                        "btnbd": "2px solid var(--teal)", "btnsh": "none", "btnr": "999px", "cardr": "14px",
                        "cardbd": "1px solid var(--line)", "cardsh": "none", "panelsh": "none",
                        "tiltk": "0", "tape": "0",
                        "bgimg": ("radial-gradient(ellipse at 15% 0%, rgba(93,240,181,.16), transparent 55%),"
                                  "radial-gradient(ellipse at 90% 10%, rgba(185,163,255,.16), transparent 50%)"),
                        "bgsize": "auto", "marginc": "transparent", "padl": "2.2rem", "dst": "solid",
                        "sidebd": "1px solid var(--line)", "hdeco": "none"}},
}
THEME_ORDER = list(THEMES)

# Theme-only extras. "@S" is replaced by the selector the theme applies to (the whole app, or one preview tile).
EXTRA = {
    "chalkboard": "@S{box-shadow:inset 0 0 0 9px #a9794b, inset 0 0 0 11px #7a5632;}",
    "blueprint": ("@S h1,@S h2,@S h3,@S .step,@S .stButton>button p,@S .tp-brand,@S .tp-btn"
                  "{text-transform:uppercase;letter-spacing:.06em;}"),
    "terminal": ("@S h1,@S h2,@S h3,@S .hero h1{text-shadow:0 0 8px rgba(141,255,155,.45);}"
                 "@S .hero h1:after{content:'\\2588';margin-left:6px;animation:htblink 1s steps(2) infinite;}"
                 "@keyframes htblink{50%{opacity:0}}"),
    "pop": "@S .hero h1,@S h2{text-shadow:2px 2px 0 rgba(0,0,0,.18);}",
    "synthwave": ("@S h1,@S h2,@S h3,@S .hero h1{text-shadow:0 0 10px rgba(255,79,216,.55);}"
                  "@S h1,@S h2,@S .step,@S .tp-brand{text-transform:uppercase;letter-spacing:.05em;}"),
    "newsprint": ("@S h1,@S h2,@S .tp-brand{font-weight:700;letter-spacing:-.01em;}"
                  "@S .hero{border-top:4px double var(--ink);border-bottom:4px double var(--ink);}"),
}

# --------------------------------------------------------------------------- preferences
DEFAULTS = {"theme": "notebook", "accent": "theme", "writing": "theme", "size": "m", "density": "cozy",
            "items": "theme", "contrast": "0", "motion": "0", "dots": "1", "auto_night": "0", "splash": "1"}
CHOICES = {"theme": set(THEMES), "accent": {"theme", *ACCENTS}, "writing": {"theme", "handwritten", "classic", "simple"},
           "size": {"s", "m", "l"}, "density": {"cozy", "compact"}, "items": {"theme", "sticky", "flat"},
           "contrast": {"0", "1"}, "motion": {"0", "1"}, "dots": {"0", "1"}, "auto_night": {"0", "1"},
           "splash": {"0", "1"}}


def get_prefs(user: str) -> dict:
    p = dict(DEFAULTS)
    for r in db.q("SELECT key, value FROM prefs WHERE user_name=?", (user,)):
        if r["key"] in CHOICES and r["value"] in CHOICES[r["key"]]:
            p[r["key"]] = r["value"]
    return p


def set_pref(user: str, key: str, value) -> bool:
    """Save one choice. Returns True if it changed. Unknown keys or values are rejected."""
    value = "1" if value is True else "0" if value is False else str(value)
    if key not in CHOICES or value not in CHOICES[key]:
        raise ValueError(f"Unknown appearance choice: {key}={value}")
    if get_prefs(user)[key] == value:
        return False
    db.x("INSERT INTO prefs(user_name,key,value) VALUES (?,?,?) ON CONFLICT(user_name,key) DO UPDATE SET value=excluded.value",
         (user, key, value))
    return True


def reset_prefs(user: str) -> None:
    db.x("DELETE FROM prefs WHERE user_name=?", (user,))


def surprise(user: str) -> str:
    cur = get_prefs(user)["theme"]
    pick = random.choice([k for k in THEME_ORDER if k != cur])
    set_pref(user, "theme", pick)
    return pick


def effective_theme(prefs: dict, now: dt.datetime | None = None) -> str:
    """Midnight after 7 pm and before 6 am if the person turned on auto night."""
    if prefs.get("auto_night") == "1":
        h = (now or dt.datetime.now()).hour
        if h >= 19 or h < 6:
            return "midnight"
    return prefs["theme"]


# --------------------------------------------------------------------------- CSS generation
def _decl(v: dict) -> str:
    return ";".join(f"--{k}:{val}" for k, val in v.items())


def _fonts(v: dict, hand: str, body: str) -> dict:
    v = dict(v)
    v["hand"], v["serif"] = FONTS[hand], FONTS[body]
    v["hs"] = str(FONT_SCALE[hand])
    return v


def theme_vars(key: str, accent: str = "theme") -> tuple:
    t = THEMES[key]
    v = {**BASE, **t["vars"]}
    v = _fonts(v, t["hand"], t["body"])
    if accent in ACCENTS:
        a, ad = ACCENTS[accent]
        v["teal"], v["tealD"] = a, (a if t["dark"] else ad)
    return v, t


FLAT = ("@S .card{background:var(--card);border:1.5px solid var(--line);border-left:7px solid var(--bg);box-shadow:none;}"
        "@S .plancol{background:var(--card);border:1.5px solid var(--line);border-top:6px solid var(--bg);box-shadow:none;}"
        "@S .sn{background:var(--card);border:1.5px solid var(--line);border-left:7px solid var(--bg);box-shadow:none;}"
        "@S .card:before,@S .plancol:before{display:none;}")


def scoped_css(sel: str, v: dict, theme_key: str, flat: bool) -> str:
    out = f"{sel}{{{_decl(v)}}}"
    if flat:
        out += FLAT.replace("@S", sel)
    out += EXTRA.get(theme_key, "").replace("@S", sel)
    return out


def css_for(prefs: dict, now: dt.datetime | None = None) -> str:
    """The <style> block for the live app: theme + the person's choices."""
    key = effective_theme(prefs, now)
    v, t = theme_vars(key, prefs["accent"])
    if prefs["writing"] != "theme":
        hand, body = {"handwritten": ("Caveat", "Lora"), "classic": ("Lora", "Lora"), "simple": ("Inter", "Inter")}[prefs["writing"]]
        v = _fonts(v, hand, body)
    if prefs["contrast"] == "1":
        v.update({"muted": "var(--ink)", "line": "var(--ink)", "cardbd": "2px solid var(--ink)", "panelbd": "2px solid var(--ink)"})
    if prefs["motion"] == "1":
        v["tiltk"] = "0"
    if prefs["dots"] == "0":
        v["bgimg"] = "none"
    flat = {"flat": True, "sticky": False}.get(prefs["items"], t["flat"])
    if prefs["items"] == "sticky" and t["flat"]:
        v.update({"tiltk": "1", "tape": "1", "cardsh": "3px 4px 0 rgba(0,0,0,.12)"})
    if prefs["items"] == "flat":
        v.update({"tiltk": "0", "tape": "0"})
    css = scoped_css(".stApp", v, key, flat)
    css += "html{font-size:%dpx;}" % {"s": 14, "m": 16, "l": 18}[prefs["size"]]
    if prefs["density"] == "compact":
        css += (".stApp .block-container{padding-top:1rem;padding-bottom:1.5rem;}.stApp .card{padding:10px 14px 6px;margin:10px 0 8px;}"
                ".stApp .planline{padding:5px 6px 5px 32px;}.stApp .hero{padding:12px 20px;margin:6px 0 16px;}"
                ".stApp .stepper{margin-bottom:14px;}.stApp .sn{padding:7px 11px 5px;margin:7px 0 3px;}"
                ".stApp [data-testid='stVerticalBlock']{gap:.55rem;}")
    if prefs["motion"] == "1":
        css += ("*{transition:none!important;animation:none!important;}.hero .mark,.side-logo,.nametag,.start,"
                ".hero .who,[data-testid='stMetric']{transform:none!important;}")
    if prefs["contrast"] == "1":
        css += (".stApp .chip{border-color:var(--ink)!important;border-width:2px;}"
                ".stApp p,.stApp li,.stApp label{font-weight:600;}")
    return f"<style>{css}</style>"


def gallery_css() -> str:
    """One scoped block per theme, so the preview tiles in the studio look like the real thing."""
    out = []
    for key, t in THEMES.items():
        v, _ = theme_vars(key)
        out.append(scoped_css(f".tp.th-{key}", v, key, t["flat"]))
    return "<style>" + "".join(out) + "</style>"
