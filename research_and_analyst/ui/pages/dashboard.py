"""Dashboard page for AgenticAI."""

import streamlit as st

from research_and_analyst.ui.styles import inject_dashboard_css
from research_and_analyst.ui.helpers import api_post


def render():
    """Render the main dashboard."""
    inject_dashboard_css()

    # ── Header row ──
    col_title, col_user = st.columns([4, 1])
    with col_title:
        st.markdown(
            '<p class="dash-title">🔬 AgenticAI Dashboard</p>',
            unsafe_allow_html=True,
        )
    with col_user:
        st.markdown(f"**👤 {st.session_state.username}**")
        if st.button("Logout", key="logout_btn"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.page = "login"
            st.session_state.thread_id = None
            st.rerun()

    st.divider()

    # ── Generate Report Card ──
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### 📄 Generate Research Report")
    st.markdown(
        "Enter a topic and our AI analysts will research and "
        "produce a comprehensive report."
    )

    topic = st.text_input(
        "Research Topic",
        placeholder="e.g., Impact of AI on Healthcare in 2026",
        key="topic_input",
    )

    # Analyst count (7/8) + Generate button (1/8) in one row
    col_slider, col_btn = st.columns([7, 1])
    with col_slider:
        max_analysts = st.slider(
            "Number of Analyst Personas",
            min_value=1, max_value=5, value=3,
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        generate_clicked = st.button(
            "🚀 Generate", use_container_width=True, key="gen_btn",
        )

    if generate_clicked:
        if not topic:
            st.error("Please enter a research topic")
        else:
            with st.spinner("Initiating report pipeline... This may take a few minutes."):
                result = api_post("generate_report", {
                    "topic": topic,
                    "max_analysts": max_analysts,
                })
            if result.get("success"):
                st.session_state.thread_id = result.get("thread_id")
                st.session_state.topic = topic
                st.success(
                    f"✅  Pipeline started! Thread ID: `{result.get('thread_id')}`"
                )
                st.session_state.page = "report"
                st.rerun()
            else:
                st.error(f"Failed: {result.get('message')}")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Active Report Card ──
    if st.session_state.thread_id:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Active Report")
        st.markdown(f"**Topic:** {st.session_state.topic}")
        st.markdown(f"**Thread ID:** `{st.session_state.thread_id}`")
        if st.button("View Report Progress →"):
            st.session_state.page = "report"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
