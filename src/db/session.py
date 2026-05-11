"""
Session management - kept for backward compatibility.

All database operations now go through src.db.supabase_client (supabase-py).
This file is kept as a stub so any remaining imports don't break.
"""
# SQLAlchemy session layer is no longer used.
# Use src.db.supabase_client.get_supabase_client() instead.
