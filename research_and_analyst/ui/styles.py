"""
CSS Styles for the Streamlit application.

Two themes:
  - inject_auth_css()       → Light, clean auth pages with Unsplash background
  - inject_dashboard_css()  → Light glassmorphism dashboard with same background
"""

import streamlit as st

# ─────────────────────────────────────────────
# Shared: Unsplash background image URL
# ─────────────────────────────────────────────

_BG_IMAGE = (
    "https://images.unsplash.com/photo-1497215728101-856f4ea42174"
    "?w=1920&q=80"
)


def inject_auth_css():
    """Clean, minimal white-card auth aesthetic with Unsplash backdrop."""
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* ── Page background with Unsplash image ── */
        .stApp {{
            background: url('{_BG_IMAGE}') center/cover fixed no-repeat !important;
        }}
        .stApp::before {{
            content: '';
            position: fixed;
            inset: 0;
            background: rgba(15, 12, 41, 0.75);
            z-index: 0;
        }}
        .main {{ background: transparent !important; }}
        [data-testid="stAppViewContainer"] {{ position: relative; z-index: 1; }}

        /* ── Navbar brand (top-left) ── */
        .navbar-brand {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0.8rem 0 0.2rem;
            font-family: 'Inter', sans-serif;
        }}
        .navbar-icon {{
            font-size: 1.6rem;
        }}
        .navbar-text {{
            font-size: 1.25rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.02em;
        }}

        /* ── Hero section ── */
        .hero-section {{
            text-align: center;
            padding: 1.5rem 1rem 1rem;
            font-family: 'Inter', sans-serif;
        }}
        .hero-title {{
            font-size: 1.75rem;
            font-weight: 700;
            color: #ffffff !important;
            margin: 0 0 0.5rem;
            letter-spacing: -0.01em;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
        }}
        .hero-rotating {{
            font-size: 1.15rem;
            color: #818cf8;
            font-weight: 500;
            height: 1.6em;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
        }}
        .rotating-prefix {{
            color: #d1d5db;
        }}
        .rotating-words {{
            display: inline-block;
            position: relative;
            height: 1.6em;
            width: 220px;
            text-align: left;
            overflow: hidden;
        }}
        .rotating-words span {{
            display: block;
            height: 1.6em;
            line-height: 1.6em;
            animation: rotateWords 22.5s infinite;
            opacity: 0;
            position: absolute;
            width: max-content;
        }}
        /* Stagger each keyword (9 total, 2.5s each in a 22.5s cycle) */
        .rotating-words span:nth-child(1) {{ animation-delay: 0s; }}
        .rotating-words span:nth-child(2) {{ animation-delay: 2.5s; }}
        .rotating-words span:nth-child(3) {{ animation-delay: 5s; }}
        .rotating-words span:nth-child(4) {{ animation-delay: 7.5s; }}
        .rotating-words span:nth-child(5) {{ animation-delay: 10s; }}
        .rotating-words span:nth-child(6) {{ animation-delay: 12.5s; }}
        .rotating-words span:nth-child(7) {{ animation-delay: 15s; }}
        .rotating-words span:nth-child(8) {{ animation-delay: 17.5s; }}
        .rotating-words span:nth-child(9) {{ animation-delay: 20s; }}

        @keyframes rotateWords {{
            0%   {{ opacity: 0; transform: translateY(50%); }}
            2%   {{ opacity: 1; transform: translateY(0); }}
            12%  {{ opacity: 1; transform: translateY(0); }}
            14%  {{ opacity: 0; transform: translateY(-50%); }}
            100% {{ opacity: 0; }}
        }}

        /* ── Section title ── */
        .auth-section-title {{
            font-family: 'Inter', sans-serif;
            font-size: 1.2rem;
            font-weight: 600;
            color: #ffffff;
            margin-bottom: 1rem;
            text-align: center;
        }}

        /* ── Divider with OR ── */
        .or-divider {{
            display: flex;
            align-items: center;
            margin: 1.4rem 0;
            color: #d1d5db;
            font-family: 'Inter', sans-serif;
            font-size: 0.8rem;
        }}
        .or-divider::before, .or-divider::after {{
            content: '';
            flex: 1;
            height: 1px;
            background: rgba(255,255,255,0.2);
        }}
        .or-divider span {{
            padding: 0 1rem;
        }}

        /* ── Google button (outlined) ── */
        .google-btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            padding: 0.7rem 1rem;
            background: #ffffff;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            font-family: 'Inter', sans-serif;
            font-weight: 500;
            font-size: 0.95rem;
            color: #1f2937;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.2s ease;
            min-height: 44px;
            box-sizing: border-box;
        }}
        .google-btn:hover {{
            background: #f9fafb;
            border-color: #9ca3af;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }}
        .google-btn img {{
            width: 18px; height: 18px;
        }}

        /* ── Inputs ── */
        .stTextInput > label, .stNumberInput > label, .stSelectbox > label {{
            font-family: 'Inter', sans-serif !important;
            font-weight: 500 !important;
            font-size: 0.88rem !important;
            color: #e5e7eb !important;
        }}
        .stTextInput input, .stNumberInput input {{
            background: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 8px !important;
            padding: 0.65rem 0.9rem !important;
            font-size: 0.95rem !important;
            color: #1f2937 !important;
            min-height: 44px !important;
            transition: border-color 0.2s ease !important;
        }}
        .stTextInput input:focus, .stNumberInput input:focus {{
            border-color: #6366f1 !important;
            box-shadow: 0 0 0 3px rgba(99,102,241,0.1) !important;
        }}
        .stTextInput input::placeholder {{
            color: #9ca3af !important;
        }}
        .stSelectbox > div > div {{
            min-height: 44px !important;
            border-radius: 8px !important;
            border: 1px solid #d1d5db !important;
        }}

        /* ── Primary button (dark) ── */
        .stButton > button {{
            width: 100%;
            background: #1a1a2e !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.7rem 1.5rem !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            min-height: 44px !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
        }}
        .stButton > button:hover {{
            background: #16213e !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(26,26,46,0.25) !important;
        }}

        /* ── Footer link ── */
        .auth-footer {{
            text-align: center;
            margin-top: 1.2rem;
            font-family: 'Inter', sans-serif;
            font-size: 0.88rem;
            color: #d1d5db;
        }}

        /* ── Hide Streamlit defaults ── */
        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}
        header {{ visibility: hidden; }}

        /* ── Responsive ── */
        @media (max-width: 640px) {{
            [data-testid="stHorizontalBlock"] {{
                flex-direction: column !important;
            }}
            [data-testid="stHorizontalBlock"] > div {{
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }}
        }}
        @media (max-width: 768px) {{
            .auth-card {{
                padding: 2rem 1.6rem 1.5rem;
                margin: 1.5rem auto 0;
                border-radius: 12px;
            }}
            .auth-logo-text {{ font-size: 1.3rem; }}
        }}
        @media (max-width: 480px) {{
            .auth-card {{
                width: 96%;
                padding: 1.5rem 1.2rem 1.2rem;
                margin: 1rem auto 0;
            }}
            .auth-logo-icon {{ font-size: 2.2rem; }}
            .auth-logo-text {{ font-size: 1.15rem; }}
            .auth-subtitle {{ font-size: 0.82rem; }}
        }}
    </style>
    """, unsafe_allow_html=True)


def inject_dashboard_css():
    """Light dashboard with Unsplash background and glassmorphism cards."""
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* ── Global — Unsplash background ── */
        .stApp {{
            background: url('{_BG_IMAGE}') center/cover fixed no-repeat !important;
            color: #1f2937;
        }}
        .stApp::before {{
            content: '';
            position: fixed;
            inset: 0;
            background: rgba(255,255,255,0.82);
            z-index: 0;
        }}
        .main {{ background: transparent !important; }}
        [data-testid="stAppViewContainer"] {{ position: relative; z-index: 1; }}

        /* ── Dashboard Card (glassmorphism) ── */
        .dashboard-card {{
            font-family: 'Inter', sans-serif;
            background: rgba(255,255,255,0.88);
            border: 1px solid rgba(0,0,0,0.08);
            border-radius: 14px;
            padding: 1.8rem;
            margin-bottom: 1.2rem;
            backdrop-filter: blur(14px);
            box-shadow: 0 2px 16px rgba(0,0,0,0.06);
        }}

        /* ── Title ── */
        .dash-title {{
            font-family: 'Inter', sans-serif;
            text-align: left;
            font-size: 1.8rem;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 0.3rem;
            word-break: break-word;
        }}

        /* ── Labels ── */
        .stTextInput > label, .stTextArea > label, .stSlider > label,
        .stNumberInput > label, .stSelectbox > label {{
            font-family: 'Inter', sans-serif !important;
            font-weight: 500 !important;
            color: #374151 !important;
        }}

        /* ── Buttons ── */
        .stButton > button {{
            width: 100%;
            background: linear-gradient(135deg, #667eea, #764ba2) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 0.7rem 1.5rem !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            min-height: 44px !important;
            transition: all 0.3s ease !important;
        }}
        .stButton > button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(102,126,234,0.4) !important;
        }}

        /* ── Inputs ── */
        .stTextInput input, .stTextArea textarea, .stNumberInput input {{
            min-height: 44px !important;
            font-size: 1rem !important;
            background: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 8px !important;
            color: #1f2937 !important;
        }}
        .stSelectbox > div > div {{ min-height: 44px !important; }}

        /* ── Status Badges ── */
        .status-running {{
            display: inline-block;
            background: #f39c12; color: #000;
            padding: 4px 14px; border-radius: 20px;
            font-weight: 600; font-size: 0.85rem;
        }}
        .status-done {{
            display: inline-block;
            background: #27ae60; color: #fff;
            padding: 4px 14px; border-radius: 20px;
            font-weight: 600; font-size: 0.85rem;
        }}

        /* ── Hide defaults ── */
        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}

        /* ── Responsive ── */
        @media (max-width: 640px) {{
            [data-testid="stHorizontalBlock"] {{
                flex-direction: column !important;
            }}
            [data-testid="stHorizontalBlock"] > div {{
                width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important;
            }}
        }}
        @media (max-width: 1024px) {{
            .dashboard-card {{ padding: 1.4rem; }}
            .dash-title {{ font-size: 1.5rem; }}
            .block-container {{ padding: 1rem 1.5rem !important; }}
        }}
        @media (max-width: 768px) {{
            .dashboard-card {{ padding: 1.2rem; border-radius: 10px; }}
            .dash-title {{ font-size: 1.3rem; }}
            .block-container {{ padding: 0.5rem 1rem !important; }}
            .stDownloadButton > button {{
                font-size: 0.85rem !important; padding: 0.5rem 0.8rem !important;
            }}
        }}
        @media (max-width: 480px) {{
            .block-container {{ padding: 0.3rem 0.5rem !important; }}
            .stButton > button {{ padding: 0.6rem 1rem !important; font-size: 0.85rem !important; }}
        }}
    </style>
    """, unsafe_allow_html=True)
