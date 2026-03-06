"""Signup page for AgenticAI."""

import time
import streamlit as st

from research_and_analyst.ui.styles import inject_auth_css
from research_and_analyst.ui.helpers import api_post


def render():
    """Render the signup page."""
    inject_auth_css()

    # ── Top-left logo (navbar-style) ──
    st.markdown("""
    <div class="navbar-brand">
        <span class="navbar-icon">🔬</span>
        <span class="navbar-text">AgenticAI</span>
    </div>
    """, unsafe_allow_html=True)

    _, col_center, _ = st.columns([1.2, 2, 1.2])
    with col_center:
        st.markdown(
            '<p class="auth-section-title">Sign Up</p>',
            unsafe_allow_html=True,
        )

        username = st.text_input("Username", key="signup_user", placeholder="Choose a username")
        email = st.text_input("Email", key="signup_email", placeholder="Your email address")
        password = st.text_input("Password", type="password", key="signup_pass", placeholder="Choose a password")
        confirm = st.text_input("Confirm Password", type="password", key="signup_confirm", placeholder="Re-enter password")

        st.markdown(
            '<div class="or-divider"><span>OPTIONAL</span></div>',
            unsafe_allow_html=True,
        )

        col_age, col_gender = st.columns(2)
        with col_age:
            age = st.number_input(
                "Age", min_value=1, max_value=120,
                value=None, step=1, key="signup_age", placeholder="Age",
            )
        with col_gender:
            gender = st.selectbox(
                "Gender",
                options=["", "Male", "Female", "Other", "Prefer not to say"],
                key="signup_gender",
            )

        st.markdown("")  # spacer

        if st.button("Create Account", use_container_width=True, key="signup_btn"):
            if not username or not email or not password:
                st.error("Please fill in Username, Email and Password")
            elif password != confirm:
                st.error("Passwords do not match")
            elif len(username) < 3:
                st.error("Username must be at least 3 characters")
            elif len(password) < 4:
                st.error("Password must be at least 4 characters")
            elif "@" not in email or "." not in email:
                st.error("Please enter a valid email address")
            else:
                with st.spinner("Creating account..."):
                    result = api_post("signup", {
                        "username": username,
                        "email": email,
                        "password": password,
                        "age": age,
                        "gender": gender if gender else None,
                    })
                if result.get("success"):
                    st.success("✅ Account created! Redirecting to login...")
                    time.sleep(1.5)
                    st.session_state.page = "login"
                    st.rerun()
                elif result.get("email_exists"):
                    st.warning("⚠️ This email is already registered. Redirecting to login...")
                    time.sleep(2)
                    st.session_state.page = "login"
                    st.rerun()
                elif result.get("username_taken"):
                    st.error("❌ Username is already taken. Please choose a different username.")
                else:
                    st.error(result.get("message", "Signup failed"))

        st.markdown(
            '<p class="auth-footer">Already have an account?</p>',
            unsafe_allow_html=True,
        )
        if st.button("← Back to Login", use_container_width=True, key="back_login"):
            st.session_state.page = "login"
            st.rerun()
