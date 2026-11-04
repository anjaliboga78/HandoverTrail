"""Phone layout that behaves like a real app: slim header, progress strip, bottom tab bar, tile cards, big tap targets.
Everything here applies only on narrow screens, so the laptop view and all 20 themes stay exactly as they are."""
import streamlit as st

import ui

TAG = "Knowledge stays when people go"
STEP_NAMES = ["Connect", "Reconstruct", "Verify", "Review", "Handover"]

CSS = """
<style>
footer, [data-testid="stDecoration"] { display: none !important; }
.ht-m-only { display: none !important; }

@media (max-width: 700px) {
  html, body, .stApp { overflow-x: hidden !important; }
  [data-testid="stToolbar"] { display: none !important; }
  .block-container { padding: 3.4rem 0.75rem 7rem !important; max-width: 100% !important; }
  img, svg, video { max-width: 100% !important; height: auto; }
  .stMarkdown, .stCaption { overflow-wrap: anywhere; }
  [data-testid="stVerticalBlock"] { gap: 0.8rem !important; }

  /* swap the big laptop header and stepper for the slim phone ones */
  .ht-d-only { display: none !important; }
  [data-testid="stElementContainer"]:has(.ht-d-only), [data-testid="element-container"]:has(.ht-d-only) { display: none !important; }
  .ht-bar { display: flex !important; align-items: center; gap: 0.6rem; background: var(--card, #fff);
            border: 2px solid var(--ink, #222); border-radius: 14px; padding: 0.5rem 0.7rem;
            box-shadow: 3px 3px 0 var(--teal, #1d8a8a); }
  .ht-bar img { width: 34px; height: 34px; border-radius: 8px; flex: 0 0 auto; }
  .ht-bar .t { flex: 1 1 auto; min-width: 0; line-height: 1.1; }
  .ht-bar .t b { display: block; font-family: var(--hand, var(--serif, serif)); font-size: 1.35rem; color: var(--ink, #222); }
  .ht-bar .t span { display: block; font-size: 0.72rem; color: var(--muted, #777); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .ht-bar .chip { flex: 0 1 auto; max-width: 42%; padding: 0.25rem 0.6rem; border: 2px solid var(--ink, #222); border-radius: 999px;
                  background: var(--teal, #1d8a8a); color: #fff; font-size: 0.75rem; font-weight: 700; white-space: nowrap;
                  overflow: hidden; text-overflow: ellipsis; }
  .ht-prog { display: block !important; }
  .ht-prog .row { display: flex; justify-content: space-between; font-size: 0.8rem; font-weight: 700; color: var(--ink, #222); margin-bottom: 0.3rem; }
  .ht-prog .segs { display: flex; gap: 4px; }
  .ht-prog .segs i { flex: 1; height: 8px; border-radius: 99px; background: rgba(0,0,0,.12); border: 1px solid var(--ink, #222); }
  .ht-prog .segs i.on { background: var(--teal, #1d8a8a); }
  .ht-prog .segs i.cur { background: var(--red, #d9534f); }

  h1 { font-size: 1.45rem !important; line-height: 1.2 !important; }
  h2 { font-size: 1.2rem !important; line-height: 1.25 !important; margin-top: 0.2rem !important; }
  h3 { font-size: 1.05rem !important; }

  /* columns stack, number cards become tiles two per row */
  div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 0.6rem !important; }
  div[data-testid="stColumn"] { min-width: 100% !important; flex: 1 1 100% !important; width: 100% !important; }
  div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMetric"]) > div[data-testid="stColumn"] {
    min-width: calc(50% - 0.4rem) !important; flex: 1 1 calc(50% - 0.4rem) !important; width: auto !important; }
  div[data-testid="stMetric"] { background: var(--card, #fff); border: 2px solid var(--ink, #222); border-radius: 12px; padding: 0.45rem 0.7rem; }
  div[data-testid="stMetricValue"] { font-size: 1.4rem !important; }
  div[data-testid="stMetricLabel"] { font-size: 0.78rem !important; }

  /* controls: big, thumb friendly (16px stops iPhone auto-zoom) */
  .stButton > button, .stDownloadButton > button { width: 100% !important; min-height: 50px !important; font-size: 1.02rem !important; border-radius: 12px !important; }
  input, textarea, div[data-baseweb="select"] { font-size: 16px !important; }
  div[data-testid="stFileUploaderDropzone"] { flex-direction: column !important; gap: 0.6rem !important; }
  div[data-testid="stExpander"] { border-radius: 12px !important; }
  div[data-testid="stExpander"] summary { padding: 0.75rem 0.6rem !important; }
  div[data-testid="stToast"], [data-testid="stToastContainer"] { bottom: 5.2rem !important; }

  /* tables and tabs scroll sideways instead of breaking the page */
  div[data-testid="stDataFrame"], div[data-testid="stDataEditor"], div[data-testid="stTable"] { overflow-x: auto !important; }
  pre, code { white-space: pre-wrap !important; }
  div[data-baseweb="tab-list"] { overflow-x: auto !important; flex-wrap: nowrap !important; scrollbar-width: none; }
  .stMarkdown table { display: block; overflow-x: auto; }

  /* BOTTOM TAB BAR: the workflow radio (key starts with nav_) */
  [class*="st-key-nav_"] {
    position: fixed !important; left: 0; right: 0; bottom: 0; z-index: 999; margin: 0 !important; width: 100% !important;
    background: var(--card, #fff); border-top: 2px solid var(--ink, #222); box-shadow: 0 -4px 14px rgba(0,0,0,.12);
    padding: 0.45rem 0.5rem calc(0.45rem + env(safe-area-inset-bottom, 0px)) !important; }
  [class*="st-key-nav_"] div[role="radiogroup"] {
    flex-wrap: nowrap !important; overflow-x: auto; gap: 0.35rem !important; scrollbar-width: none; scroll-snap-type: x proximity; }
  [class*="st-key-nav_"] div[role="radiogroup"]::-webkit-scrollbar { display: none; }
  [class*="st-key-nav_"] label {
    flex: 0 0 auto; margin: 0 !important; padding: 0.35rem 0.9rem; min-height: 44px; align-items: center; scroll-snap-align: center;
    border: 2px solid transparent; border-radius: 999px; }
  [class*="st-key-nav_"] label > div:first-child { display: none !important; }
  [class*="st-key-nav_"] label p { font-size: 0.86rem !important; font-weight: 700; white-space: nowrap; margin: 0; }
  [class*="st-key-nav_"] label:has(input:checked) { background: var(--teal, #1d8a8a); border-color: var(--ink, #222); }
  [class*="st-key-nav_"] label:has(input:checked) p { color: #fff !important; }

  /* short drawer: account, notes, appearance */
  section[data-testid="stSidebar"] { width: 80vw !important; min-width: 0 !important; max-width: 320px !important; }
  [data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] button {
    background: var(--teal, #1d8a8a) !important; color: #fff !important; border-radius: 999px !important;
    min-width: 44px; min-height: 44px; box-shadow: 0 2px 8px rgba(0,0,0,.25); }
  [data-testid="stExpandSidebarButton"] svg, [data-testid="stSidebarCollapsedControl"] svg { fill: #fff !important; color: #fff !important; }
}
</style>
"""


def apply() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def header_html(user: str, role: str) -> str:
    """Slim app bar for phones (hidden on laptops by CSS)."""
    icon = ui.asset_uri("icon.png")
    img = f"<img src='{icon}' alt=''>" if icon else ""
    return (f"<div class='ht-m-only ht-bar'>{img}<div class='t'><b>HandoverTrail</b><span>{ui.esc(TAG)}</span></div>"
            f"<div class='chip'>{ui.esc(user)} &middot; {ui.esc(role)}</div></div>")


def progress_html(done: dict, current: str) -> str:
    """Thin five-segment progress strip for phones (hidden on laptops by CSS)."""
    segs = "".join(f"<i class='{'on' if done.get(n) else ('cur' if n == current else '')}'></i>" for n in STEP_NAMES)
    n = STEP_NAMES.index(current) + 1 if current in STEP_NAMES else 1
    return (f"<div class='ht-m-only ht-prog'><div class='row'><span>Step {n} of {len(STEP_NAMES)}</span>"
            f"<span>{ui.esc(current)}</span></div><div class='segs'>{segs}</div></div>")
