"""The button wire format, tested without a database or a bot.

This is where a silent bug is most likely: a callback that fails to parse does not raise
anything visible in Telegram, the tap simply does nothing. Hence a strict decoder and a
test for every way it can be handed garbage.
"""

import pytest

from app.core.callbacks import Callback, decode, encode


def test_round_trip_without_a_game():
    original = Callback(kind="suggest", event_id=42)
    assert decode(encode(original)) == original


def test_round_trip_with_a_game_and_a_score():
    original = Callback(kind="rate", event_id=42, game_id=7, score=4)
    assert decode(encode(original)) == original


def test_encoding_is_positional_and_compact():
    assert encode(Callback(kind="clear", event_id=3)) == "clear:3::"
    assert encode(Callback(kind="rate", event_id=3, game_id=9, score=5)) == "rate:3:9:5"


def test_a_payload_never_exceeds_the_telegram_limit():
    # Ids far beyond anything this system will reach still fit in 64 bytes.
    encoded = encode(Callback(kind="rate", event_id=10**12, game_id=10**12, score=5))
    assert len(encoded.encode()) <= 64


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "clear",
        "clear:3",
        "clear:3::extra",
        "unknown:3::",
        "clear:abc::",
        "clear:0::",
        "clear:-1::",
        "rate:3:9:",
        "rate:3::4",
        "rate:3:9:0",
        "rate:3:9:6",
        "clear:3:9:",
    ],
)
def test_malformed_payloads_are_rejected_loudly(raw):
    with pytest.raises(ValueError):
        decode(raw)
