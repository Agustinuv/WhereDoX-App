from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.tables import AvailabilityVote, Person, ProposedDate


def upsert(
    session: Session, proposed_date_id: int, person_id: int, availability: str
) -> AvailabilityVote:
    """Voting again on the same slot overwrites the previous answer rather than stacking."""
    stmt = select(AvailabilityVote).where(
        AvailabilityVote.proposed_date_id == proposed_date_id,
        AvailabilityVote.person_id == person_id,
    )
    vote = session.scalars(stmt).first()
    if vote is None:
        vote = AvailabilityVote(
            proposed_date_id=proposed_date_id,
            person_id=person_id,
            availability=availability,
        )
        session.add(vote)
    else:
        vote.availability = availability
    session.flush()
    return vote


def list_for_event(session: Session, event_id: int) -> list[AvailabilityVote]:
    """Every vote across every proposed slot of one event.

    Returned raw so the tally itself stays a pure function in the service layer.
    """
    stmt = (
        select(AvailabilityVote)
        .join(ProposedDate, ProposedDate.id == AvailabilityVote.proposed_date_id)
        .where(ProposedDate.event_id == event_id)
    )
    return list(session.scalars(stmt))


def list_for_event_with_people(
    session: Session, event_id: int
) -> list[tuple[AvailabilityVote, Person]]:
    """Individual votes with the voter's name, for showing who answered what."""
    stmt = (
        select(AvailabilityVote, Person)
        .join(ProposedDate, ProposedDate.id == AvailabilityVote.proposed_date_id)
        .join(Person, Person.id == AvailabilityVote.person_id)
        .where(ProposedDate.event_id == event_id)
        .order_by(AvailabilityVote.voted_at, AvailabilityVote.id)
    )
    return [(vote, person) for vote, person in session.execute(stmt)]


def list_for_date(session: Session, proposed_date_id: int) -> list[AvailabilityVote]:
    stmt = select(AvailabilityVote).where(AvailabilityVote.proposed_date_id == proposed_date_id)
    return list(session.scalars(stmt))
