from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.tables import TelegramPoll


def record(
    session: Session,
    telegram_poll_id: str,
    event_id: int,
    chat_id: int,
    proposed_date_ids: list[int],
) -> TelegramPoll:
    poll = TelegramPoll(
        telegram_poll_id=telegram_poll_id,
        event_id=event_id,
        chat_id=chat_id,
        proposed_date_ids=proposed_date_ids,
    )
    session.add(poll)
    session.flush()
    return poll


def get_by_telegram_poll_id(session: Session, telegram_poll_id: str) -> TelegramPoll | None:
    stmt = select(TelegramPoll).where(TelegramPoll.telegram_poll_id == telegram_poll_id)
    return session.scalars(stmt).first()
