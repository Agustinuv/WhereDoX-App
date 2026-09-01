"""The wire format of an inline button, encoded and decoded by pure functions.

Every conversational step travels inside the button the reader taps, so the bot keeps no
session state: nothing to lose across a restart, nothing to corrupt, no table to migrate.
Telegram caps callback_data at 64 bytes, which is why the format is positional rather than
JSON.

It lives in core/ rather than in bot/ because both ends need it: app/ builds the buttons it
sends, bot/ reads the taps that come back. The plan sketched it as bot/callback_data.py,
which would have made app/ depend on the adapter it is meant to be independent of.

Decoding is strict on purpose. A malformed payload raises instead of returning something
half-valid: a bad parse here does not crash anything visible, it silently does nothing, and
that is the hardest kind of bug to notice in a live demo.
"""

from typing import Literal

from pydantic import BaseModel

from app.core.constants import MAX_RATING, MIN_RATING

CallbackKind = Literal["clear", "suggest", "later", "rate"]
KINDS: tuple[str, ...] = ("clear", "suggest", "later", "rate")

SEPARATOR = ":"
FIELD_COUNT = 4
MAX_BYTES = 64


class Callback(BaseModel):
    """What a tap meant. game_id and score are only ever set for 'rate'."""

    kind: CallbackKind
    event_id: int
    game_id: int | None = None
    score: int | None = None


def encode(callback: Callback) -> str:
    parts = [
        callback.kind,
        str(callback.event_id),
        "" if callback.game_id is None else str(callback.game_id),
        "" if callback.score is None else str(callback.score),
    ]
    encoded = SEPARATOR.join(parts)
    if len(encoded.encode()) > MAX_BYTES:
        raise ValueError(f"callback_data exceeds Telegram's {MAX_BYTES}-byte limit: {encoded!r}")
    return encoded


def decode(raw: str) -> Callback:
    parts = raw.split(SEPARATOR)
    if len(parts) != FIELD_COUNT:
        raise ValueError(f"callback_data must have {FIELD_COUNT} fields, got {len(parts)}: {raw!r}")

    kind, event_field, game_field, score_field = parts
    if kind not in KINDS:
        raise ValueError(f"Unknown callback kind {kind!r}.")

    event_id = _positive_int(event_field, "event_id")
    if kind != "rate":
        if game_field or score_field:
            raise ValueError(f"Callback kind {kind!r} carries no game or score: {raw!r}")
        return Callback(kind=kind, event_id=event_id)

    score = _positive_int(score_field, "score")
    if not MIN_RATING <= score <= MAX_RATING:
        raise ValueError(f"Score must be between {MIN_RATING} and {MAX_RATING}, got {score}.")
    return Callback(
        kind=kind,
        event_id=event_id,
        game_id=_positive_int(game_field, "game_id"),
        score=score,
    )


def _positive_int(field: str, name: str) -> int:
    if not field.isdigit():
        raise ValueError(f"{name} must be a positive integer, got {field!r}.")
    value = int(field)
    if value < 1:
        raise ValueError(f"{name} must be a positive integer, got {value}.")
    return value
