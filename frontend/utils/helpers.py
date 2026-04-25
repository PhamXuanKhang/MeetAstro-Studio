from __future__ import annotations

from datetime import datetime


def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M")


def clamp(s: str, max_len: int = 120) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"
