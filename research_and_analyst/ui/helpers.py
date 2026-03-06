"""
Helper utilities for the Streamlit frontend.

Contains:
  - api_post / api_get — HTTP helpers for FastAPI backend
  - handle_google_callback — process Google OAuth redirect
"""

import os
import streamlit as st
import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api")


# ─────────────────────────────────────────────
# API Helpers
# ─────────────────────────────────────────────

def api_post(endpoint: str, data: dict) -> dict:
    """POST JSON to the FastAPI backend and return the parsed response."""
    try:
        resp = requests.post(f"{API_BASE}/{endpoint}", json=data, timeout=120)
        return resp.json()
    except requests.ConnectionError:
        return {
            "success": False,
            "message": "Cannot connect to API server. Make sure FastAPI is running on port 8000.",
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


def api_get(endpoint: str) -> dict:
    """GET from the FastAPI backend and return the parsed response."""
    try:
        resp = requests.get(f"{API_BASE}/{endpoint}", timeout=120)
        return resp.json()
    except requests.ConnectionError:
        return {"success": False, "message": "Cannot connect to API server."}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ─────────────────────────────────────────────
# Google OAuth Callback
# ─────────────────────────────────────────────

def handle_google_callback():
    """
    Auto-detect a ?code= query-param (returned by Google OAuth redirect)
    and exchange it for a user session.
    """
    params = st.query_params
    code = params.get("code")

    if code and not st.session_state.logged_in:
        with st.spinner("Signing in with Google..."):
            result = api_post("google_auth", {"code": code})

        # Clear the OAuth params from the URL
        st.query_params.clear()

        if result.get("success"):
            st.session_state.logged_in = True
            st.session_state.username = result.get("username", "User")
            st.session_state.page = "dashboard"
            st.rerun()
        else:
            st.error(
                f"Google sign-in failed: {result.get('message', 'Unknown error')}"
            )
