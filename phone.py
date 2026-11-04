"""HandoverTrail phone app mode: a native-app style UI (bottom tabs, readiness ring, tiles, verification card).

Opened automatically on phones (?view=phone). It reuses the same database and core logic as the laptop view, so nothing
about the data, roles or the Evidence Gate changes. The default look ("Showcase") follows the app-flow design:
lavender background, indigo buttons, pastel tiles. Other themes: Midnight, Ocean, Graphite, Daylight, Mint, Sunset,
Minimal, Minimal dark, Mono.
"""
from __future__ import annotations

import re

import streamlit as st

import splash
import ui
from core import config, db, extract, flags, handover, ingest, notes, readiness, themes
from ui import STATUS_TEXT, type_label

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
.ph-bell { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 50%; background: var(--p-surface); border: 1px solid var(--p-border); font-size: 1.05rem; }
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
.ph-act span:last-child { color: var(--p-muted); white-space: nowrap; }
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
"""


def theme_css(key: str) -> str:
    t = THEMES[key]
    v = (f"--p-bg:{t['bg']};--p-surface:{t['surface']};--p-surface2:{t['surface2']};--p-border:{t['border']};"
         f"--p-text:{t['text']};--p-muted:{t['muted']};--p-accent:{t['accent']};--p-on:{t['on']};"
         f"--p-good:{t['good']};--p-warn:{t['warn']};--p-bad:{t['bad']};--p-font:{FONT};")
    legacy = (f"--paper:{t['bg']};--ink:{t['text']};--card:{t['surface']};--teal:{t['accent']};--red:{t['bad']};--muted:{t['muted']};"
              f"--yellow:{t['surface2']};--green:{t['surface2']};--blue:{t['surface2']};--pink:{t['surface2']};"
              f"--serif:{FONT};--hand:{FONT};--hs:.78;--bgimg:none;--bgsize:auto;")
    dark = "color-scheme:dark;" if t["dark"] else "color-scheme:light;"
    extra = ('[data-testid="stDataFrame"],[data-testid="stDataEditor"]{filter:invert(.92) hue-rotate(180deg);}' if t["dark"] else "")
    if key == "showcase":
        extra += ".stApp{background:linear-gradient(180deg,#e8e7ff 0%,#f5f4ff 40%,#ffffff 100%) !important;}"
    return f"<style>html body .stApp, html body [data-testid='stAppViewContainer']{{{v}{legacy}{dark}}}{STATIC_CSS}{extra}</style>"


def current_theme() -> str:
    key = st.query_params.get("mt") or st.session_state.get("ph_theme") or DEFAULT_THEME
    return key if key in THEMES else DEFAULT_THEME


# ------------------------------------------------------------------ small helpers
def _h(s: str) -> None:
    st.markdown(s, unsafe_allow_html=True)


def _plain(s) -> str:
    return re.sub(r"[*_`\[\]~#<>]", "", str(s)).strip()


def _go(tab: str, item: int | None = None) -> None:
    st.session_state["ph_goto"] = tab
    if item is not None:
        st.session_state["ph_item"] = item
    st.rerun()


def _flash(msg: str) -> None:
    st.session_state["flash"] = msg


STATUS_EMOJI = {"verified": "✅", "approximate": "🟡", "unverified": "🔴"}
VIS_CLASS = {"Everyone": "c-accent", "Core": "c-warn", "Lead": "c-good"}
NAV = {"Overview": "🏠\nHome", "Sources": "🗂️\nSources", "Verify": "🛡️\nVerify", "Report": "📄\nReport",
       "Handover": "📄\nHandover", "Checklist": "☑️\nChecklist", "Profile": "👤\nProfile"}
LEAD_TABS = ["Overview", "Sources", "Verify", "Report", "Profile"]
OTHER_TABS = ["Handover", "Checklist", "Profile"]


def ring_svg(score: int, color: str) -> str:
    r = 44
    c = 2 * 3.14159 * r
    off = c * (1 - max(0, min(100, score)) / 100)
    return (f"<svg viewBox='0 0 120 120'><circle cx='60' cy='60' r='{r}' fill='none' stroke='var(--p-surface2)' stroke-width='10'/>"
            f"<circle cx='60' cy='60' r='{r}' fill='none' stroke='{color}' stroke-width='10' stroke-linecap='round' "
            f"stroke-dasharray='{c:.1f}' stroke-dashoffset='{off:.1f}' transform='rotate(-90 60 60)'/>"
            f"<text x='60' y='64' text-anchor='middle' font-size='24' font-weight='800' fill='var(--p-text)'>{int(score)}%</text>"
            f"<text x='60' y='80' text-anchor='middle' font-size='9' fill='var(--p-muted)'>Readiness</text></svg>")


def header_html() -> str:
    icon = ui.asset_uri("icon.png")
    img = f"<img src='{icon}' alt=''>" if icon else "<span style='font-size:1.6rem'>🤝</span>"
    return (f"<div class='ph-top'><div class='ph-brand'>{img}<b>HandoverTrail</b></div>"
            f"<span class='ph-bell' title='{ui.esc(readiness.status_flow())}'>🔔</span></div>")


def title_html(title: str, sub: str = "") -> str:
    return f"<div class='ph-h'>{ui.esc(title)}</div>" + (f"<div class='ph-sub'>{ui.esc(sub)}</div>" if sub else "")


def empty_html(title: str, text: str) -> str:
    return f"<div class='ph-card ph-empty'><b>{ui.esc(title)}</b>{ui.esc(text)}</div>"


def severity(it: dict) -> int:
    if it["is_conflict"]:
        return 0
    if it["verify_status"] == "unverified":
        return 1
    if it["is_gap"]:
        return 2
    return 3


def run_extraction_button(user: str, ctx, key: str) -> None:
    pending = db.q("SELECT COUNT(*) AS n FROM sources WHERE extracted=0")[0]["n"]
    if pending and st.button(f"Run extraction ({pending} new source{'s' if pending != 1 else ''})", key=key, type="primary"):
        with st.spinner("Reading sources and checking every quote..."):
            result = extract.run_extraction(user, provider=ctx.provider())
        for w in result["warnings"]:
            st.warning(w)
        _flash(f"Found {result['items']} items in {result['sources']} source(s)")
        st.rerun()


# ------------------------------------------------------------------ Login (choose your account)
def login_screen(users: list) -> None:
    logo = ui.asset_uri("logo.png")
    img = f"<img src='{logo}' alt='HandoverTrail logo'>" if logo else "<h1>HandoverTrail</h1>"
    _h(f"<div class='ph-login'>{img}</div>")
    _h("<div class='ph-sec'>Choose your account</div>")
    names = [u["name"] for u in users]
    sel = st.session_state.get("ph_pick") or names[0]
    for i, u in enumerate(users):
        mark = "✔  " if u["name"] == sel else "👤  "
        if st.button(f"{mark}{u['name']}\n{u['role']}", key=f"row_login_{i}", use_container_width=True):
            st.session_state["ph_pick"] = u["name"]
            st.rerun()
    if st.button("Continue  →", key="ph_continue", type="primary"):
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
        _go("Verify")

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
    if st.button("←  Choose another way", key="ph_addback"):
        st.session_state["ph_addmode"] = None
        st.rerun()


def add_panel(user: str, ctx) -> None:
    mode = st.session_state.get("ph_addmode")
    if not mode:
        _h("<div class='ph-sec'>Add Source</div>")
        for key, label in (("upload", "📄  Upload Files\n(.txt, .md, .csv)"), ("github", "🐙  Import GitHub\n(Repo or Issues)"),
                           ("paste", "📝  Paste Notes\n(With AI Analysis)"), ("demo", "🧪  Demo project\n(Made-up club app)")):
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
        query = st.text_input("Search sources", placeholder="🔍  Search sources...", key="ph_srcq", label_visibility="collapsed")
    else:
        query = ""
    if st.button("Close" if adding else "＋  Add Source", key="ph_addbtn", type="secondary" if adding else "primary"):
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


# ------------------------------------------------------------------ Verify
MEANING = {
    "verified": "The quote was found word for word in the source. No action needed.",
    "approximate": "The quote differs by a few words from the source. Check it, then mark it as reviewed.",
    "unverified": "The quote was not found in the source, so it is not treated as fact. Check the source yourself before approving.",
}


def verify_detail(it: dict, lookup: dict, user: str, role: str) -> None:
    if st.button("←  Back to list", key="ph_back"):
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
    _h(f"<div class='ph-chips'>{chips}</div>")
    _h(f"<div class='ph-quote'>“{ui.esc(it['quote'])}”</div>")
    _h(f"<div class='ph-muted'>📄 {ui.esc(it['source_name'])} · {ui.esc(it['item_date'] or it.get('source_date') or 'undated')} · "
       f"{ui.esc(type_label(it['type']))} · review: {ui.esc(it['review_status'])}</div>")
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
        if st.button("✓  Mark as reviewed", key=f"phap{it['id']}", type="primary"):
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


def tab_verify(user: str, role: str, ctx) -> None:
    items = handover.list_items()
    if not items:
        _h(title_html("Verification", "Every item is checked against its source quote."))
        _h(empty_html("Nothing to verify yet", "Add sources, then run extraction."))
        run_extraction_button(user, ctx, "ph_ext3")
        return
    lookup = {i["id"]: i for i in items}
    sel = st.session_state.get("ph_item")
    if sel in lookup:
        verify_detail(lookup[sel], lookup, user, role)
        return
    _h(title_html("Verification"))
    flt = st.radio("Filter", [f"All ({len(items)})", "Verified", "Approximate", "Unverified", "Conflicts"], horizontal=True,
                   key="phpill_vf", label_visibility="collapsed")
    shown = [i for i in items if flt.startswith("All") or (flt == "Verified" and i["verify_status"] == "verified")
             or (flt == "Approximate" and i["verify_status"] == "approximate")
             or (flt == "Unverified" and i["verify_status"] == "unverified") or (flt == "Conflicts" and i["is_conflict"])]
    st.caption(f"{len(shown)} of {len(items)} items")
    for i in shown:
        sub = f"{STATUS_TEXT[i['verify_status']]} · {type_label(i['type'])} · {i['source_name']}"
        if st.button(f"{STATUS_EMOJI[i['verify_status']]} {_plain(i['text'])[:75]}\n{_plain(sub)[:80]}", key=f"row_it_{i['id']}", use_container_width=True):
            st.session_state["ph_item"] = i["id"]
            st.rerun()


# ------------------------------------------------------------------ Report
def tab_report(user: str, role: str, ctx) -> None:
    _h(title_html("Report", "Review, hand over, transfer and close out."))
    sections = ["Handover", "Review", "Transfer", "Checklist", "Audit"]
    sec = st.radio("Section", sections, horizontal=True, key="phpill_rep", label_visibility="collapsed")
    {"Handover": ctx.page_handover, "Review": ctx.page_review, "Transfer": ctx.page_transfer,
     "Checklist": ctx.page_checklist}.get(sec, lambda u, r: ctx.page_audit())(user, role)


# ------------------------------------------------------------------ Profile
def tab_profile(user: str, role: str, ctx, names: list) -> None:
    _h(title_html("Profile & Settings"))
    _h(f"<div class='ph-card ph-src'><div class='ph-avatar'>{ui.esc(user[:1].upper())}</div><div class='m'><b>{ui.esc(user)}</b>"
       f"<span class='ph-chip c-accent'>{ui.esc(role)}</span></div></div>")
    pick = st.selectbox("Signed in as (demo login)", names, index=names.index(user), key="ph_user_sel")
    if pick != user:
        st.session_state["ph_user"] = pick
        st.rerun()

    _h("<div class='ph-sec'>🎨 Appearance</div>")
    keys = list(THEMES)
    cur = current_theme()
    chosen = st.radio("Theme", keys, index=keys.index(cur), horizontal=True, key="phpill_theme",
                      format_func=lambda k: THEMES[k]["name"], label_visibility="collapsed")
    t = THEMES[chosen]
    _h("<div class='ph-swatch'>" + "".join(f"<i style='background:{t[k]}'></i>" for k in ("bg", "surface", "accent", "good", "warn", "bad")) + "</div>")
    if chosen != cur:
        st.session_state["ph_theme"] = chosen
        st.query_params["mt"] = chosen
        st.rerun()

    _h("<div class='ph-sec'>📝 Notes and tools</div>")
    if st.button(f"My notes ({notes.count_open(user, role)})", key="ph_notes"):
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
    if prefs["splash"] == "1" and prefs["motion"] == "0" and not st.session_state.get("splash_shown"):
        st.session_state["splash_shown"] = True
        _h(splash.markup())

    if not st.session_state.get("ph_logged"):      # first screen after the splash: choose your account
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
        for k in ("ph_item", "notes_open", "ph_add", "ph_addmode"):
            st.session_state.pop(k, None)
        st.session_state["ph_last_tab"] = tab

    msg = st.session_state.pop("flash", None)
    if msg:
        st.toast(msg)
    _h(header_html())

    if st.session_state.get("notes_open"):
        ctx.notes_page(user, role)
    elif tab == "Overview":
        tab_overview(user, role, ctx)
    elif tab == "Sources":
        tab_sources(user, role, ctx)
    elif tab == "Verify":
        tab_verify(user, role, ctx)
    elif tab == "Report":
        tab_report(user, role, ctx)
    elif tab == "Handover":
        ctx.page_handover(user, role)
    elif tab == "Checklist":
        ctx.page_checklist(user, role)
    else:
        tab_profile(user, role, ctx, names)
