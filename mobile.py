"""Phone layout: behaves like a real app. A bottom tab bar for the workflow, a short drawer for account and look,
compact cards, big tap targets. Applies only on narrow screens, so the laptop view and all 20 themes stay the same."""
import streamlit as st

CSS = """
<style>
footer, [data-testid="stDecoration"] { display: none !important; }

@media (max-width: 700px) {
  html, body, .stApp { overflow-x: hidden !important; }
  [data-testid="stToolbar"] { display: none !important; }
  .block-container { padding: 3rem 0.8rem 6.5rem !important; max-width: 100% !important; }
  .stMarkdown, .stCaption, [data-testid="stMetric"] { overflow-wrap: anywhere; }
  img, svg, video { max-width: 100% !important; height: auto; }

  h1 { font-size: 1.5rem !important; line-height: 1.2 !important; }
  h2 { font-size: 1.25rem !important; line-height: 1.25 !important; }
  h3 { font-size: 1.05rem !important; }

  /* columns stack, number cards sit two per row */
  div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 0.6rem !important; }
  div[data-testid="stColumn"] { min-width: 100% !important; flex: 1 1 100% !important; width: 100% !important; }
  div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMetric"]) > div[data-testid="stColumn"] {
    min-width: calc(50% - 0.4rem) !important; flex: 1 1 calc(50% - 0.4rem) !important; width: auto !important; }
  div[data-testid="stMetricValue"] { font-size: 1.4rem !important; }
  div[data-testid="stMetricLabel"] { font-size: 0.8rem !important; }

  /* easy-to-tap controls (16px stops iPhone auto-zoom) */
  .stButton > button, .stDownloadButton > button { width: 100% !important; min-height: 48px !important; font-size: 1.02rem !important; }
  input, textarea, div[data-baseweb="select"] { font-size: 16px !important; }
  div[data-testid="stFileUploaderDropzone"] { flex-direction: column !important; gap: 0.6rem !important; }
  div[data-testid="stExpander"] summary { padding: 0.7rem 0.5rem !important; }

  /* tables and tabs scroll sideways instead of breaking the page */
  div[data-testid="stDataFrame"], div[data-testid="stDataEditor"], div[data-testid="stTable"] { overflow-x: auto !important; }
  pre, code { white-space: pre-wrap !important; }
  div[data-baseweb="tab-list"] { overflow-x: auto !important; flex-wrap: nowrap !important; scrollbar-width: none; }
  .stMarkdown table { display: block; overflow-x: auto; }

  /* BOTTOM TAB BAR: the workflow radio (key starts with nav_) becomes a fixed app-style bar */
  [class*="st-key-nav_"] {
    position: fixed !important; left: 0; right: 0; bottom: 0; z-index: 999; margin: 0 !important; width: 100% !important;
    background: var(--card, #fff); border-top: 2px solid var(--ink, #222);
    padding: 0.4rem 0.5rem calc(0.4rem + env(safe-area-inset-bottom, 0px)) !important; }
  [class*="st-key-nav_"] div[role="radiogroup"] {
    flex-wrap: nowrap !important; overflow-x: auto; gap: 0.35rem !important; scrollbar-width: none; }
  [class*="st-key-nav_"] div[role="radiogroup"]::-webkit-scrollbar { display: none; }
  [class*="st-key-nav_"] label {
    flex: 0 0 auto; margin: 0 !important; padding: 0.35rem 0.85rem; min-height: 42px; align-items: center;
    border: 2px solid transparent; border-radius: 999px; }
  [class*="st-key-nav_"] label > div:first-child { display: none !important; }
  [class*="st-key-nav_"] label p { font-size: 0.85rem !important; font-weight: 700; white-space: nowrap; margin: 0; }
  [class*="st-key-nav_"] label:has(input:checked) { background: var(--teal, #1d8a8a); border-color: var(--ink, #222); }
  [class*="st-key-nav_"] label:has(input:checked) p { color: #fff !important; }

  /* short drawer: just account, notes, appearance */
  section[data-testid="stSidebar"] { width: 80vw !important; min-width: 0 !important; max-width: 320px !important; }
  section[data-testid="stSidebar"] .block-container, section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    padding-top: 1rem !important; }
  [data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] button {
    background: var(--teal, #1d8a8a) !important; color: #fff !important; border-radius: 999px !important;
    min-width: 44px; min-height: 44px; box-shadow: 0 2px 8px rgba(0,0,0,.25); }
  [data-testid="stExpandSidebarButton"] svg, [data-testid="stSidebarCollapsedControl"] svg { fill: #fff !important; color: #fff !important; }
}
</style>
"""


def apply() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
