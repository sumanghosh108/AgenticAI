"""
Supabase client singleton.

Initialises once using SUPABASE_URL and SUPABASE_KEY from the environment.
Import `supabase` from this module wherever Supabase access is needed.
"""

import os
from pathlib import Path

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
