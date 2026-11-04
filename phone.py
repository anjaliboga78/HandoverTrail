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
html body .stApp [class*="st-key-ph_bell"] button, html body .stApp [class*="st-key-ph_menu"] button { width: 40px !important; min-width: 40px !important;
  min-height: 40px !important; height: 40px !important; padding: 0 !important; border-radius: 50% !important; }
/* accent colour swatches (appearance screen) */
div[data-testid="stHorizontalBlock"]:has([class*="st-key-ph_acc_"]) { flex-wrap: nowrap !important; gap: .4rem !important; }
div[data-testid="stHorizontalBlock"]:has([class*="st-key-ph_acc_"]) > div[data-testid="stColumn"] { min-width: 0 !important; width: auto !important; flex: 0 0 auto !important; }
html body .stApp [class*="st-key-ph_acc_"] button { width: 40px !important; min-width: 40px !important; min-height: 40px !important; height: 40px !important;
  padding: 0 !important; border-radius: 50% !important; color: #fff !important; border: 3px solid var(--p-surface) !important; box-shadow: 0 0 0 1px var(--p-border); }
html body .stApp [class*="st-key-ph_acc_"] button p { color: #fff !important; }
html body .stApp [class*="st-key-ph_acc_indigo"] button { background: #4f46e5 !important; }
html body .stApp [class*="st-key-ph_acc_green"] button { background: #16a37a !important; }
html body .stApp [class*="st-key-ph_acc_blue"] button { background: #2f7de1 !important; }
html body .stApp [class*="st-key-ph_acc_magenta"] button { background: #c026d3 !important; }
html body .stApp [class*="st-key-ph_acc_orange"] button { background: #f0613c !important; }
"""

HC_CSS = (".stApp{--p-border:var(--p-text) !important;}"
          ".ph-card,.ph-tile,.ph-attn,.ph-proj,.ph-li,[data-testid='stExpander'],[data-testid='stMetric']{border-width:2px !important;}"
          ".stApp .stButton>button,.stApp .stDownloadButton>button{border:2px solid var(--p-text) !important;}"
          ".stApp [data-testid='stCaptionContainer'],.ph-muted,.ph-sub{color:var(--p-text) !important;}")
RM_CSS = "*,*::before,*::after{animation:none !important;transition:none !important;scroll-behavior:auto !important;}"


def _vars(t: dict) -> str:
    v = (f"--p-bg:{t['bg']};--p-surface:{t['surface']};--p-surface2:{t['surface2']};--p-border:{t['border']};"
         f"--p-text:{t['text']};--p-muted:{t['muted']};--p-accent:{t['accent']};--p-on:{t['on']};"
         f"--p-good:{t['good']};--p-warn:{t['warn']};--p-bad:{t['bad']};--p-font:{FONT};")
    legacy = (f"--paper:{t['bg']};--ink:{t['text']};--card:{t['surface']};--teal:{t['accent']};--red:{t['bad']};--muted:{t['muted']};"
              f"--yellow:{t['surface2']};--green:{t['surface2']};--blue:{t['surface2']};--pink:{t['surface2']};"
              f"--serif:{FONT};--hand:{FONT};--hs:.78;--bgimg:none;--bgsize:auto;")
    return v + legacy + ("color-scheme:dark;" if t["dark"] else "color-scheme:light;")


def _with_accent(t: dict) -> dict:
    t = dict(t)
    acc = pref("pa", "default")
    if acc in ACCENTS:
        t["accent"] = ACCENTS[acc]
        t["on"] = "#ffffff"
    return t


SEL = "html body .stApp, html body [data-testid='stAppViewContainer']"
DARK_TABLES = '[data-testid="stDataFrame"],[data-testid="stDataEditor"]{filter:invert(.92) hue-rotate(180deg);}'


def theme_css(key: str) -> str:
    base = "showcase" if key == "system" else key
    t = _with_accent(THEMES[base])
    extra = DARK_TABLES if t["dark"] else ""
    if base == "showcase":
        extra += ".stApp{background:linear-gradient(180deg,#e8e7ff 0%,#f5f4ff 40%,#ffffff 100%) !important;}"
    system = ""
    if key == "system":  # follow the phone's own light / dark setting
        d = _with_accent(THEMES["midnight"])
        system = (f"@media (prefers-color-scheme: dark){{{SEL}{{{_vars(d)}}}html body .stApp{{background:var(--p-bg) !important;}}{DARK_TABLES}}}")
    return f"<style>{SEL}{{{_vars(t)}}}{STATIC_CSS}{extra}{system}</style>"


def _qp(name: str, default: str = "") -> str:
    try:
        return st.query_params.get(name) or default
    except Exception:
        return default


def pref(name: str, default: str = "") -> str:
    """A small look-and-feel setting: this session first, then the page address (so it survives a reload)."""
    v = st.session_state.get("pp_" + name)
    return v if v is not None else _qp(name, default)


def set_pref(name: str, value: str) -> None:
    st.session_state["pp_" + name] = value
    try:
        st.query_params[name] = value
    except Exception:
        pass


def current_theme() -> str:
    key = st.query_params.get("mt") or st.session_state.get("ph_theme") or DEFAULT_THEME
    return key if (key in THEMES or key == "system") else DEFAULT_THEME


# ------------------------------------------------------------------ small helpers

def _h(s: str) -> None:
    st.markdown(s, unsafe_allow_html=True)


def _plain(s) -> str:
    return re.sub(r"[*_`\[\]~#<>]", "", str(s)).strip()


def _go(tab: str, item: int | None = None, vmode: str | None = None, rep: str | None = None) -> None:
    st.session_state["ph_goto"] = tab
    st.session_state.pop("ph_screen", None)
    if item is not None:
        st.session_state["ph_item"] = item
        st.session_state["ph_vmode"] = "list"
    if vmode:
        st.session_state["ph_vmode"] = vmode
    if rep:
        st.session_state["ph_rep_goto"] = rep
    st.rerun()


def _flash(msg: str) -> None:
    st.session_state["flash"] = msg


def _initial(name: str) -> str:
    return ui.esc((str(name or "?").strip()[:1] or "?").upper())


STATUS_EMOJI = {"verified": "✅", "approximate": "🟡", "unverified": "🔴"}
VIS_CLASS = {"Everyone": "c-accent", "Core": "c-warn", "Lead": "c-good"}
NAV = {"Overview": "🏠\nHome", "Sources": "🗂️\nSources", "Verify": "🛡️\nVerify", "Report": "📄\nReport",
       "Handover": "📄\nHandover", "Checklist": "☑️\nChecklist", "Profile": "👤\nProfile"}
LEAD_TABS = ["Overview", "Sources", "Verify", "Report", "Profile"]
OTHER_TABS = ["Handover", "Checklist", "Profile"]
REPORT_SECTIONS = ["Handover", "Review", "Transfer", "Checklist", "Audit"]


def ring_svg(score: int, color: str) -> str:
    r = 44
    c = 2 * 3.14159 * r
    off = c * (1 - max(0, min(100, score)) / 100)
    return (f"<svg viewBox='0 0 120 120'><circle cx='60' cy='60' r='{r}' fill='none' stroke='var(--p-surface2)' stroke-width='10'/>"
            f"<circle cx='60' cy='60' r='{r}' fill='none' stroke='{color}' stroke-width='10' stroke-linecap='round' "
            f"stroke-dasharray='{c:.1f}' stroke-dashoffset='{off:.1f}' transform='rotate(-90 60 60)'/>"
            f"<text x='60' y='64' text-anchor='middle' font-size='24' font-weight='800' fill='var(--p-text)'>{int(score)}%</text>"
            f"<text x='60' y='80' text-anchor='middle' font-size='9' fill='var(--p-muted)'>Readiness</text></svg>")


def header_block() -> None:
    """Brand on the left, notifications bell and menu on the right."""
    icon = ui.asset_uri("icon.png")
    img = f"<img src='{icon}' alt=''>" if icon else "<span style='font-size:1.6rem'>🤝</span>"
    c = st.columns([8, 1, 1])
    c[0].markdown(f"<div class='ph-top'><div class='ph-brand'>{img}<b>HandoverTrail</b></div></div>", unsafe_allow_html=True)
    if c[1].button("🔔", key="ph_bell"):
        st.session_state["ph_screen"] = "notifications"
        st.rerun()
    if c[2].button("☰", key="ph_menu"):
        st.session_state["ph_screen"] = "menu"
        st.rerun()


def title_html(title: str, sub: str = "") -> str:
    return f"<div class='ph-h'>{ui.esc(title)}</div>" + (f"<div class='ph-sub'>{ui.esc(sub)}</div>" if sub else "")


def empty_html(title: str, text: str) -> str:
    return f"<div class='ph-card ph-empty'><b>{ui.esc(title)}</b>{ui.esc(text)}</div>"


def bar_html(pct: int, label: str = "") -> str:
    pct = max(0, min(100, int(pct)))
    return (f"<div class='ph-row'><span>{ui.esc(label)}</span><span>{pct}%</span></div>"
            f"<div class='ph-bar'><i style='width:{pct}%'></i></div>")


def severity(it: dict) -> int:
    if it["is_conflict"]:
        return 0
    if it["verify_status"] == "unverified":
        return 1
    if it["is_gap"]:
        return 2
    return 3


def _extract_now(user: str, ctx) -> None:
    with st.spinner("Reading sources and checking every quote..."):
        result = extract.run_extraction(user, provider=ctx.provider())
    for w in result["warnings"]:
        st.warning(w)
    _flash(f"Found {result['items']} items in {result['sources']} source(s)")
    st.rerun()


def run_extraction_button(user: str, ctx, key: str) -> None:
    pending = db.q("SELECT COUNT(*) AS n FROM sources WHERE extracted=0")[0]["n"]
    if pending and st.button(f"Run extraction ({pending} new source{'s' if pending != 1 else ''})", key=key, type="primary"):
        _extract_now(user, ctx)


# ------------------------------------------------------------------ Welcome and Login

def welcome_screen() -> None:
    logo = ui.asset_uri("logo.png") or ui.asset_uri("icon.png")
    img = f"<img src='{logo}' alt='HandoverTrail'>" if logo else "<div style='font-size:4rem'>🤝</div>"
    _h(f"<div class='ph-welcome'>{img}<h1>HandoverTrail</h1>"
       "<p>Turn scattered project activity into a verified, usable handover.</p></div>")
    if st.button("Get Started →", key="ph_start", type="primary"):
        st.session_state["ph_started"] = True
        st.rerun()


def login_screen(users: list) -> None:
    logo = ui.asset_uri("logo.png")
    img = f"<img src='{logo}' alt='HandoverTrail logo'>" if logo else "<h1>HandoverTrail</h1>"
    _h(f"<div class='ph-login'>{img}</div>")
    _h("<div class='ph-sec'>Choose your account</div>")
    names = [u["name"] for u in users]
    sel = st.session_state.get("ph_pick") or names[0]
    for i, u in enumerate(users):
        mark = "✔ " if u["name"] == sel else "👤 "
        if st.button(f"{mark}{u['name']}\n{u['role']}", key=f"row_login_{i}", use_container_width=True):
            st.session_state["ph_pick"] = u["name"]
            st.rerun()
    if st.button("Continue →", key="ph_continue", type="primary"):
        st.session_state["ph_user"] = sel
        st.session_state["ph_logged"] = True
        st.rerun()
    _h("<div class='ph-secure'>🔒 Secure demo workspace</div>")


# ------------------------------------------------------------------ Overview (Home)

def tab_overview(user: str, role: str, ctx) -> None:
    n_src = db.q("SELECT COUNT(*) AS n FROM sources")[0]["n"]
    items = handover.list_items()
    if not n_src:
        _h(empty_html("No sources yet", "Load the demo project to see the whole workflow, or add your own files."))
        if st.button("Load the demo project", key="ph_demo0", type="primary"):
            ingest.load_demo(user)
            _flash("Demo project loaded")
            st.rerun()
        if st.button("Add my own source", key="ph_add0"):
            st.session_state["ph_add"] = True
            _go("Sources")
        return
    _h(f"<div class='ph-proj'>{ui.esc(PROJECT)}<span>⌄</span></div>")
    if not items:
        _h(empty_html("Sources are in", "Run extraction so HandoverTrail can find the decisions, tasks and risks and check every quote."))
        run_extraction_button(user, ctx, "ph_ext0")
        return
    lookup = {i["id"]: i for i in items}
    rd = readiness.readiness(role)
    score = int(rd["score"])
    color = "var(--p-good)" if score >= 70 else ("var(--p-warn)" if score >= 40 else "var(--p-bad)")
    _h(f"<div class='ph-card ph-ready'>{ring_svg(score, color)}<div class='ph-muted'>{ui.esc(rd['band'])}</div></div>")
    decisions = sum(1 for i in items if i["type"] == "decision")
    tasks = sum(1 for i in items if i["type"] == "task")
    conflicts = sum(1 for i in items if i["is_conflict"])
    _h("<div class='ph-tiles'>"
       f"<div class='ph-tile t-blue'><div class='i'>📄</div><div class='n'>{n_src}</div><div class='l'>Sources</div></div>"
       f"<div class='ph-tile t-accent'><div class='i'>✅</div><div class='n'>{decisions}</div><div class='l'>Decisions</div></div>"
       f"<div class='ph-tile t-warn'><div class='i'>🕒</div><div class='n'>{tasks}</div><div class='l'>Open Tasks</div></div>"
       f"<div class='ph-tile t-bad'><div class='i'>⚠️</div><div class='n'>{conflicts}</div><div class='l'>Conflicts</div></div></div>")
    run_extraction_button(user, ctx, "ph_ext1")
    attn = sorted([i for i in items if i["review_status"] == "pending" and severity(i) < 3], key=severity)[:5]
    if attn:
        _h(f"<div class='ph-attn'><span style='font-size:1.4rem'>⚠️</span><div><b>Needs Attention</b>"
           f"<span>{len(attn)} item{'s' if len(attn) != 1 else ''} need review</span></div></div>")
    else:
        _h("<div class='ph-card ph-muted'>Nothing needs attention. Nice work.</div>")
    for i in attn:
        dot = {0: "🔴", 1: "🟠", 2: "🔵"}[severity(i)]
        why = "; ".join(flags.describe(i, lookup, role)) or type_label(i["type"])
        if st.button(f"{dot} {_plain(i['text'])[:70]}\n{_plain(why)[:80]}", key=f"row_att_{i['id']}", use_container_width=True):
            _go("Verify", i["id"])
    if attn and st.button("See all in Verify →", key="ph_seeall"):
        st.session_state.pop("ph_item", None)
        _go("Verify", vmode="list")
    act = db.q("SELECT at, user_name, action, target FROM audit_log ORDER BY id DESC LIMIT 4")
    if act:
        lines = "".join(f"<div class='ph-act'><span>{ui.esc(a['user_name'])}: {ui.esc(str(a['action']).replace('_', ' '))}"
                        f"{(' ' + ui.esc(str(a['target']))[:24]) if a['target'] else ''}</span><span>{ui.esc(str(a['at'])[5:16])}</span></div>"
                        for a in act)
        _h(f"<div class='ph-sec'>Recent Activity</div><div class='ph-card'>{lines}</div>")


# ------------------------------------------------------------------ Sources

def src_icon(s: dict) -> str:
    t = (s.get("type") or "").lower()
    n = (s.get("name") or "").lower()
    if "git" in t or "git" in n:
        return "🐙"
    if "chat" in t or "chat" in n or "slack" in n:
        return "💬"
    if n.endswith(".csv") or "task" in n or "jira" in n:
        return "📊"
    return "📄"


def _add_back() -> None:
    if st.button("← Choose another way", key="ph_addback"):
        st.session_state["ph_addmode"] = None
        st.rerun()


def add_panel(user: str, ctx) -> None:
    mode = st.session_state.get("ph_addmode")
    if not mode:
        _h("<div class='ph-sec'>Add Source</div>")
        for key, label in (("upload", "📄 Upload Files\n(.txt, .md, .csv)"), ("github", "🐙 Import GitHub\n(Repo or Issues)"),
                           ("paste", "📝 Paste Notes\n(With AI Analysis)"), ("demo", "🧪 Demo project\n(Made-up club app)")):
            if st.button(label, key=f"row_add_{key}", use_container_width=True):
                st.session_state["ph_addmode"] = key
                st.rerun()
        _h("<div class='ph-private'><span style='font-size:1.4rem'>🛡️</span>Your data stays private and secure.</div>")
        return
    _add_back()
    if mode == "upload":
        files = st.file_uploader("Notes, chat exports, task lists (.txt .md .csv .json)", type=["txt", "md", "csv", "json"],
                                 accept_multiple_files=True, key="ph_files")
        vis = st.selectbox("Who may see these?", list(config.LEVELS), index=0, key="ph_vis")
        date_txt = st.text_input("Source date (optional, YYYY-MM-DD)", key="ph_date")
        if st.button("Import files", key="ph_imp", type="primary"):
            if date_txt and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_txt):
                st.error("Use the date format YYYY-MM-DD.")
            elif not files:
                st.warning("Choose at least one file first.")
            else:
                done = 0
                for f in files:
                    try:
                        done += len(ingest.ingest_upload(f.name, f.getvalue(), vis, date_txt or None, user))
                    except ValueError as e:
                        st.error(str(e))
                if done:
                    _flash(f"Imported {done} source(s)")
                    st.session_state["ph_add"] = False
                    st.session_state["ph_addmode"] = None
                    st.rerun()
    elif mode == "paste":
        ctx.paste_box(user)
    elif mode == "github":
        repo = st.text_input("Repository (owner/name)", key="ph_repo")
        token = st.text_input("GitHub token (optional, read-only)", type="password", key="ph_tok")
        gvis = st.selectbox("Visibility", list(config.LEVELS), index=0, key="ph_gvis")
        if st.button("Import from GitHub", key="ph_gh", type="primary"):
            try:
                n = ingest.import_github(repo.strip(), token.strip() or None, gvis, user)
                _flash(f"Imported {n} source(s) from {repo}")
                st.session_state["ph_addmode"] = None
                st.rerun()
            except (ValueError, RuntimeError) as e:
                st.error(str(e))
    else:
        st.caption("A made-up club app with planted conflicts, gaps, secrets and a lead-only note.")
        if st.button("Load the whole demo project", key="ph_demo1", type="primary"):
            _flash(f"Loaded {ingest.load_demo(user)} demo sources")
            st.session_state["ph_add"] = False
            st.session_state["ph_addmode"] = None
            st.rerun()
        picks = st.multiselect("Or pick demo files", ingest.demo_file_names(), key="ph_picks")
        if st.button("Load the chosen files", key="ph_demo2") and picks:
            _flash(f"Loaded {ingest.load_demo_files(picks, user)} source(s)")
            st.rerun()


def tab_sources(user: str, role: str, ctx) -> None:
    _h(title_html("Sources"))
    adding = bool(st.session_state.get("ph_add"))
    if not adding:
        query = st.text_input("Search sources", placeholder="🔍 Search sources...", key="ph_srcq", label_visibility="collapsed")
    else:
        query = ""
    if st.button("Close" if adding else "＋ Add Source", key="ph_addbtn", type="secondary" if adding else "primary"):
        st.session_state["ph_add"] = not adding
        st.session_state["ph_addmode"] = None
        st.rerun()
    if adding:
        add_panel(user, ctx)
        return
    flt = st.radio("Filter", ["All", "Files", "GitHub"], horizontal=True, key="phpill_src", label_visibility="collapsed")
    run_extraction_button(user, ctx, "ph_ext2")
    rows = db.q("SELECT id, name, type, source_date, visibility, redaction_count, extracted, LENGTH(text) AS n FROM sources ORDER BY id DESC")
    rows = [s for s in rows if (not query or query.lower() in (s["name"] or "").lower())
            and (flt == "All" or (flt == "GitHub") == ("git" in ((s["type"] or "") + (s["name"] or "")).lower()))]
    if not rows:
        _h(empty_html("No sources here", "Tap Add Source to upload files, paste notes or load the demo."))
    for s in rows:
        kb = (s["n"] or 0) / 1024
        vis = s["visibility"]
        status = "<span class='ph-ok'>● Processed</span>" if s["extracted"] else "<span class='ph-wait'>● Processing</span>"
        masked = f" · {s['redaction_count']} masked" if s["redaction_count"] else ""
        _h(f"<div class='ph-card ph-src'><div class='ph-ico'>{src_icon(s)}</div><div class='m'><b>{ui.esc(s['name'])}</b>"
           f"<span class='ph-muted'>{ui.esc(s['source_date'] or 'undated')} · {kb:.1f} KB{masked}</span><br>{status}</div>"
           f"<div class='r'><span class='ph-chip {VIS_CLASS.get(vis, '')}'>{ui.esc(vis)}</span><span class='ph-muted'>⋮</span></div></div>")
    with st.expander("What was masked (originals are never stored)"):
        red = db.q("SELECT s.name AS source, r.tag, r.preview FROM redactions r JOIN sources s ON s.id=r.source_id")
        if red:
            for r in red:
                st.caption(f"{r['source']}: {r['tag']} {r['preview']}")
        else:
            st.caption("Nothing needed masking.")


# ------------------------------------------------------------------ Reconstruct, Verify, Conflicts, Item details

MEANING = {
    "verified": "The quote was found word for word in the source. No action needed.",
    "approximate": "The quote differs by a few words from the source. Check it, then mark it as reviewed.",
    "unverified": "The quote was not found in the source, so it is not treated as fact. Check the source yourself before approving.",
}
TYPE_DOT = {"decision": "🟢", "task": "🟢", "risk": "🟠", "blocker": "🔴", "open_question": "🟠", "dependency": "🔵", "contact": "🔵"}


def reconstruct_screen(user: str, role: str, ctx, items: list) -> None:
    """Screen 6: run extraction and see what was found."""
    _h(title_html("Reconstruct & Verify", "Extract project information from your sources."))
    pending = db.q("SELECT COUNT(*) AS n FROM sources WHERE extracted=0")[0]["n"]
    label = f"Run Extraction ({pending} new)" if pending else "Run Extraction"
    if st.button(label, key="ph_ext_main", type="primary"):
        if not pending:
            st.warning("Nothing new to process. Add a source first.")
        else:
            _extract_now(user, ctx)
    if not items:
        _h(empty_html("Nothing found yet", "Add sources, then run extraction."))
        return
    counts = Counter(i["type"] for i in items)
    conflicts = sum(1 for i in items if i["is_conflict"])
    gaps = sum(1 for i in items if i["is_gap"])
    rows = "".join(f"<div class='ph-act'><span>{TYPE_DOT.get(t, '🔹')} {ui.esc(type_label(t))}</span><b>{counts[t]}</b></div>"
                   for t in config.ITEM_TYPES if counts.get(t))
    rows += f"<div class='ph-act'><span>🔴 Conflicts</span><b>{conflicts}</b></div>"
    if gaps:
        rows += f"<div class='ph-act'><span>🟠 Gaps (missing owners or details)</span><b>{gaps}</b></div>"
    _h(f"<div class='ph-sec'>Found {len(items)} items</div><div class='ph-card'>{rows}</div>")
    if st.button("View Details →", key="ph_viewdet"):
        st.session_state["ph_vmode"] = "list"
        st.rerun()


def conflicts_view(items: list, lookup: dict, role: str) -> None:
    """Screen 8: every item that disagrees with another, with a button to review it."""
    conf = [i for i in items if i["is_conflict"]]
    if not conf:
        _h(empty_html("No conflicts", "No two sources disagree right now."))
        return
    _h(f"<div class='ph-banner'>🚨 {len(conf)} Conflict{'s' if len(conf) != 1 else ''} Found</div>")
    cls = {"verified": "c-good", "approximate": "c-warn", "unverified": "c-bad"}
    for i in conf:
        why = "".join(f"<div class='ph-muted'>• {ui.esc(f)}</div>" for f in flags.describe(i, lookup, role))
        _h(f"<div class='ph-card'><div class='ph-card-t'>{ui.esc(_plain(i['text'])[:110])}</div>"
           f"<div class='ph-chips'><span class='ph-chip {cls[i['verify_status']]}'>{STATUS_TEXT[i['verify_status']]}</span>"
           f"<span class='ph-chip'>{ui.esc(i['source_name'])}</span></div>{why}</div>")
        if st.button("Review Conflict", key=f"phcf_{i['id']}"):
            st.session_state["ph_item"] = i["id"]
            st.rerun()


def related_items(it: dict, items: list, n: int = 3) -> list:
    base = _plain(it["text"]).lower()
    scored = []
    for o in items:
        if o["id"] == it["id"]:
            continue
        r = difflib.SequenceMatcher(None, base, _plain(o["text"]).lower()).ratio()
        if r >= 0.5:
            scored.append((r, o))
    scored.sort(key=lambda x: -x[0])
    return [o for _, o in scored[:n]]


def verify_detail(it: dict, lookup: dict, user: str, role: str) -> None:
    """Screen 9: one item with its proof quote, match score and related items."""
    if st.button("← Back to list", key="ph_back"):
        st.session_state.pop("ph_item", None)
        st.rerun()
    status = it["verify_status"]
    score = max(0, min(100, float(it["verify_score"] or 0)))
    cls = {"verified": "on-good", "approximate": "on-warn", "unverified": "on-bad"}
    chips = "".join(f"<span class='ph-chip {cls[s] if s == status else ''}'>{STATUS_TEXT[s]}</span>" for s in ("verified", "approximate", "unverified"))
    bar = {"verified": "var(--p-good)", "approximate": "var(--p-warn)", "unverified": "var(--p-bad)"}[status]
    src = db.one("SELECT text FROM sources WHERE id=?", (it["source_id"],))
    icon = {"decision": "🧭", "risk": "⚠️", "blocker": "⛔"}.get(it["type"], "📌")
    _h(f"<div class='ph-card'><div class='ph-title'><div class='ph-ico'>{icon}</div><b>{ui.esc(it['text'])}</b></div></div>")
    _h(f"<div class='ph-chips'><span class='ph-chip c-accent'>{ui.esc(type_label(it['type']))}</span>{chips}</div>")
    _h(f"<div class='ph-quote'>“{ui.esc(it['quote'])}”</div>")
    _h(f"<div class='ph-muted'>📄 {ui.esc(it['source_name'])} · {ui.esc(it['item_date'] or it.get('source_date') or 'undated')} · "
       f"review: {ui.esc(it['review_status'])}</div>")
    _h(f"<div class='ph-row'><span>Match score</span><span>{score:.0f}%</span></div><div class='ph-bar'><i style='width:{score:.0f}%;background:{bar}'></i></div>")
    extra = "".join(f"<div>• {ui.esc(f)}</div>" for f in flags.describe(it, lookup, role))
    _h(f"<div class='ph-card'><div class='ph-card-t'>🛡️ What this means</div><div class='ph-muted'>{MEANING[status]}</div>{extra}</div>")
    checked = True
    if status == "unverified" and it["review_status"] != "approved":
        checked = st.checkbox("I checked the source myself and this is correct", key=f"phchk{it['id']}")
    if it["review_status"] == "approved":
        st.success("Reviewed and approved.")
        if st.button("Back to pending", key=f"phpd{it['id']}"):
            handover.set_review(it["id"], "pending", user, it["text"])
            st.rerun()
    else:
        if st.button("✓ Mark as reviewed", key=f"phap{it['id']}", type="primary"):
            if checked:
                handover.set_review(it["id"], "approved", user, it["text"])
                _flash("Item approved")
                st.rerun()
            else:
                st.error("Tick the box to confirm you checked this unverified item.")
        if st.button("Reject", key=f"phrj{it['id']}"):
            handover.set_review(it["id"], "rejected", user, it["text"])
            _flash("Item rejected")
            st.rerun()
    with st.expander("Open source"):
        _h(ui.evidence_html(src["text"], it["quote"]))
    rel = related_items(it, list(lookup.values()))
    if rel:
        _h("<div class='ph-sec'>Related Items</div>")
        for o in rel:
            if st.button(f"{STATUS_EMOJI[o['verify_status']]} {_plain(o['text'])[:70]}\n{_plain(type_label(o['type']))} · {_plain(o['source_name'])}",
                         key=f"row_rel_{it['id']}_{o['id']}", use_container_width=True):
                st.session_state["ph_item"] = o["id"]
                st.rerun()


def tab_verify(user: str, role: str, ctx) -> None:
    items = handover.list_items()
    lookup = {i["id"]: i for i in items}
    sel = st.session_state.get("ph_item")
    if sel in lookup:
        verify_detail(lookup[sel], lookup, user, role)
        return
    if st.session_state.get("ph_vmode") != "list" or not items:
        reconstruct_screen(user, role, ctx, items)
        return
    if st.button("← Reconstruct", key="ph_vback"):
        st.session_state["ph_vmode"] = None
        st.rerun()
    _h(title_html("Verification"))
    flt = st.radio("Filter", [f"All ({len(items)})", "Verified", "Approximate", "Unverified", "Conflicts"], horizontal=True,
                   key="phpill_vf", label_visibility="collapsed")
    if flt == "Conflicts":
        conflicts_view(items, lookup, role)
        return
    shown = [i for i in items if flt.startswith("All") or (flt == "Verified" and i["verify_status"] == "verified")
             or (flt == "Approximate" and i["verify_status"] == "approximate")
             or (flt == "Unverified" and i["verify_status"] == "unverified")]
    st.caption(f"{len(shown)} of {len(items)} items")
    for i in shown:
        sub = f"{STATUS_TEXT[i['verify_status']]} · {type_label(i['type'])} · {i['source_name']}"
        q = _plain(i["quote"])[:70]
        if st.button(f"{STATUS_EMOJI[i['verify_status']]} {_plain(i['text'])[:75]}\n{_plain(sub)[:80]}\n“{q}”", key=f"row_it_{i['id']}", use_container_width=True):
            st.session_state["ph_item"] = i["id"]
            st.rerun()


# ------------------------------------------------------------------ Report: handover report, transfer, checklist, audit

REPORT_PARTS = ["Project Overview", "Responsibilities & New Owners", "Important Decisions", "Pending Tasks",
                "Readiness Score", "Onboarding Plan (Day 1 / Week 1 / Month 1)"]


def report_card(user: str, role: str) -> None:
    """Screen 10: what the PDF contains, with a download button."""
    ticks = "".join(f"<div class='ph-check'><span class='ph-tick'>✓</span>{ui.esc(p)}</div>" for p in REPORT_PARTS)
    _h(f"<div class='ph-card ph-rep'><div class='big'>🚩</div><div class='ph-card-t'>HandoverTrail</div>"
       f"<div class='pr'>Project Handover Report</div><div class='ph-muted'>{ui.esc(PROJECT)}</div></div>")
    _h(f"<div class='ph-card'><div class='ph-muted'>Included in the PDF (restricted items are left out for your role)</div>{ticks}</div>")
    people = report.people_for(role) or ["(none)"]
    who = st.selectbox("Departing member", people, key="phrep_who")
    if st.button("Generate PDF report", key="phrep_go", type="primary") and who != "(none)":
        try:
            st.session_state["phrep_pdf"] = (who, report.generate(user, role, who))
        except (ValueError, PermissionError) as e:
            st.error(str(e))
    got = st.session_state.get("phrep_pdf")
    if got and got[0] == who:
        view = handover.view_for(role)
        ver = f"_v{view['version']}" if view else ""
        st.download_button("⬇ Download PDF", data=got[1], file_name=f"handover_report{ver}_{who.lower().replace(' ', '_')}.pdf",
                           mime="application/pdf", key="phrep_dl")


def transfer_header() -> None:
    """Screen 11 summary. The full transfer tools are right below it."""
    people = transfer.owners()
    if not people:
        return
    who = st.session_state.get("tr_who")
    if who not in people:
        who = people[0]
    pr = transfer.progress(who)
    _h(f"<div class='ph-card'><div class='ph-muted'>Who is leaving?</div><div class='ph-card-t'>{ui.esc(who)}</div>"
       f"{bar_html(pr['percent'], 'Complete')}<div class='ph-muted' style='margin-top:.4rem'>Transfer {pr['completed']} of {pr['total']} items</div></div>")
    try:
        rows = transfer.list_transfers(None, who)[:4]
    except Exception:
        rows = []
    for t in rows:
        done = t["status"] == "completed"
        _h(f"<div class='ph-li'><div class='m'><b>#{t['item_id']} {ui.esc(_plain(t['text'])[:60])}</b>"
           f"<span>{ui.esc(t['from_owner'])} → {ui.esc(t['to_owner'])}</span></div>"
           f"<span class='ph-chip {'on-good' if done else 'c-warn'}'>{ui.esc(transfer.LABEL[t['status']])}</span></div>")


def checklist_header(user: str, role: str) -> None:
    """Screen 12 summary. The full checklist (tick, add, note, download) is right below it."""
    names = checklist.people()
    if not names:
        return
    start = names.index(user) if (role != "Lead" and user in names) else 0
    who = st.session_state.get("dc_who")
    if who not in names:
        who = names[start]
    data = checklist.build(who, role)
    _h(f"<div class='ph-card'><div class='ph-card-t'>{ui.esc(who)}'s departure checklist</div>"
       f"{bar_html(data['percent'], 'Complete')}<div class='ph-muted' style='margin-top:.4rem'>{data['done']} of {data['total']} done · {data['left']} left</div></div>")
    lines = []
    for sec in data["sections"]:
        for e in sec["entries"]:
            if not e["restricted"]:
                lines.append(f"<div class='ph-check'><span class='ph-tick {'' if e['done'] else 'off'}'>✓</span>{ui.esc(_plain(e['label'])[:70])}</div>")
    if lines:
        _h(f"<div class='ph-card'>{''.join(lines[:6])}</div>")


def screen_audit(ctx) -> None:
    """Screen 13: recent activity as a feed. The full tables are one tap away."""
    flt = st.radio("Filter", ["All", "Actions", "Views"], horizontal=True, key="phpill_audit", label_visibility="collapsed")
    rows = db.q("SELECT at, user_name, action, target, detail FROM audit_log ORDER BY id DESC LIMIT 80")
    rows = [r for r in rows if flt == "All" or (flt == "Views") == ("view" in str(r["action"]).lower())]
    if not rows:
        _h(empty_html("Nothing here", "Actions and views will show up as people use the app."))
    for r in rows[:30]:
        what = str(r["action"]).replace("_", " ")
        tgt = f" · {ui.esc(str(r['target']))[:40]}" if r["target"] else ""
        _h(f"<div class='ph-li'><div class='ph-av'>{_initial(r['user_name'])}</div><div class='m'><b>{ui.esc(r['user_name'])}</b>"
           f"<span>{ui.esc(what)}{tgt}</span></div><span class='ph-muted'>{ui.esc(str(r['at'])[5:16])}</span></div>")
    with st.expander("Full audit tables (who viewed, acknowledgements)"):
        ctx.page_audit()


def tab_report(user: str, role: str, ctx) -> None:
    _h(title_html("Report", "Review, hand over, transfer and close out."))
    want = st.session_state.pop("ph_rep_goto", None)
    if want in REPORT_SECTIONS:
        st.session_state["phpill_rep"] = want
    sec = st.radio("Section", REPORT_SECTIONS, horizontal=True, key="phpill_rep", label_visibility="collapsed")
    if sec == "Handover":
        report_card(user, role)
        _h("<div class='ph-sec'>Full handover view</div>")
        ctx.page_handover(user, role)  # not inside an expander: it has expanders of its own
    elif sec == "Review":
        ctx.page_review(user, role)
    elif sec == "Transfer":
        transfer_header()
        ctx.page_transfer(user, role)
    elif sec == "Checklist":
        checklist_header(user, role)
        ctx.page_checklist(user, role)
    else:
        screen_audit(ctx)


def tab_handover(user: str, role: str, ctx) -> None:
    report_card(user, role)
    _h("<div class='ph-sec'>Full handover view</div>")
    ctx.page_handover(user, role)  # not inside an expander: it has expanders of its own


def tab_checklist(user: str, role: str, ctx) -> None:
    checklist_header(user, role)
    ctx.page_checklist(user, role)


# ------------------------------------------------------------------ Profile, settings and their sub-screens

PROFILE_ROWS = [("👤", "Account & Permissions", "account"), ("🔔", "Notifications", "notifications"), ("🎨", "Appearance", "appearance"),
                ("🔒", "Privacy & Security", "privacy"), ("🐙", "GitHub Integration", "github"), ("❓", "Help & Support", "help")]

ROLE_INFO = {
    "Lead": "Sees every source and item. Can review, edit, approve and share the handover.",
    "Core": "Sees Everyone-level and Core-team sources. Can view the handover and accept transfers.",
    "Intern": "Sees Everyone-level sources only. Can view the handover and acknowledge it.",
}


def _open(tab: str | None = None, item: int | None = None, rep: str | None = None, screen: str | None = None,
          notes_open: bool = False, vmode: str | None = None) -> None:
    if notes_open:
        st.session_state["notes_open"] = True
        st.session_state.pop("ph_screen", None)
        st.rerun()
    if screen:
        st.session_state["ph_screen"] = screen
        st.rerun()
    if tab == "Verify" and item is None:
        st.session_state.pop("ph_item", None)
    _go(tab or "Overview", item=item, vmode=vmode, rep=rep)


def tab_profile(user: str, role: str, ctx, names: list) -> None:
    _h(title_html("Profile & Settings"))
    _h(f"<div class='ph-card ph-src'><div class='ph-avatar'>{_initial(user)}</div><div class='m'><b>{ui.esc(user)}</b>"
       f"<span class='ph-chip c-accent'>{ui.esc(role)}</span></div></div>")
    pick = st.selectbox("Signed in as (demo login)", names, index=names.index(user), key="ph_user_sel")
    if pick != user:
        st.session_state["ph_user"] = pick
        st.rerun()
    for icon, label, key in PROFILE_ROWS:
        if st.button(f"{icon} {label}   ›", key=f"row_prof_{key}", use_container_width=True):
            st.session_state["ph_screen"] = key
            st.rerun()
    if st.button(f"📝 My notes ({notes.count_open(user, role)})   ›", key="row_prof_notes", use_container_width=True):
        st.session_state["notes_open"] = True
        st.rerun()
    if st.button("Switch account", key="ph_switch"):
        st.session_state["ph_logged"] = False
        st.rerun()
    if st.button("Use the laptop view", key="ph_desk"):
        st.query_params["view"] = "desktop"
        st.rerun()
    if role == "Lead":
        with st.expander("Danger zone"):
            sure = st.checkbox("I understand this deletes all sources, items, handovers and the audit log", key="ph_sure")
            if st.button("Reset everything", key="ph_reset") and sure:
                db.reset_all()
                db.log(user, "reset", "all data")
                _flash("All data deleted")
                st.rerun()


def screen_account(user: str, role: str) -> None:
    _h(title_html("Account & Permissions"))
    _h(f"<div class='ph-card ph-src'><div class='ph-avatar'>{_initial(user)}</div><div class='m'><b>{ui.esc(user)}</b>"
       f"<span class='ph-chip c-accent'>{ui.esc(role)}</span></div></div>")
    rows = "".join(f"<div class='ph-act'><span><b style='color:var(--p-text)'>{ui.esc(r)}</b><br>{ui.esc(t)}</span></div>"
                   for r, t in ROLE_INFO.items())
    _h(f"<div class='ph-sec'>What each role can see</div><div class='ph-card'>{rows}</div>")
    st.caption("Demo roles only: this is not password or single sign-on security.")


def screen_privacy(user: str, role: str) -> None:
    _h(title_html("Privacy & Security"))
    pts = ["Secrets and personal data are masked before anything is stored or sent to an AI service.",
           "Every item must show an exact quote from its source (the Evidence Gate).",
           "Restricted material is removed before a reader's view, plan, export or PDF is built.",
           "Lines that look like instructions to an AI are flagged and treated as plain data.",
           "Every view, edit and approval goes in the audit log."]
    _h("<div class='ph-card'>" + "".join(f"<div class='ph-check'><span class='ph-tick'>✓</span>{ui.esc(p)}</div>" for p in pts) + "</div>")
    _h("<div class='ph-private'><span style='font-size:1.4rem'>🛡️</span>Your data stays private and secure.</div>")


def screen_github(user: str, role: str) -> None:
    _h(title_html("GitHub Integration", "Read-only: issues and commits are imported, nothing is ever written back."))
    if role == "Lead":
        if st.button("Import from GitHub", key="ph_ghgo", type="primary"):
            st.session_state["ph_add"] = True
            st.session_state["ph_addmode"] = "github"
            _go("Sources")
    else:
        st.caption("Only a Lead can add sources.")


def screen_help() -> None:
    _h(title_html("Help & Support", "The five steps"))
    steps = [("1", "Connect", "Upload notes, chats and tasks, or link a GitHub repository."),
             ("2", "Reconstruct", "Extract decisions, owners, blockers and risks."),
             ("3", "Verify", "Every item needs an exact quote from its source."),
             ("4", "Review", "A Lead approves, edits or rejects each item."),
             ("5", "Handover", "The incoming person reads a role-based plan and acknowledges it.")]
    _h("".join(f"<div class='ph-li' style='margin-bottom:.5rem'><div class='ph-av'>{n}</div><div class='m'><b>{t}</b><span>{d}</span></div></div>"
               for n, t, d in steps))
    st.caption("Tip: switch accounts in Profile to see what each role can see.")


def screen_appearance() -> None:
    """Screen 16: Light / Dark / System, accent colour, high contrast, reduce motion."""
    _h(title_html("Choose Your Look"))
    cur = current_theme()
    mode = "system" if cur == "system" else ("dark" if THEMES[cur]["dark"] else "light")
    _h("<div class='ph-sec'>Theme</div>")
    modes = {"light": "☀️ Light", "dark": "🌙 Dark", "system": "🖥️ System"}
    if st.session_state.get("phpill_mode_seen") != mode:  # theme changed elsewhere: re-sync, but never overwrite a fresh tap
        st.session_state["phpill_mode"] = mode
        st.session_state["phpill_mode_seen"] = mode
    pick = st.radio("Mode", list(modes), horizontal=True, key="phpill_mode", format_func=lambda k: modes[k], label_visibility="collapsed")
    if pick != mode:
        key = {"light": "showcase", "dark": "midnight", "system": "system"}[pick]
        st.session_state["ph_theme"] = key
        st.query_params["mt"] = key
        st.rerun()
    _h("<div class='ph-sec'>Accent Colour</div>")
    sel = pref("pa", "default")
    cols = st.columns(len(ACCENTS))
    for col, name in zip(cols, ACCENTS):
        if col.button("✓" if sel == name else "●", key=f"ph_acc_{name}"):
            set_pref("pa", name)
            st.rerun()
    if sel in ACCENTS and st.button("Reset accent colour", key="ph_resetacc"):
        set_pref("pa", "default")
        st.rerun()
    hc = pref("hc", "0") == "1"
    v = st.toggle("High Contrast", value=hc, key="ph_hc_t")
    if v != hc:
        set_pref("hc", "1" if v else "0")
        st.rerun()
    rm = pref("rm", "0") == "1"
    v = st.toggle("Reduce Motion", value=rm, key="ph_rm_t")
    if v != rm:
        set_pref("rm", "1" if v else "0")
        st.rerun()
    with st.expander("More themes"):
        keys = list(THEMES)
        base = cur if cur in keys else "showcase"
        if st.session_state.get("phpill_theme_seen") != base:
            st.session_state["phpill_theme"] = base
            st.session_state["phpill_theme_seen"] = base
        chosen = st.radio("Theme", keys, horizontal=True, key="phpill_theme", format_func=lambda k: THEMES[k]["name"], label_visibility="collapsed")
        t = THEMES[chosen]
        _h("<div class='ph-swatch'>" + "".join(f"<i style='background:{t[k]}'></i>" for k in ("bg", "surface", "accent", "good", "warn", "bad")) + "</div>")
        if chosen != base:
            st.session_state["ph_theme"] = chosen
            st.query_params["mt"] = chosen
            st.rerun()


def screen_notifications(user: str, role: str) -> None:
    """Screen 14: built from the real project state. Non-Leads only see counts, never titles of restricted items."""
    _h(title_html("Notifications"))
    cards = []  # (icon, title, sub, kwargs for _open)
    if role == "Lead":
        items = handover.list_items()
        for i in [i for i in items if i["is_conflict"] and i["review_status"] == "pending"][:3]:
            cards.append(("⚠️", "New conflict detected", _plain(i["text"])[:70], dict(tab="Verify", item=i["id"])))
        pend = sum(1 for i in items if i["review_status"] == "pending")
        if pend:
            cards.append(("🔔", "Reminder", f"Review {pend} pending item{'s' if pend != 1 else ''}", dict(tab="Report", rep="Review")))
    ho = handover.current_handover()
    if ho:
        target = dict(tab="Report", rep="Handover") if role == "Lead" else dict(tab="Handover")
        cards.append(("🔄", "Handover updated", f"v{ho['version']} approved by {ho['approved_by']}", target))
    ns = notes.stats(user, role)
    if ns.get("due"):
        cards.append(("⏰", "Notes due", f"{ns['due']} note{'s' if ns['due'] != 1 else ''} due or overdue", dict(notes_open=True)))
    if role == "Lead":
        for r in db.q("SELECT at, user_name, action, target FROM audit_log WHERE action LIKE '%transfer%' ORDER BY id DESC LIMIT 3"):
            cards.append(("✅", "Transfer activity", f"{r['user_name']}: {str(r['action']).replace('_', ' ')} {str(r['target'] or '')}"[:80],
                          dict(tab="Report", rep="Transfer")))
    if not cards:
        _h(empty_html("You're all caught up", "New conflicts, reminders and handover updates will show up here."))
        return
    for n, (icon, title, sub, kw) in enumerate(cards):
        if st.button(f"{icon} {title}\n{sub}", key=f"row_nt_{n}", use_container_width=True):
            _open(**kw)


def screen_menu(user: str, role: str) -> None:
    """Screen 18: every screen in one list."""
    _h(f"<div class='ph-card ph-src'><div class='ph-avatar'>{_initial(user)}</div><div class='m'><b>{ui.esc(user)}</b>"
       f"<span class='ph-chip c-accent'>{ui.esc(role)}</span></div></div>")
    if role == "Lead":
        entries = [("🏠", "Home", dict(tab="Overview")), ("🗂️", "Sources", dict(tab="Sources")),
                   ("🛡️", "Reconstruct & Verify", dict(tab="Verify", vmode="reconstruct")),
                   ("📄", "Handover report", dict(tab="Report", rep="Handover")), ("✅", "Review & approve", dict(tab="Report", rep="Review")),
                   ("🔁", "Transfer responsibilities", dict(tab="Report", rep="Transfer")),
                   ("☑️", "Departure checklist", dict(tab="Report", rep="Checklist")), ("🧾", "Audit log", dict(tab="Report", rep="Audit"))]
    else:
        entries = [("📄", "Handover", dict(tab="Handover")), ("☑️", "Departure checklist", dict(tab="Checklist"))]
    entries += [("📝", "My notes", dict(notes_open=True)), ("🔔", "Notifications", dict(screen="notifications")),
                ("🎨", "Appearance", dict(screen="appearance")), ("👤", "Profile & Settings", dict(tab="Profile"))]
    for n, (icon, label, kw) in enumerate(entries):
        if st.button(f"{icon} {label}", key=f"row_menu_{n}", use_container_width=True):
            _open(**kw)


def screen_overlay(name: str, user: str, role: str, ctx) -> None:
    if st.button("← Back", key="ph_ovback"):
        st.session_state.pop("ph_screen", None)
        st.rerun()
    if name == "notifications":
        screen_notifications(user, role)
    elif name == "appearance":
        screen_appearance()
    elif name == "account":
        screen_account(user, role)
    elif name == "privacy":
        screen_privacy(user, role)
    elif name == "github":
        screen_github(user, role)
    elif name == "help":
        screen_help()
    else:
        screen_menu(user, role)


# ------------------------------------------------------------------ entry point

def run(ctx) -> None:
    users = db.q("SELECT name, role FROM users ORDER BY id")
    names = [u["name"] for u in users]
    user = st.session_state.get("ph_user")
    if user not in names:
        user = names[0]
        st.session_state["ph_user"] = user
    role = next(u["role"] for u in users if u["name"] == user)
    prefs = themes.get_prefs(user)
    _h(ui.CSS)
    _h(themes.css_for(prefs))
    _h(theme_css(current_theme()))
    if pref("hc", "0") == "1":
        _h(f"<style>{HC_CSS}</style>")
    if pref("rm", "0") == "1":
        _h(f"<style>{RM_CSS}</style>")
    if prefs["splash"] == "1" and prefs["motion"] == "0" and not st.session_state.get("splash_shown"):
        st.session_state["splash_shown"] = True
        _h(splash.markup())
    if WELCOME and not st.session_state.get("ph_started") and not st.session_state.get("ph_logged"):
        welcome_screen()
        return
    if not st.session_state.get("ph_logged"):  # next: choose your account
        login_screen(users)
        return
    if st.session_state.get("last_user") != user:
        db.log(user, "switch_user", role)
        st.session_state["last_user"] = user
    tabs = LEAD_TABS if role == "Lead" else OTHER_TABS
    goto = st.session_state.pop("ph_goto", None)
    if goto in tabs:
        st.session_state["phnav"] = goto
        st.session_state["ph_last_tab"] = goto
    if st.session_state.get("phnav") not in tabs:
        st.session_state["phnav"] = tabs[0]
    tab = st.radio("Navigate", tabs, key="phnav", horizontal=True, format_func=lambda k: NAV[k], label_visibility="collapsed")
    if st.session_state.get("ph_last_tab") != tab:
        for k in ("ph_item", "notes_open", "ph_add", "ph_addmode", "ph_screen", "ph_vmode"):
            st.session_state.pop(k, None)
        st.session_state["ph_last_tab"] = tab
    msg = st.session_state.pop("flash", None)
    if msg:
        st.toast(msg)
    header_block()
    if st.session_state.get("notes_open"):
        ctx.notes_page(user, role)
    elif st.session_state.get("ph_screen"):
        screen_overlay(st.session_state["ph_screen"], user, role, ctx)
    elif tab == "Overview":
        tab_overview(user, role, ctx)
    elif tab == "Sources":
        tab_sources(user, role, ctx)
    elif tab == "Verify":
        tab_verify(user, role, ctx)
    elif tab == "Report":
        tab_report(user, role, ctx)
    elif tab == "Handover":
        tab_handover(user, role, ctx)
    elif tab == "Checklist":
        tab_checklist(user, role, ctx)
    else:
        tab_profile(user, role, ctx, names)
