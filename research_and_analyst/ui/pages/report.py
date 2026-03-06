"""Report progress & download page for AgenticAI."""

import os
import streamlit as st

from research_and_analyst.ui.styles import inject_dashboard_css
from research_and_analyst.ui.helpers import api_post, api_get


def render():
    """Render the report progress / download page."""
    inject_dashboard_css()

    # ── Header row ──
    col_title, col_back = st.columns([4, 1])
    with col_title:
        st.markdown(
            '<p class="dash-title">📊 Report Progress</p>',
            unsafe_allow_html=True,
        )
    with col_back:
        if st.button("← Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()

    st.divider()

    thread_id = st.session_state.thread_id
    if not thread_id:
        st.warning("No active report. Go to the dashboard to start one.")
        return

    st.markdown(
        f"**Topic:** {st.session_state.topic}  |  **Thread:** `{thread_id}`"
    )

    # ── Feedback Card ──
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### 💬 Submit Feedback")
    st.markdown(
        "Approve the analyst personas or provide feedback to regenerate them."
    )

    feedback = st.text_area(
        "Feedback",
        placeholder='Type "approve" to proceed, or provide specific feedback...',
        key="feedback_input",
    )

    if st.button("Submit Feedback", use_container_width=True):
        if not feedback:
            st.error("Please enter feedback")
        else:
            with st.spinner("Processing feedback..."):
                result = api_post("submit_feedback", {
                    "thread_id": thread_id,
                    "feedback": feedback,
                })
            if result.get("success"):
                st.success("✅ Feedback processed!")
            else:
                st.error(f"Failed: {result.get('message')}")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Status Card ──
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### 📋 Report Status")

    if st.button("🔄 Check Status", use_container_width=True):
        with st.spinner("Checking..."):
            result = api_get(f"report_status/{thread_id}")

        if result.get("success"):
            status = result.get("status", "unknown")

            if status == "completed":
                st.markdown(
                    '<span class="status-done">✅ Completed</span>',
                    unsafe_allow_html=True,
                )
                st.divider()
                st.markdown("### 📥 Download Report")

                col1, col2, col3 = st.columns(3)
                for col, key, label, icon in [
                    (col1, "md_path", "Markdown", "📝"),
                    (col2, "docx_path", "Word", "📄"),
                    (col3, "pdf_path", "PDF", "📕"),
                ]:
                    path = result.get(key)
                    if path and os.path.exists(path):
                        with col:
                            with open(path, "rb") as f:
                                st.download_button(
                                    f"{icon} Download {label}",
                                    data=f.read(),
                                    file_name=os.path.basename(path),
                                    use_container_width=True,
                                )
                    elif path:
                        with col:
                            st.info(f"{label} file at: `{path}`")

            elif status == "running":
                st.markdown(
                    '<span class="status-running">⏳ Running</span>',
                    unsafe_allow_html=True,
                )
                st.info("The report is still being generated. Check back in a moment.")
            else:
                st.warning(f"Status: {status}")
        else:
            st.error(f"Error: {result.get('message')}")

    st.markdown('</div>', unsafe_allow_html=True)
