"""One logging setup, shared by both entrypoints.

It exists for a single reason: httpx logs every request line at INFO, and a Telegram Bot
API URL carries the bot token in its path. With plain basicConfig the token ends up in
container logs in clear text — a real credential leak, from a library nobody configured on
purpose. Silencing httpx below WARNING is not cosmetic, so do not "restore" it.
"""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
