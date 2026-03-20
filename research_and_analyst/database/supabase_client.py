"""
Supabase client singleton.

Provides both sync and async access:
  - `supabase`          → sync client (for background threads / non-async code)
  - `supabase_async()`  → runs sync calls via asyncio.to_thread (non-blocking)

Import `supabase` from this module wherever Supabase access is needed.
"""

import asyncio
import os
from functools import partial
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(str(_env_path), override=True)

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY must be set in the environment / .env file."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


async def run_async(func, *args, **kwargs) -> Any:
    """Run a sync Supabase operation in a thread so it doesn't block the event loop."""
    if kwargs:
        return await asyncio.to_thread(partial(func, **kwargs), *args)
    return await asyncio.to_thread(func, *args)
