"""
FastAPI dependency injection helpers.

get_supabase: Supabase client for each request (read/write via SERVICE_ROLE_KEY).
"""
from supabase import Client

from src.db.supabase_client import get_supabase_client


def get_supabase() -> Client:
    """Return Supabase client (singleton per process, SERVICE_ROLE_KEY)."""
    return get_supabase_client()
