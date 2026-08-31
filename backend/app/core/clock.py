from datetime import UTC, datetime


def now() -> datetime:
    """Single source of "now", so tests can patch one place."""
    return datetime.now(UTC)


def ensure_utc(moment: datetime) -> datetime:
    """Naive input is read as UTC; everything stored is timezone-aware."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)
