from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.tables import Person


def create(session: Session, name: str, telegram_user_id: int | None) -> Person:
    person = Person(name=name, telegram_user_id=telegram_user_id)
    session.add(person)
    session.flush()
    return person


def get(session: Session, person_id: int) -> Person | None:
    return session.get(Person, person_id)


def list_all(session: Session) -> list[Person]:
    return list(session.scalars(select(Person).order_by(Person.name)))


def get_by_telegram_user_id(session: Session, telegram_user_id: int) -> Person | None:
    """Identity resolution for the bot: an incoming update carries only this id."""
    stmt = select(Person).where(Person.telegram_user_id == telegram_user_id)
    return session.scalars(stmt).first()


def set_telegram_user_id(session: Session, person: Person, telegram_user_id: int) -> Person:
    person.telegram_user_id = telegram_user_id
    session.flush()
    return person


def clear_telegram_user_id(session: Session, person: Person) -> Person:
    person.telegram_user_id = None
    session.flush()
    return person
