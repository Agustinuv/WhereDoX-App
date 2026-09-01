"""Turning the port's channel-agnostic Button rows into Telegram markup.

app/ builds buttons without knowing what a keyboard is; this is the one place that knows.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.ports import ButtonRows


def to_markup(rows: ButtonRows) -> InlineKeyboardMarkup | None:
    if not rows:
        return None
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(button.label, callback_data=button.data) for button in row]
            for row in rows
        ]
    )
