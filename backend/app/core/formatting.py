"""Turning stored UTC instants into Spanish text a person can read in a chat message.

The web client formats dates in the browser, where the reader's locale is known. Telegram
messages are built server-side, so the formatting lives here instead. Hand-written month
and day names rather than `locale`: container images rarely ship the es_CL locale, and a
silent fallback to English would be worse than three lines of table.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings

DAYS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MONTHS = [
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
]


def to_display_timezone(moment: datetime) -> datetime:
    return moment.astimezone(ZoneInfo(get_settings().display_timezone))


def format_slot(moment: datetime) -> str:
    """ "vie 12 sep, 20:00" — short enough to fit a Telegram poll option (100 chars)."""
    local = to_display_timezone(moment)
    return f"{DAYS[local.weekday()]} {local.day} {MONTHS[local.month - 1]}, {local:%H:%M}"
