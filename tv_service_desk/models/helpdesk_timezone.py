"""Shared timezone helpers for Helpdesk."""

DEPRECATED_TIMEZONE_MAP = {
    "Asia/Calcutta": "Asia/Kolkata",
}


def normalize_timezone(tz):
    return DEPRECATED_TIMEZONE_MAP.get(tz, tz) if tz else tz
