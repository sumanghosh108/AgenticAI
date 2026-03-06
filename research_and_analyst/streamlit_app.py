"""
Streamlit Frontend — Autonomous Research Report Generator

Run with: streamlit run research_and_analyst/streamlit_app.py

This file is a thin router. All logic lives in:
  - ui/styles.py      → CSS injection
  - ui/helpers.py      → API calls, Google OAuth callback
  - ui/pages/login.py  → Login page
  - ui/pages/signup.py → Signup page
  - ui/pages/dashboard.py → Dashboard
  - ui/pages/report.py    → Report progress & download
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── Ensure imports resolve & .env is loaded ──
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
load_dotenv(os.path.join(_project_root, ".env"), override=True)

import streamlit as st

# ── Page config (must be first Streamlit call) ──
st.set_page_config(
    page_title="AgenticAI — Research Report Generator",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Session state defaults ──
for key, default in {
    "logged_in": False,
    "username": "",
    "page": "login",
    "thread_id": None,
    "topic": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Handle Google OAuth redirect (must run before pages) ──
from research_and_analyst.ui.helpers import handle_google_callback  # noqa: E402
handle_google_callback()

# ── Import page modules ──
from research_and_analyst.ui.pages import login, signup, dashboard, report  # noqa: E402


# ── Router ──
def main():
    if not st.session_state.logged_in:
        if st.session_state.page == "signup":
            signup.render()
        else:
            login.render()
    else:
        if st.session_state.page == "report":
            report.render()
        else:
            dashboard.render()


if __name__ == "__main__":
    main()
