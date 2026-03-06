"""
Streamlit Frontend — Autonomous Research Report Generator

Run with: streamlit run research_and_analyst/streamlit_app.py
"""

import streamlit as st
import requests
import time
import os

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api")

st.set_page_config(
    page_title="AgenticAI — Research Report Generator",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
    /* Global */
    .main { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); }
    .stApp { color: #e0e0e0; }

    /* Cards */
    .auth-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 2.5rem;
        backdrop-filter: blur(10px);
        max-width: 420px;
        margin: 4rem auto;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .dashboard-card {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 14px;
        padding: 1.8rem;
        margin-bottom: 1.2rem;
        backdrop-filter: blur(8px);
    }

    /* Title */
    .app-title {
        text-align: center;
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    .app-subtitle {
        text-align: center;
        color: #aaa;
        font-size: 1rem;
        margin-bottom: 2rem;
    }

    /* Buttons */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.7rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102,126,234,0.4) !important;
    }

    /* Status badge */
    .status-running {
        display: inline-block;
        background: #f39c12;
        color: #000;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .status-done {
        display: inline-block;
        background: #27ae60;
        color: #fff;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }

    /* Hide Streamlit defaults */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Session State Defaults
# ─────────────────────────────────────────────

for key, default in {
    "logged_in": False,
    "username": "",
    "page": "login",
    "thread_id": None,
    "topic": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────────────────────────────────────────
# Helper: API calls
# ─────────────────────────────────────────────

def api_post(endpoint: str, data: dict) -> dict:
    """POST to the FastAPI backend."""
    try:
        resp = requests.post(f"{API_BASE}/{endpoint}", json=data, timeout=120)
        return resp.json()
    except requests.ConnectionError:
        return {"success": False, "message": "Cannot connect to API server. Make sure FastAPI is running on port 8000."}
    except Exception as e:
        return {"success": False, "message": str(e)}


def api_get(endpoint: str) -> dict:
    """GET from the FastAPI backend."""
    try:
        resp = requests.get(f"{API_BASE}/{endpoint}", timeout=120)
        return resp.json()
    except requests.ConnectionError:
        return {"success": False, "message": "Cannot connect to API server."}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ─────────────────────────────────────────────
# Page: Login
# ─────────────────────────────────────────────

def page_login():
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<p class="app-title">🔬 AgenticAI</p>', unsafe_allow_html=True)
    st.markdown('<p class="app-subtitle">Autonomous Research Report Generator</p>', unsafe_allow_html=True)

    st.markdown("#### 🔐 Login")

    username = st.text_input("Username", key="login_user", placeholder="Enter your username")
    password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login", use_container_width=True):
            if not username or not password:
                st.error("Please fill in all fields")
            else:
                with st.spinner("Authenticating..."):
                    result = api_post("login", {"username": username, "password": password})
                if result.get("success"):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.page = "dashboard"
                    st.rerun()
                else:
                    st.error(result.get("message", "Login failed"))

    with col2:
        if st.button("Sign Up →", use_container_width=True):
            st.session_state.page = "signup"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Page: Signup
# ─────────────────────────────────────────────

def page_signup():
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<p class="app-title">🔬 AgenticAI</p>', unsafe_allow_html=True)
    st.markdown('<p class="app-subtitle">Create your account</p>', unsafe_allow_html=True)

    st.markdown("#### 📝 Sign Up")

    username = st.text_input("Username", key="signup_user", placeholder="Choose a username")
    email = st.text_input("Email", key="signup_email", placeholder="Enter your email")
    password = st.text_input("Password", type="password", key="signup_pass", placeholder="Choose a password")
    confirm = st.text_input("Confirm Password", type="password", key="signup_confirm", placeholder="Re-enter password")

    col_age, col_gender = st.columns(2)
    with col_age:
        age = st.number_input("Age", min_value=1, max_value=120, value=None, step=1, key="signup_age", placeholder="Your age")
    with col_gender:
        gender = st.selectbox("Gender", options=["", "Male", "Female", "Other", "Prefer not to say"], key="signup_gender")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Create Account", use_container_width=True):
            if not username or not email or not password:
                st.error("Please fill in all required fields (Username, Email, Password)")
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
                    st.success("✅ Account created! Please log in.")
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

    with col2:
        if st.button("← Back to Login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Page: Dashboard
# ─────────────────────────────────────────────

def page_dashboard():
    # Top bar
    col_title, col_user = st.columns([4, 1])
    with col_title:
        st.markdown('<p class="app-title" style="text-align:left; font-size:1.8rem;">🔬 AgenticAI Dashboard</p>', unsafe_allow_html=True)
    with col_user:
        st.markdown(f"**👤 {st.session_state.username}**")
        if st.button("Logout", key="logout_btn"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.page = "login"
            st.session_state.thread_id = None
            st.rerun()

    st.divider()

    # ── Generate Report Section ──
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### 📄 Generate Research Report")
    st.markdown("Enter a topic and our AI analysts will research and produce a comprehensive report.")

    topic = st.text_input(
        "Research Topic",
        placeholder="e.g., Impact of AI on Healthcare in 2026",
        key="topic_input",
    )
    max_analysts = st.slider("Number of Analyst Personas", min_value=1, max_value=5, value=3)

    if st.button("🚀 Generate Report", use_container_width=True):
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
                st.success(f"✅  Pipeline started! Thread ID: `{result.get('thread_id')}`")
                st.session_state.page = "report"
                st.rerun()
            else:
                st.error(f"Failed: {result.get('message')}")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Check Existing Report ──
    if st.session_state.thread_id:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Active Report")
        st.markdown(f"**Topic:** {st.session_state.topic}")
        st.markdown(f"**Thread ID:** `{st.session_state.thread_id}`")
        if st.button("View Report Progress →"):
            st.session_state.page = "report"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Page: Report Progress & View
# ─────────────────────────────────────────────

def page_report():
    col_title, col_back = st.columns([4, 1])
    with col_title:
        st.markdown('<p class="app-title" style="text-align:left; font-size:1.8rem;">📊 Report Progress</p>', unsafe_allow_html=True)
    with col_back:
        if st.button("← Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()

    st.divider()

    thread_id = st.session_state.thread_id
    if not thread_id:
        st.warning("No active report. Go to the dashboard to start one.")
        return

    st.markdown(f"**Topic:** {st.session_state.topic}  |  **Thread:** `{thread_id}`")

    # ── Feedback ──
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### 💬 Submit Feedback")
    st.markdown("Approve the analyst personas or provide feedback to regenerate them.")

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

    # ── Status ──
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("### 📋 Report Status")

    if st.button("🔄 Check Status", use_container_width=True):
        with st.spinner("Checking..."):
            result = api_get(f"report_status/{thread_id}")

        if result.get("success"):
            status = result.get("status", "unknown")

            if status == "completed":
                st.markdown('<span class="status-done">✅ Completed</span>', unsafe_allow_html=True)

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
                st.markdown('<span class="status-running">⏳ Running</span>', unsafe_allow_html=True)
                st.info("The report is still being generated. Check back in a moment.")
            else:
                st.warning(f"Status: {status}")
        else:
            st.error(f"Error: {result.get('message')}")

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────

def main():
    if not st.session_state.logged_in:
        if st.session_state.page == "signup":
            page_signup()
        else:
            page_login()
    else:
        if st.session_state.page == "report":
            page_report()
        else:
            page_dashboard()


if __name__ == "__main__":
    main()
