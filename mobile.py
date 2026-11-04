"""Phone-friendly layout. Applies only on narrow screens, so the laptop view and all 20 themes stay the same."""
import streamlit as st

CSS = """
<style>
@media (max-width: 700px) {
  html, body, .stApp { overflow-x: hidden !important; }
  .block-container { padding: 3.2rem 0.9rem 4rem !important; max-width: 100% !important; }
  * { overflow-wrap: anywhere; }
  img, svg, video { max-width: 100% !important; height: auto; }

  /* headings and text */
  h1 { font-size: 1.55rem !important; line-height: 1.2 !important; }
  h2 { font-size: 1.3rem !important; line-height: 1.25 !important; }
  h3 { font-size: 1.1rem !important; }
  p, li, label, .stMarkdown, .stCaption { font-size: 1rem !important; line-height: 1.5 !important; }

  /* columns stack, number cards sit two per row */
  div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 0.7rem !important; }
  div[data-testid="stColumn"] { min-width: 100% !important; flex: 1 1 100% !important; width: 100% !important; }
  div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMetric"]) > div[data-testid="stColumn"] {
    min-width: calc(50% - 0.5rem) !important; flex: 1 1 calc(50% - 0.5rem) !important; width: auto !important; }
  div[data-testid="stMetricValue"] { font-size: 1.5rem !important; }
  div[data-testid="stMetricLabel"] { font-size: 0.85rem !important; }

  /* easy-to-tap controls (16px stops iPhone auto-zoom) */
  .stButton > button, .stDownloadButton > button { width: 100% !important; min-height: 48px !important; font-size: 1.05rem !important; }
  input, textarea, div[data-baseweb="select"] { font-size: 16px !important; }
  div[data-testid="stFileUploader"] section { padding: 1rem !important; }
  div[data-testid="stFileUploaderDropzone"] { flex-direction: column !important; gap: 0.6rem !important; }
  div[role="radiogroup"] { gap: 0.4rem !important; }
  div[data-testid="stExpander"] summary { font-size: 1rem !important; padding: 0.75rem 0.5rem !important; }

  /* tables scroll sideways instead of breaking the page */
  div[data-testid="stDataFrame"], div[data-testid="stDataEditor"], div[data-testid="stTable"] { overflow-x: auto !important; }
  pre, code { white-space: pre-wrap !important; }

  /* tabs scroll sideways */
  div[data-baseweb="tab-list"] { overflow-x: auto !important; flex-wrap: nowrap !important; }

  /* your own cards and callouts */
  .start { padding: 0.9rem !important; font-size: 1rem !important; }
  .stMarkdown div, .stMarkdown table { max-width: 100% !important; }
  .stMarkdown table { display: block; overflow-x: auto; }

  /* sidebar: wide enough to read, and a big visible open button so new people find the menu */
  section[data-testid="stSidebar"] { width: 86vw !important; min-width: 0 !important; max-width: 340px !important; }
  [data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] button {
    background: var(--teal, #1d8a8a) !important; color: #fff !important; border-radius: 999px !important;
    min-width: 44px; min-height: 44px; box-shadow: 0 2px 8px rgba(0,0,0,.25); }
  [data-testid="stExpandSidebarButton"] svg, [data-testid="stSidebarCollapsedControl"] svg { fill: #fff !important; color: #fff !important; }
}
</style>
"""


def apply() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
