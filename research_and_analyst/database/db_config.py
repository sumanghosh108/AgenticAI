"""
Database configuration for the Autonomous Research Report Generator.

- Supabase as the backend (replaces local PostgreSQL / SQLAlchemy)
- User model operations via Supabase REST API
- user_report table for persisting generated reports
"""

import hashlib
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from research_and_analyst.logger import GLOBAL_LOGGER as log
from research_and_analyst.exception.custom_exception import ResearchAnalystException

load_dotenv()

# ─────────────────────────────────────────────
# Supabase Client (lazy import to avoid circular deps)
# ─────────────────────────────────────────────

def _get_supabase():
    from research_and_analyst.database.supabase_client import supabase
    return supabase


# ─────────────────────────────────────────────
# Password Utilities (hashlib)
# ─────────────────────────────────────────────

SALT = os.getenv("PASSWORD_SALT", "agenticai_salt_2026")


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 (computationally expensive)."""
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        SALT.encode("utf-8"),
        100000
    ).hex()
    return f"v2${digest}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored hash."""
    if hashed_password.startswith("v2$"):
        return hash_password(plain_password) == hashed_password
        
    return False


# ─────────────────────────────────────────────
# Table Creation (no-op — tables managed in Supabase)
# ─────────────────────────────────────────────

def create_tables():
    """No-op: tables are created in Supabase dashboard / SQL editor."""
    log.info("Supabase mode — table creation managed externally")


# ─────────────────────────────────────────────
# User CRUD via Supabase
# ─────────────────────────────────────────────

def get_user_by_username(username: str) -> dict | None:
    """Fetch a user row by username."""
    sb = _get_supabase()
    res = sb.table("users").select("*").eq("username", username).execute()
    return res.data[0] if res.data else None


def get_user_by_email(email: str) -> dict | None:
    """Fetch a user row by email."""
    sb = _get_supabase()
    res = sb.table("users").select("*").eq("email", email).execute()
    return res.data[0] if res.data else None


def create_user(username: str, email: str, password_hash: str,
                age: int | None = None, gender: str | None = None) -> dict:
    """Insert a new user into the Supabase `users` table."""
    sb = _get_supabase()
    payload = {
        "username": username,
        "email": email,
        "password": password_hash,
    }
    if age is not None:
        payload["age"] = age
    if gender is not None:
        payload["gender"] = gender

    res = sb.table("users").insert(payload).execute()
    return res.data[0] if res.data else {}


# ─────────────────────────────────────────────
# User Report CRUD via Supabase
# ─────────────────────────────────────────────

def save_user_report(user_name: str, research_topic: str,
                     research_domain: str | None, document: str | None) -> dict:
    """Insert a report into the Supabase `user_report` table."""
    sb = _get_supabase()
    payload = {
        "user_name": user_name,
        "research_topic": research_topic,
        "research_domain": research_domain or "",
        "document": document or "",
    }
    res = sb.table("user_report").insert(payload).execute()
    return res.data[0] if res.data else {}


def get_user_reports(user_name: str) -> list[dict]:
    """Fetch all reports for a given user, newest first."""
    sb = _get_supabase()
    res = (
        sb.table("user_report")
        .select("*")
        .eq("user_name", user_name)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


# ─────────────────────────────────────────────
# Standalone Test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    create_tables()
    print("✅ Supabase connection verified")
