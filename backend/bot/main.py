"""Bot entrypoint: long polling, no webhook.

Polling means no public URL, no tunnel and no TLS termination to arrange for a demo — the
process just dials out. A webhook would be the right call under real load; at six people
per group it would only add infrastructure that can fail in front of an audience.

Run it with `python -m bot.main`, or as the `bot` service in docker-compose.
"""

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    PollAnswerHandler,
)

from app.core.config import get_settings
from app.core.logs import configure_logging
from bot.handlers import game_check, onboarding, rating, status, voting

configure_logging()
logger = logging.getLogger(__name__)


def build_application(token: str) -> Application:
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", onboarding.start))
    application.add_handler(CommandHandler("junta", status.junta))
    application.add_handler(PollAnswerHandler(voting.on_poll_answer))
    application.add_handler(CallbackQueryHandler(game_check.handle, pattern=game_check.PATTERN))
    application.add_handler(CallbackQueryHandler(rating.handle, pattern=rating.PATTERN))
    return application


def main() -> None:
    token = get_settings().telegram_bot_token
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN is not set. Add it to .env — the API runs without it, "
            "falling back to logged notifications, but the bot has nothing to connect to."
        )

    logger.info("Starting WhereDoX bot on long polling.")
    # Explicit rather than relying on Telegram's default set: poll_answer is the update
    # the whole date vote depends on, and a silent omission would look like a dead bot.
    build_application(token).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
