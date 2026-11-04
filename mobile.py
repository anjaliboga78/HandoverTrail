"""Phone-friendly layout. Only applies on narrow screens, so the laptop view stays the same."""
import streamlit as st

CSS = """
<style>
@media (max-width: 640px) {
  .block-container { padding: 1rem 0.9rem 4rem !important; max-width: 100% !important; }
  h1 { font-size: 1.6rem !important; line-height: 1.2 !important; }
  h2 { font-size: 1.35rem !important; }
  h3 { font-size: 1.15rem !important; }
  p, li, label, .stMarkdown { font-size: 1rem !important; line-height: 1.5 !important; }

  /* columns stack one under another */
  div[data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 0.7rem !important; }
  div[data-testid="stColumn"] { min-width: 100% !important; flex: 1 1 100% !important; }

  /* number cards (Items, Verified...) sit two per row */
  div[data-testid="stHorizontalBlock"]:has(div[data-testid="stMetric"]) > div[data-testid="stColumn"] {
    min-width: calc(50% - 0.5rem) !important; flex: 1 1 calc(50% - 0.5rem) !important; }

  /* big, easy-to-tap buttons and inputs (16px stops iPhone auto-zoom) */
  .stButton > button, .stDownloadButton > button { width: 100% !important; min-height: 48px !important; font-size: 1.05rem !important; }
  input, textarea, div[data-baseweb="select"] { font-size: 16px !important; }
  div[data-testid="stFileUploader"] section { padding: 1rem !important; }

  /* tables scroll sideways instead of breaking the page */
  div[data-testid="stDataFrame"], div[data-testid="stDataEditor"], div[data-testid="stTable"] { overflow-x: auto !important; }
  div[data-testid="stExpander"] summary { font-size: 1rem !important; padding: 0.7rem 0.5rem !important; }
  .start { padding: 0.9rem !important; }
}
</style>
"""


def apply() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
