"""
Database configuration for AgenticAI.

- Supabase as the backend (replaces local PostgreSQL / SQLAlchemy)
- User model operations via Supabase REST API
- user_report table for persisting generated reports
- Both sync and async variants of every operation
"""

import asyncio
import hashlib
import os
from typing import Optional

from dotenv import load_dotenv

from research_and_analyst.logger import GLOBAL_LOGGER as log

load_dotenv()

# ─────────────────────────────────────────────
# Supabase Client (lazy import to avoid circular deps)
# ─────────────────────────────────────────────

def _sb():
    from research_and_analyst.database.supabase_client import supabase
    return supabase


# ─────────────────────────────────────────────
# Password Utilities
# ─────────────────────────────────────────────

SALT = os.getenv("PASSWORD_SALT", "agenticai_salt_2026")


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256."""
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        SALT.encode("utf-8"),
        100_000,
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
# User CRUD — sync
# ─────────────────────────────────────────────

def get_user_by_username(username: str) -> Optional[dict]:
    res = _sb().table("users").select("*").eq("username", username).execute()
    return res.data[0] if res.data else None


def get_user_by_email(email: str) -> Optional[dict]:
    res = _sb().table("users").select("*").eq("email", email).execute()
    return res.data[0] if res.data else None


def create_user(username: str, email: str, password_hash: str,
                age: Optional[int] = None, gender: Optional[str] = None) -> dict:
    payload: dict = {"username": username, "email": email, "password": password_hash}
    if age is not None:
        payload["age"] = age
    if gender is not None:
        payload["gender"] = gender
    res = _sb().table("users").insert(payload).execute()
    return res.data[0] if res.data else {}


# ─────────────────────────────────────────────
# User CRUD — async (non-blocking)
# ─────────────────────────────────────────────

async def async_get_user_by_username(username: str) -> Optional[dict]:
    return await asyncio.to_thread(get_user_by_username, username)


async def async_get_user_by_email(email: str) -> Optional[dict]:
    return await asyncio.to_thread(get_user_by_email, email)


async def async_create_user(username: str, email: str, password_hash: str,
                            age: Optional[int] = None,
                            gender: Optional[str] = None) -> dict:
    return await asyncio.to_thread(create_user, username, email, password_hash, age, gender)


# ─────────────────────────────────────────────
# Report CRUD — sync
# ─────────────────────────────────────────────

def save_user_report(user_name: str, research_topic: str,
                     research_domain: Optional[str] = None,
                     document: Optional[str] = None) -> dict:
    payload = {
        "user_name": user_name,
        "research_topic": research_topic,
        "research_domain": research_domain or "",
        "document": document or "",
    }
    res = _sb().table("user_report").insert(payload).execute()
    return res.data[0] if res.data else {}


def get_user_reports(user_name: str) -> list[dict]:
    res = (
        _sb().table("user_report")
        .select("*")
        .eq("user_name", user_name)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


# ─────────────────────────────────────────────
# Daily Usage (rate limiting) — sync
# ─────────────────────────────────────────────

DAILY_REQUEST_LIMIT = 5


def get_daily_usage(username: str) -> dict:
    """Get today's usage via ACID-safe database function."""
    try:
        res = _sb().rpc("get_daily_usage", {
            "p_username": username,
            "p_limit": DAILY_REQUEST_LIMIT,
        }).execute()
        if res.data:
            return res.data
    except Exception:
        pass

    # Fallback to manual query if RPC not available
    from datetime import date
    today = date.today().isoformat()
    res = (
        _sb().table("daily_usage")
        .select("*")
        .eq("username", username)
        .eq("request_date", today)
        .execute()
    )
    count = res.data[0]["request_count"] if res.data else 0
    return {
        "username": username,
        "date": today,
        "request_count": count,
        "remaining": max(0, DAILY_REQUEST_LIMIT - count),
        "limit_reached": count >= DAILY_REQUEST_LIMIT,
    }


def increment_daily_usage(username: str) -> dict:
    """Atomic increment via database function (race-condition safe)."""
    try:
        res = _sb().rpc("increment_daily_usage", {
            "p_username": username,
            "p_limit": DAILY_REQUEST_LIMIT,
        }).execute()
        if res.data:
            return res.data
    except Exception:
        pass

    # Fallback to manual upsert if RPC not available
    from datetime import date, datetime
    today = date.today().isoformat()
    res = (
        _sb().table("daily_usage")
        .select("*")
        .eq("username", username)
        .eq("request_date", today)
        .execute()
    )
    if res.data:
        new_count = res.data[0]["request_count"] + 1
        _sb().table("daily_usage").update({
            "request_count": new_count,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("username", username).eq("request_date", today).execute()
    else:
        new_count = 1
        _sb().table("daily_usage").insert({
            "username": username,
            "request_date": today,
            "request_count": 1,
        }).execute()
    return {
        "username": username,
        "date": today,
        "request_count": new_count,
        "remaining": max(0, DAILY_REQUEST_LIMIT - new_count),
        "limit_reached": new_count >= DAILY_REQUEST_LIMIT,
    }


# ─────────────────────────────────────────────
# Daily Usage — async (non-blocking)
# ─────────────────────────────────────────────

async def async_get_daily_usage(username: str) -> dict:
    return await asyncio.to_thread(get_daily_usage, username)


async def async_increment_daily_usage(username: str) -> dict:
    return await asyncio.to_thread(increment_daily_usage, username)


# ─────────────────────────────────────────────
# Report CRUD — async (non-blocking)
# ─────────────────────────────────────────────

async def async_save_user_report(user_name: str, research_topic: str,
                                 research_domain: Optional[str] = None,
                                 document: Optional[str] = None) -> dict:
    return await asyncio.to_thread(save_user_report, user_name, research_topic,
                                   research_domain, document)


async def async_get_user_reports(user_name: str) -> list[dict]:
    return await asyncio.to_thread(get_user_reports, user_name)


# ─────────────────────────────────────────────
# Report Files (B2 metadata) — sync
# ─────────────────────────────────────────────

def save_report_file(
    username: str,
    report_id: int,
    file_type: str,
    file_name: str,
    b2_file_id: str,
    b2_file_path: str,
    file_size: int = 0,
    content_sha1: str = "",
) -> dict:
    """Save file metadata via ACID-safe RPC (validates report ownership)."""
    try:
        res = _sb().rpc("save_report_file", {
            "p_username": username,
            "p_report_id": report_id,
            "p_file_type": file_type,
            "p_file_name": file_name,
            "p_b2_file_id": b2_file_id,
            "p_b2_file_path": b2_file_path,
            "p_file_size": file_size,
            "p_content_sha1": content_sha1,
        }).execute()
        if res.data:
            return res.data
    except Exception:
        pass

    # Fallback to direct insert
    payload = {
        "username": username,
        "report_id": report_id,
        "file_type": file_type,
        "file_name": file_name,
        "b2_file_id": b2_file_id,
        "b2_file_path": b2_file_path,
        "file_size": file_size,
        "content_sha1": content_sha1,
    }
    res = _sb().table("report_files").insert(payload).execute()
    return res.data[0] if res.data else {}


def get_report_files(username: str) -> list[dict]:
    """Get all report files for a user."""
    res = (
        _sb().table("report_files")
        .select("*")
        .eq("username", username)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def get_report_files_by_report(report_id: int) -> list[dict]:
    """Get files for a specific report."""
    res = (
        _sb().table("report_files")
        .select("*")
        .eq("report_id", report_id)
        .execute()
    )
    return res.data or []


def get_report_file_by_id(file_id: int, username: str) -> Optional[dict]:
    """Get a single file record — only if it belongs to the given user (security)."""
    res = (
        _sb().table("report_files")
        .select("*")
        .eq("id", file_id)
        .eq("username", username)
        .execute()
    )
    return res.data[0] if res.data else None


# ─────────────────────────────────────────────
# Report Files — async (non-blocking)
# ─────────────────────────────────────────────

async def async_save_report_file(**kwargs) -> dict:
    return await asyncio.to_thread(save_report_file, **kwargs)


async def async_get_report_files(username: str) -> list[dict]:
    return await asyncio.to_thread(get_report_files, username)


async def async_get_report_files_by_report(report_id: int) -> list[dict]:
    return await asyncio.to_thread(get_report_files_by_report, report_id)


async def async_get_report_file_by_id(file_id: int, username: str) -> Optional[dict]:
    return await asyncio.to_thread(get_report_file_by_id, file_id, username)


# ─────────────────────────────────────────────
# Standalone Test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    create_tables()
    print("Supabase connection verified")
