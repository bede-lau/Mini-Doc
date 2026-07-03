"""Timezone-aware timestamps for audit reports."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from packages.core.config import get_settings


def _tz():
    try:
        return ZoneInfo(get_settings().timezone)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def now_iso() -> str:
    """ISO-8601 timestamp in the configured (or UTC) timezone."""
    return datetime.now(_tz()).isoformat(timespec="seconds")


def today_iso() -> str:
    return datetime.now(_tz()).date().isoformat()
