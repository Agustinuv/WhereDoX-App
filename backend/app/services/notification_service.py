"""The Telegram implementation of NotificationPort, plus the choice of which one to use.

Outbound messages are plain HTTPS calls to the Bot API, not the bot library: sending needs
only the token, so the API process can notify without talking to the bot process. The bot
library is used solely for *receiving* updates, in bot/.

Delivery never breaks the caller. A group whose members have not linked Telegram yet still
gets its dates proposed and its votes tallied; a failed send is logged and dropped.
"""

import logging
from functools import lru_cache

import httpx

from app.core.config import get_settings
from app.services.ports import ButtonRows, LoggingNotifier, NotificationPort

logger = logging.getLogger(__name__)

API_ROOT = "https://api.telegram.org"
TIMEOUT_SECONDS = 10.0


class TelegramNotifier(NotificationPort):
    def __init__(self, token: str) -> None:
        # The token sits in the URL, so this string is a secret: never log it.
        self._base_url = f"{API_ROOT}/bot{token}"

    def _call(self, method: str, payload: dict) -> dict | None:
        try:
            response = httpx.post(
                f"{self._base_url}/{method}", json=payload, timeout=TIMEOUT_SECONDS
            )
            body = response.json()
        except (httpx.HTTPError, ValueError) as error:
            logger.warning("Telegram %s failed: %s", method, error)
            return None

        if not body.get("ok"):
            # description is Telegram's own error text and carries no token.
            logger.warning("Telegram %s rejected: %s", method, body.get("description"))
            return None
        return body.get("result")

    def send_message(self, chat_id: int, text: str, buttons: ButtonRows | None = None) -> None:
        payload: dict = {"chat_id": chat_id, "text": text}
        if buttons:
            payload["reply_markup"] = {
                "inline_keyboard": [
                    [{"text": button.label, "callback_data": button.data} for button in row]
                    for row in buttons
                ]
            }
        self._call("sendMessage", payload)

    def send_choice_poll(self, chat_id: int, question: str, options: list[str]) -> str | None:
        # is_anonymous must be false: Telegram omits the voter from poll_answer otherwise,
        # and without the voter there is nobody to attribute the availability to.
        result = self._call(
            "sendPoll",
            {
                "chat_id": chat_id,
                "question": question,
                "options": options,
                "allows_multiple_answers": True,
                "is_anonymous": False,
            },
        )
        if result is None:
            return None
        return result.get("poll", {}).get("id")


@lru_cache
def get_notifier() -> NotificationPort:
    """Telegram when a token is configured, the logging stub otherwise."""
    token = get_settings().telegram_bot_token
    if not token:
        logger.info("No TELEGRAM_BOT_TOKEN set; notifications will be logged, not sent.")
        return LoggingNotifier(logger)
    return TelegramNotifier(token)
