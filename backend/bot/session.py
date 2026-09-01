"""Bridging the async bot library to the synchronous data layer."""

import asyncio
from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


async def in_session(work: Callable[[Session], T]) -> T:
    """Run one unit of database work as a transaction, off the event loop.

    The repositories are synchronous SQLAlchemy and python-telegram-bot is asyncio, so the
    work goes to a worker thread instead of blocking the poller. An async rewrite of the
    data layer would have meant two versions of every repository — one for the API, one for
    the bot — for no benefit at this size.
    """

    # Imported here, not at module scope: app.core.database builds its engine on import,
    # so a top-level import would make merely *loading* a handler require a reachable
    # DATABASE_URL — and the handlers' unit tests deliberately have neither.
    from app.core.database import SessionFactory

    def run() -> T:
        session = SessionFactory()
        try:
            result = work(session)
            session.commit()
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return await asyncio.to_thread(run)
