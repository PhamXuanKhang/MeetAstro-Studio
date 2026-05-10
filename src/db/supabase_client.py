"""
Supabase client singleton for backend access using SERVICE_ROLE_KEY.

Used for all database operations: meetings, transcripts, analysis_results, review_items,
provider_configs. Frontend uses Supabase JS SDK (ANON_KEY) for auth/user operations.
Backend uses this client (SERVICE_ROLE_KEY) for all read/write operations.
"""
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from src.config import get_logger, get_settings

logger = get_logger(__name__)

_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Return cached Supabase client singleton.

    Raises RuntimeError if SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY are not configured.
    """
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.supabase_url:
            raise RuntimeError(
                "SUPABASE_URL chua duoc cau hinh. "
                "Kiem tra bien moi truong SUPABASE_URL."
            )
        if not settings.supabase_service_role_key:
            raise RuntimeError(
                "SUPABASE_SERVICE_ROLE_KEY chua duoc cau hinh. "
                "Kiem tra bien moi truong SUPABASE_SERVICE_ROLE_KEY."
            )
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        logger.info("Supabase client initialized (SERVICE_ROLE_KEY).")
    return _client


def clear_supabase_client() -> None:
    """Clear the cached client. Useful for testing."""
    global _client
    _client = None


# ── Table name constants ──────────────────────────────────────────

TABLE_MEETINGS = "meetings"
TABLE_TRANSCRIPTS = "transcripts"
TABLE_ANALYSIS_RESULTS = "analysis_results"
TABLE_REVIEW_ITEMS = "review_items"
TABLE_PROVIDER_CONFIGS = "provider_configs"


# ── Convenience helpers ──────────────────────────────────────────

def insert(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a row and return the inserted record."""
    client = get_supabase_client()
    result = client.table(table).insert(data).execute()
    if result.data:
        return result.data[0]
    raise RuntimeError(f"Insert into {table} returned no data: {result}")


def upsert(
    table: str,
    data: Dict[str, Any],
    on_conflict: Optional[str] = None,
) -> Dict[str, Any]:
    """Upsert a row and return the record."""
    client = get_supabase_client()
    kwargs: Dict[str, Any] = {"data": data}
    if on_conflict:
        kwargs["on_conflict"] = on_conflict
    result = client.table(table).upsert(**kwargs).execute()
    if result.data:
        return result.data[0]
    raise RuntimeError(f"Upsert into {table} returned no data: {result}")


def update_by_id(table: str, row_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a row by ID and return the updated record."""
    client = get_supabase_client()
    result = client.table(table).update(data).eq("id", row_id).execute()
    if result.data:
        return result.data[0]
    raise RuntimeError(f"Update {table}/{row_id} returned no data: {result}")


def delete_by_id(table: str, row_id: str) -> bool:
    """Delete a row by ID. Returns True if deleted."""
    client = get_supabase_client()
    result = client.table(table).delete().eq("id", row_id).execute()
    return bool(result.data)


def fetch_one(table: str, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fetch a single row matching filters, or None."""
    client = get_supabase_client()
    query = client.table(table).select("*")
    for col, val in filters.items():
        query = query.eq(col, val)
    result = query.maybe_single().execute()
    return result.data if result.data else None


def fetch_all(
    table: str,
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    ascending: bool = True,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Fetch all rows matching filters."""
    client = get_supabase_client()
    query = client.table(table).select("*")
    if filters:
        for col, val in filters.items():
            query = query.eq(col, val)
    if order_by:
        query = query.order(order_by, ascending=ascending)
    if limit:
        query = query.limit(limit)
    return client.table(table).select("*").execute().data
