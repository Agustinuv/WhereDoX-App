from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.tables import Attendance, Person


def create_many(session: Session, event_id: int, person_ids: list[int]) -> list[Attendance]:
    rows = [Attendance(event_id=event_id, person_id=pid, status="expected") for pid in person_ids]
    session.add_all(rows)
    session.flush()
    return rows


def list_for_event(session: Session, event_id: int) -> list[tuple[Attendance, Person]]:
    stmt = (
        select(Attendance, Person)
        .join(Person, Person.id == Attendance.person_id)
        .where(Attendance.event_id == event_id)
        .order_by(Person.name)
    )
    return [(attendance, person) for attendance, person in session.execute(stmt)]


def get(session: Session, event_id: int, person_id: int) -> Attendance | None:
    stmt = select(Attendance).where(
        Attendance.event_id == event_id, Attendance.person_id == person_id
    )
    return session.scalars(stmt).first()


def set_status(session: Session, event_id: int, person_id: int, status: str) -> Attendance:
    """Upsert: someone who never voted can still turn up on the night."""
    attendance = get(session, event_id, person_id)
    if attendance is None:
        attendance = Attendance(event_id=event_id, person_id=person_id, status=status)
        session.add(attendance)
    else:
        attendance.status = status
    session.flush()
    return attendance
