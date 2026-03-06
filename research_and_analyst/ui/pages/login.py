"""Login page for AgenticAI."""

import streamlit as st

from research_and_analyst.auth.google_oauth import (
    is_google_oauth_configured,
    get_google_auth_url,
)
from research_and_analyst.ui.styles import inject_auth_css
from research_and_analyst.ui.helpers import api_post


def render():
    """Render the login page."""
    inject_auth_css()

    # ── Top-left logo (navbar-style) ──
    st.markdown("""
    <div class="navbar-brand">
        <span class="navbar-icon">🔬</span>
        <span class="navbar-text">AgenticAI</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Hero section: fixed title + rotating keywords ──
    st.markdown("""
    <div class="hero-section">
        <h1 class="hero-title">Autonomous Research Report Generator</h1>
        <div class="hero-rotating">
            <span class="rotating-prefix">for </span>
            <span class="rotating-words">
                <span>Machine Learning</span>
                <span>Deep Learning</span>
                <span>MLOps</span>
                <span>Agentic AI</span>
                <span>RAG</span>
                <span>LLM</span>
                <span>AI Agent</span>
                <span>Others</span>
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Center the form using columns
    _, col_center, _ = st.columns([1.2, 2, 1.2])
    with col_center:
        st.markdown('<p class="auth-section-title">Login</p>', unsafe_allow_html=True)

        username = st.text_input(
            "Username", key="login_user",
            placeholder="Enter your username",
        )
        password = st.text_input(
            "Password", type="password", key="login_pass",
            placeholder="Enter your password",
        )

        st.markdown("")  # spacer

        if st.button("Continue", use_container_width=True, key="login_btn"):
            if not username or not password:
                st.error("Please fill in all fields")
            else:
                with st.spinner("Authenticating..."):
                    result = api_post("login", {
                        "username": username,
                        "password": password,
                    })
                if result.get("success"):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.page = "dashboard"
                    st.rerun()
                else:
                    st.error(result.get("message", "Login failed"))

        st.markdown(
            '<div class="or-divider"><span>OR</span></div>',
            unsafe_allow_html=True,
        )

        # Google Sign-In
        if is_google_oauth_configured():
            google_url = get_google_auth_url()
            st.markdown(
                f'<a href="{google_url}" class="google-btn">'
                '<img src="https://www.gstatic.com/firebasejs/ui/2.0.0/'
                'images/auth/google.svg" alt="G">'
                'Continue with Google</a>',
                unsafe_allow_html=True,
            )
        else:
            st.info(
                "ℹ️ Google Sign-In available once GOOGLE_CLIENT_ID "
                "and GOOGLE_CLIENT_SECRET are set in .env"
            )

        # Sign Up link
        st.markdown(
            '<p class="auth-footer">Don\'t have an account?</p>',
            unsafe_allow_html=True,
        )
        if st.button("Sign Up", use_container_width=True, key="goto_signup"):
            st.session_state.page = "signup"
            st.rerun()
