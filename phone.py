"""HandoverTrail phone app mode: a native-app style UI that follows the 18-screen app-flow design.

Opened automatically on phones (?view=phone). It reuses the same database and core logic as the laptop view, so nothing
about the data, roles, the Evidence Gate or the exports changes. Screens: welcome, choose account, home dashboard,
sources, add source, reconstruct, verification, conflicts, item details, handover report, transfer, checklist,
audit log, notifications, profile and settings, appearance, my notes, menu.

The default look ("Showcase") is lavender with indigo buttons and pastel tiles. Other themes: Midnight, Ocean,
Graphite, Daylight, Mint, Sunset, Minimal, Minimal dark, Mono, plus Light / Dark / System and accent colours.
"""

from __future__ import annotations

import difflib
import re
from collections import Counter

import streamlit as st

import splash
import ui
from core import checklist, config, db, extract, flags, handover, ingest, notes, readiness, report, themes, transfer
from ui import STATUS_TEXT, type_label

WELCOME = True  # set to False to skip the welcome screen and open on "Choose your account"

# ------------------------------------------------------------------ themes

THEMES = {
    "showcase": dict(name="Showcase", dark=False, bg="#f4f3ff", surface="#ffffff", surface2="#eeedfc", border="#e4e2f7",
                     text="#1b1b3a", muted="#6b6f93", accent="#4f46e5", on="#ffffff", good="#22c55e", warn="#f59e0b", bad="#ef4444"),
    "midnight": dict(name="Midnight", dark=True, bg="#0e1020", surface="#171a2e", surface2="#20243d", border="#2b3050",
                     text="#f2f3fa", muted="#9aa0bf", accent="#6c63ff", on="#ffffff", good="#34d399", warn="#f5a524", bad="#f0556b"),
    "ocean": dict(name="Ocean", dark=True, bg="#07161f", surface="#0d2430", surface2="#143242", border="#1c4156",
                  text="#eaf6fb", muted="#8fb3c4", accent="#22b8cf", on="#04202a", good="#3ddc97", warn="#f5b041", bad="#ff6b6b"),
    "graphite": dict(name="Graphite", dark=True, bg="#121212", surface="#1c1c1e", surface2="#2a2a2d", border="#38383c",
                     text="#f5f5f7", muted="#9a9aa1", accent="#ffb020", on="#1a1200", good="#4ade80", warn="#fbbf24", bad="#f87171"),
    "daylight": dict(name="Daylight", dark=False, bg="#f5f6fb", surface="#ffffff", surface2="#eef0f8", border="#dfe2ef",
                     text="#171a2e", muted="#6b7190", accent="#5b53f0", on="#ffffff", good="#16a37a", warn="#d98a0b", bad="#d93a4f"),
    "mint": dict(name="Mint", dark=False, bg="#f1faf6", surface="#ffffff", surface2="#e4f4ec", border="#cfe8dc",
                 text="#10291f", muted="#5f7f70", accent="#12a36b", on="#ffffff", good="#12a36b", warn="#cf8a0a", bad="#d6453d"),
    "sunset": dict(name="Sunset", dark=False, bg="#fff6ef", surface="#ffffff", surface2="#ffebdc", border="#f6d7c1",
                   text="#2b1810", muted="#8a6a58", accent="#f0613c", on="#ffffff", good="#1f9d6b", warn="#c98400", bad="#d0334a"),
    "minimal": dict(name="Minimal", dark=False, bg="#ffffff", surface="#f5f7fa", surface2="#eceff4", border="#e3e7ed",
                    text="#101046", muted="#6b7090", accent="#24baa2", on="#06122e", good="#16a37a", warn="#d98a0b", bad="#d93a4f"),
    "minimal_dark": dict(name="Minimal dark", dark=True, bg="#0f1226", surface="#181c38", surface2="#20243d", border="#272c4f",
                         text="#f1f3ff", muted="#9aa0c8", accent="#2fd0b6", on="#06122e", good="#34d399", warn="#f5a524", bad="#f0556b"),
    "mono": dict(name="Mono", dark=False, bg="#ffffff", surface="#f4f4f4", surface2="#eaeaea", border="#dddddd",
                 text="#111111", muted="#777777", accent="#111111", on="#ffffff", good="#2d7a4f", warn="#8a6200", bad="#a02020"),
}
DEFAULT_THEME = "showcase"
ACCENTS = {"indigo": "#4f46e5", "green": "#16a37a", "blue": "#2f7de1", "magenta": "#c026d3", "orange": "#f0613c"}
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Inter,Helvetica,Arial,sans-serif"
PROJECT = "Club App Project"

STATIC_CSS = r"""
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"],
footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
[data-testid="stHeader"] { background: transparent !important; }
.stApp { background: var(--p-bg) !important; font-family: var(--p-font) !important; }
.block-container { max-width: 520px !important; margin: 0 auto; padding: 2.6rem 0.9rem 7.5rem !important; }
[data-testid="stVerticalBlock"] { gap: 0.75rem; }
html, body, .stApp { overflow-x: hidden !important; }
img, svg { max-width: 100%; }
.stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp summary,
.stApp [data-testid="stMetricValue"], .stApp [data-testid="stMetricLabel"] { color: var(--p-text); font-family: var(--p-font); }
.stApp [data-testid="stCaptionContainer"], .stApp small { color: var(--p-muted) !important; }
.stApp h2 { font-size: 1.5rem !important; font-weight: 800 !important; }
.stApp hr { border-color: var(--p-border) !important; }
/* inputs */
.stApp input, .stApp textarea, .stApp [data-baseweb="input"], .stApp [data-baseweb="textarea"], .stApp [data-baseweb="base-input"],
.stApp [data-baseweb="select"] > div { background: var(--p-surface2) !important; color: var(--p-text) !important;
  border-color: var(--p-border) !important; border-radius: 12px !important; font-size: 16px !important; }
.stApp [data-baseweb="select"] * { color: var(--p-text) !important; }
[data-baseweb="popover"] ul, [data-baseweb="popover"] > div, [data-baseweb="menu"] { background: var(--p-surface) !important; color: var(--p-text) !important; }
[data-baseweb="popover"] li, [data-baseweb="popover"] [role="option"] { color: var(--p-text) !important; background: transparent !important; }
[data-testid="stFileUploaderDropzone"] { background: var(--p-surface2) !important; border: 1px dashed var(--p-border) !important; border-radius: 14px !important;
  flex-direction: column; gap: .6rem; }
[data-testid="stFileUploaderDropzone"] * { color: var(--p-muted) !important; }
/* buttons */
.stApp .stButton > button, .stApp .stDownloadButton > button { width: 100%; min-height: 50px; border-radius: 14px; font-weight: 700;
  background: var(--p-surface); color: var(--p-text); border: 1px solid var(--p-border); }
.stApp .stButton > button p, .stApp .stDownloadButton > button p { color: inherit; }
.stApp button[kind="primary"], .stApp [data-testid="stBaseButton-primary"] { background: var(--p-accent) !important; color: var(--p-on) !important; border: none !important;
  box-shadow: 0 6px 16px color-mix(in srgb, var(--p-accent) 35%, transparent); }
.stApp button[kind="primary"] p, .stApp [data-testid="stBaseButton-primary"] p { color: var(--p-on) !important; }
.stApp button:disabled { opacity: .5; }
/* list rows (buttons whose key starts with row_) */
[class*="st-key-row_"] button { justify-content: flex-start !important; text-align: left !important; height: auto !important; min-height: 66px;
  padding: .7rem .9rem !important; border-radius: 16px !important; box-shadow: 0 3px 12px rgba(40,40,120,.06); }
[class*="st-key-row_"] button p { white-space: pre-line; text-align: left; width: 100%; line-height: 1.35; font-weight: 600; }
/* expanders, alerts, metrics, tabs, progress */
[data-testid="stExpander"] { background: var(--p-surface); border: 1px solid var(--p-border) !important; border-radius: 16px !important; }
[data-testid="stExpander"] summary { padding: .75rem .8rem !important; }
[data-testid="stAlert"] { background: var(--p-surface2) !important; border-radius: 14px !important; }
[data-testid="stAlert"] * { color: var(--p-text) !important; }
[data-testid="stMetric"] { background: var(--p-surface); border: 1px solid var(--p-border); border-radius: 14px; padding: .5rem .7rem; }
[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: .6rem !important; }
[data-testid="stColumn"] { min-width: 100% !important; flex: 1 1 100% !important; width: 100% !important; }
[data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="stColumn"] { min-width: calc(50% - .4rem) !important; flex: 1 1 calc(50% - .4rem) !important; width: auto !important; }
div[data-baseweb="tab-list"] { overflow-x: auto !important; flex-wrap: nowrap !important; scrollbar-width: none; gap: .2rem; }
button[data-baseweb="tab"] { color: var(--p-muted) !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--p-accent) !important; }
[data-baseweb="tab-highlight"] { background: var(--p-accent) !important; }
[data-testid="stProgress"] div[role="progressbar"] > div { background: var(--p-accent) !important; }
[data-testid="stDataFrame"], [data-testid="stDataEditor"] { overflow-x: auto !important; border-radius: 12px; }
pre, code { white-space: pre-wrap !important; }
[data-testid="stToast"], [data-testid="stToastContainer"] { bottom: 5.5rem !important; }
/* bottom tab bar (radio with key phnav) */
[class*="st-key-phnav"] { position: fixed !important; bottom: 0; left: 50%; transform: translateX(-50%); width: min(100%, 520px) !important;
  z-index: 999; margin: 0 !important; background: var(--p-surface); border-top: 1px solid var(--p-border);
  box-shadow: 0 -6px 18px rgba(0,0,0,.10); padding: .15rem .2rem calc(.25rem + env(safe-area-inset-bottom, 0px)) !important; }
[class*="st-key-phnav"] div[role="radiogroup"] { display: flex !important; flex-wrap: nowrap !important; justify-content: space-around; gap: 0 !important; width: 100%; }
[class*="st-key-phnav"] label { flex: 1 1 0; margin: 0 !important; padding: .45rem .1rem .3rem !important; justify-content: center; text-align: center;
  border-radius: 12px; cursor: pointer; }
[class*="st-key-phnav"] label > div:first-child { display: none !important; }
[class*="st-key-phnav"] label > div { width: 100%; }
[class*="st-key-phnav"] label p { white-space: pre-line; text-align: center; font-size: .7rem !important; line-height: 1.3 !important;
  color: var(--p-muted) !important; font-weight: 600; margin: 0; }
[class*="st-key-phnav"] label p::first-line { font-size: 1.4rem; }
[class*="st-key-phnav"] label:has(input:checked) { box-shadow: inset 0 3px 0 var(--p-accent); background: var(--p-surface2); }
[class*="st-key-phnav"] label:has(input:checked) p { color: var(--p-accent) !important; }
/* pill filters (radio with key starting phpill_) */
[class*="st-key-phpill_"] div[role="radiogroup"] { flex-wrap: nowrap !important; overflow-x: auto; gap: .4rem !important; scrollbar-width: none; }
[class*="st-key-phpill_"] label { flex: 0 0 auto; margin: 0 !important; padding: .35rem .95rem; border: 1px solid var(--p-border); border-radius: 999px; background: var(--p-surface); }
[class*="st-key-phpill_"] label > div:first-child { display: none !important; }
[class*="st-key-phpill_"] label p { font-size: .85rem !important; font-weight: 700; white-space: nowrap; margin: 0; }
[class*="st-key-phpill_"] label:has(input:checked) { background: var(--p-accent); border-color: var(--p-accent); }
[class*="st-key-phpill_"] label:has(input:checked) p { color: var(--p-on) !important; }
/* custom blocks */
.ph-top { display: flex; align-items: center; justify-content: space-between; gap: .6rem; }
.ph-brand { display: flex; align-items: center; gap: .55rem; min-width: 0; }
.ph-brand img { width: 34px; height: 34px; border-radius: 10px; }
.ph-brand b { font-size: 1.35rem; font-weight: 800; color: var(--p-text); letter-spacing: -.01em; }
.ph-proj { display: flex; justify-content: space-between; align-items: center; background: var(--p-surface); border: 1px solid var(--p-border);
  border-radius: 14px; padding: .65rem .9rem; font-weight: 700; color: var(--p-text); }
.ph-proj span { color: var(--p-muted); }
.ph-h { font-size: 1.8rem; font-weight: 800; color: var(--p-text); margin: .2rem 0 0; letter-spacing: -.02em; }
.ph-sub { color: var(--p-muted); font-size: .95rem; margin: .1rem 0 .3rem; }
.ph-muted { color: var(--p-muted); font-size: .85rem; }
.ph-card { background: var(--p-surface); border: 1px solid var(--p-border); border-radius: 18px; padding: .9rem; box-shadow: 0 4px 14px rgba(60,60,150,.07); }
.ph-ready { display: flex; flex-direction: column; align-items: center; gap: .2rem; text-align: center; }
.ph-ready svg { flex: 0 0 auto; width: 170px; height: 170px; }
.ph-card-t { font-size: 1.1rem; font-weight: 800; color: var(--p-text); margin-bottom: .2rem; }
.ph-tiles { display: grid; grid-template-columns: repeat(2, 1fr); gap: .6rem; }
.ph-tile { border-radius: 16px; padding: .8rem .9rem; display: flex; flex-direction: column; gap: .1rem; border: 1px solid var(--p-border); }
.ph-tile .i { font-size: 1.15rem; line-height: 1.2; }
.ph-tile .n { font-size: 1.7rem; font-weight: 800; color: var(--p-text); line-height: 1.15; }
.ph-tile .l { font-size: .82rem; font-weight: 600; color: var(--p-muted); }
.ph-tile.t-blue { background: color-mix(in srgb, #4f8ff7 14%, var(--p-surface)); }
.ph-tile.t-accent { background: color-mix(in srgb, var(--p-accent) 14%, var(--p-surface)); }
.ph-tile.t-warn { background: color-mix(in srgb, var(--p-warn) 16%, var(--p-surface)); }
.ph-tile.t-bad { background: color-mix(in srgb, var(--p-bad) 14%, var(--p-surface)); }
.ph-attn { display: flex; align-items: center; gap: .7rem; border-radius: 16px; padding: .8rem .9rem;
  background: color-mix(in srgb, var(--p-bad) 12%, var(--p-surface)); border: 1px solid color-mix(in srgb, var(--p-bad) 25%, var(--p-border)); }
.ph-attn b { display: block; color: var(--p-text); }
.ph-attn span { color: var(--p-muted); font-size: .85rem; }
.ph-sec { display: flex; align-items: center; gap: .5rem; margin-top: .3rem; font-size: 1.05rem; font-weight: 800; color: var(--p-text); }
.ph-dot { display: inline-grid; place-items: center; width: 24px; height: 24px; border-radius: 50%; background: var(--p-accent); color: var(--p-on); font-size: .8rem; font-weight: 800; }
.ph-chip { display: inline-block; padding: .18rem .7rem; border-radius: 999px; font-size: .74rem; font-weight: 700; background: var(--p-surface2); color: var(--p-muted); white-space: nowrap; border: 1px solid var(--p-border); }
.ph-chip.c-accent { color: var(--p-accent); border-color: var(--p-accent); }
.ph-chip.c-good { color: var(--p-good); border-color: var(--p-good); }
.ph-chip.c-warn { color: var(--p-warn); border-color: var(--p-warn); }
.ph-chip.c-bad { color: var(--p-bad); border-color: var(--p-bad); }
.ph-chip.on-good { background: var(--p-good); color: #062; border-color: var(--p-good); }
.ph-chip.on-warn { background: var(--p-warn); color: #310; border-color: var(--p-warn); }
.ph-chip.on-bad { background: var(--p-bad); color: #fff; border-color: var(--p-bad); }
.ph-src { display: flex; align-items: center; gap: .75rem; }
.ph-ico { flex: 0 0 auto; width: 46px; height: 46px; border-radius: 12px; background: var(--p-surface2); display: grid; place-items: center; font-size: 1.5rem; }
.ph-src .m { flex: 1 1 auto; min-width: 0; }
.ph-src .m b { display: block; font-size: 1rem; color: var(--p-text); overflow-wrap: anywhere; }
.ph-src .r { flex: 0 0 auto; display: flex; flex-direction: column; align-items: flex-end; gap: .3rem; }
.ph-ok { color: var(--p-good); font-size: .78rem; font-weight: 700; }
.ph-wait { color: var(--p-warn); font-size: .78rem; font-weight: 700; }
.ph-quote { background: var(--p-surface2); border-left: 4px solid var(--p-accent); border-radius: 12px; padding: .8rem .9rem; color: var(--p-text); font-size: 1.02rem; line-height: 1.5; }
.ph-chips { display: flex; flex-wrap: wrap; gap: .4rem; }
.ph-title { display: flex; align-items: center; gap: .7rem; }
.ph-title .ph-ico { background: var(--p-accent); color: var(--p-on); }
.ph-title b { font-size: 1.25rem; line-height: 1.25; color: var(--p-text); overflow-wrap: anywhere; }
.ph-bar { height: 9px; border-radius: 99px; background: var(--p-surface2); overflow: hidden; }
.ph-bar i { display: block; height: 100%; border-radius: 99px; background: var(--p-good); }
.ph-row { display: flex; justify-content: space-between; font-weight: 700; color: var(--p-text); margin-bottom: .35rem; }
.ph-act { display: flex; justify-content: space-between; gap: .6rem; padding: .35rem 0; font-size: .9rem; color: var(--p-text); border-bottom: 1px solid var(--p-border); }
.ph-act:last-child { border-bottom: none; }
.ph-act span:last-child, .ph-act b { color: var(--p-muted); white-space: nowrap; }
.ph-avatar { width: 64px; height: 64px; border-radius: 50%; background: var(--p-accent); color: var(--p-on); display: grid; place-items: center; font-size: 1.8rem; font-weight: 800; flex: 0 0 auto; }
.ph-empty { text-align: center; padding: 1.2rem .6rem; color: var(--p-muted); }
.ph-empty b { display: block; color: var(--p-text); font-size: 1.1rem; margin-bottom: .3rem; }
.ph-swatch { display: flex; gap: 6px; margin: .2rem 0 .4rem; }
.ph-swatch i { width: 28px; height: 28px; border-radius: 50%; border: 2px solid var(--p-border); }
.ph-login { text-align: center; padding: .4rem 0 .2rem; }
.ph-login img { width: 150px; border-radius: 12px; background: #fff; padding: 4px; }
.ph-secure { text-align: center; color: var(--p-muted); font-size: .8rem; margin-top: .4rem; }
.ph-private { display: flex; align-items: center; gap: .7rem; border-radius: 16px; padding: .8rem .9rem;
  background: color-mix(in srgb, var(--p-good) 14%, var(--p-surface)); border: 1px solid color-mix(in srgb, var(--p-good) 30%, var(--p-border)); color: var(--p-text); font-weight: 600; }
/* new in this version: list items, banners, checks, report card, welcome */
.ph-li { display: flex; align-items: center; gap: .75rem; background: var(--p-surface); border: 1px solid var(--p-border); border-radius: 16px;
  padding: .7rem .85rem; box-shadow: 0 3px 12px rgba(40,40,120,.06); }
.ph-li .m { flex: 1 1 auto; min-width: 0; }
.ph-li .m b { display: block; color: var(--p-text); font-size: .98rem; overflow-wrap: anywhere; }
.ph-li .m span { color: var(--p-muted); font-size: .8rem; }
.ph-av { flex: 0 0 auto; width: 42px; height: 42px; border-radius: 50%; background: var(--p-accent); color: var(--p-on); display: grid; place-items: center; font-weight: 800; }
.ph-banner { display: flex; align-items: center; gap: .6rem; border-radius: 14px; padding: .75rem .9rem; font-weight: 800; color: var(--p-bad);
  background: color-mix(in srgb, var(--p-bad) 12%, var(--p-surface)); border: 1px solid color-mix(in srgb, var(--p-bad) 28%, var(--p-border)); }
.ph-check { display: flex; align-items: center; gap: .6rem; padding: .4rem 0; color: var(--p-text); font-weight: 600; }
.ph-tick { flex: 0 0 auto; width: 22px; height: 22px; border-radius: 6px; display: grid; place-items: center; background: var(--p-good); color: #fff; font-size: .8rem; }
.ph-tick.off { background: transparent; border: 2px solid var(--p-border); color: transparent; }
.ph-rep { text-align: center; padding: 1.1rem .9rem; background: linear-gradient(180deg, color-mix(in srgb, var(--p-accent) 14%, var(--p-surface)), var(--p-surface)); }
.ph-rep .big { font-size: 2.2rem; line-height: 1.2; }
.ph-rep .pr { font-weight: 700; color: var(--p-accent); }
.ph-welcome { text-align: center; padding: 2.4rem .5rem .6rem; }
.ph-welcome img { width: 150px; border-radius: 22px; }
.ph-welcome h1 { font-size: 2rem; font-weight: 800; margin: .8rem 0 .2rem; color: var(--p-text); letter-spacing: -.02em; }
.ph-welcome p { color: var(--p-muted); font-size: 1.02rem; margin: 0 auto; max-width: 18rem; }
/* header icon buttons (bell, menu) stay on one row */
div[data-testid="stHorizontalBlock"]:has([class*="st-key-ph_bell"]) { flex-wrap: nowrap !important; align-items: center; gap: .35rem !important; }
div[data-testid="stHorizontalBlock"]:has([class*="st-key-ph_bell"]) > div[data-testid="stColumn"] { min-width: 0 !important; width: auto !important; flex: 0 0 auto !important; }
div[data-testid="stHorizontalBlock"]:has([class*="st-key-ph_bell"]) > div[data-testid="stColumn"]:first-child { flex: 1 1 auto !important; }
html body .stApp [class*="st-key-ph_bell"] button, html body .s
