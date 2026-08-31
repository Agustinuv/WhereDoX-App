from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.tables import Event, ProposedDate


def create(session: Session, group_id: int, host_id: int, title: str) -> Event:
    event = Event(group_id=group_id, host_id=host_id, title=title, status="draft")
    session.add(event)
    session.flush()
    return event


def get(session: Session, event_id: int) -> Event | None:
    return session.get(Event, event_id)


def list_by_group(session: Session, group_id: int) -> list[Event]:
    # created_at defaults to now(), which in Postgres is the *transaction* timestamp: two
    # events seeded in one transaction share it exactly. id breaks that tie so "most
    # recent first" is deterministic.
    stmt = (
        select(Event)
        .where(Event.group_id == group_id)
        .order_by(Event.created_at.desc(), Event.id.desc())
    )
    return list(session.scalars(stmt))


def set_status(session: Session, event: Event, status: str) -> None:
    event.status = status
    session.flush()


def confirm_date(session: Session, event: Event, proposed_date_id: int) -> None:
    event.confirmed_date_id = proposed_date_id
    event.status = "confirmed"
    session.flush()


def add_proposed_dates(
    session: Session, event_id: int, starts_at: list[datetime]
) -> list[ProposedDate]:
    dates = [ProposedDate(event_id=event_id, starts_at=moment) for moment in starts_at]
    session.add_all(dates)
    session.flush()
    return dates


def list_proposed_dates(session: Session, event_id: int) -> list[ProposedDate]:
    stmt = (
        select(ProposedDate)
        .where(ProposedDate.event_id == event_id)
        .order_by(ProposedDate.starts_at)
    )
    return list(session.scalars(stmt))


def get_proposed_date(session: Session, proposed_date_id: int) -> ProposedDate | None:
    return session.get(ProposedDate, proposed_date_id)


def list_upcoming_confirmed(session: Session, until: datetime) -> list[tuple[Event, ProposedDate]]:
    """Confirmed events starting between now and `until` — the reminder job's input."""
    stmt = (
        select(Event, ProposedDate)
        .join(ProposedDate, ProposedDate.id == Event.confirmed_date_id)
        .where(Event.status == "confirmed", ProposedDate.starts_at <= until)
        .order_by(ProposedDate.starts_at)
    )
    return [(event, proposed) for event, proposed in session.execute(stmt)]
