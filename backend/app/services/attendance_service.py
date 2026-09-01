"""Closing the coordination loop: confirming a date, then tracking who actually came."""

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.domain.models import AttendanceOut, AttendanceSet, DateConfirm
from app.domain.tables import Event
from app.repositories import (
    attendance_repository,
    event_repository,
    group_repository,
    vote_repository,
)
from app.services import announcement_service, event_service, voting_service


def confirm_date(session: Session, event_id: int, payload: DateConfirm) -> Event:
    """The host locks a slot, which freezes the attendance list and advances the rotation."""
    event = event_service.require_event(session, event_id)
    event_service.require_host(event, payload.person_id)
    if event.status != "voting":
        raise ConflictError(f"Event {event_id} is {event.status}; there is nothing to confirm.")

    proposed_date_id = _resolve_date(session, event_id, payload)
    proposed = event_repository.get_proposed_date(session, proposed_date_id)
    if proposed is None or proposed.event_id != event_id:
        raise NotFoundError(
            f"Proposed date {proposed_date_id} does not belong to event {event_id}."
        )

    _create_attendance_list(session, event, proposed_date_id)
    event_repository.confirm_date(session, event, proposed_date_id)

    # The rotation advances on confirmation, not on completion: the hosting slot is taken
    # as soon as the date is locked, and a cancelled event is rare enough to fix by hand.
    group_repository.set_last_hosted_at(
        session, event.group_id, event.host_id, proposed.starts_at.date()
    )
    announcement_service.announce_confirmation(session, event_id)
    return event


def _resolve_date(session: Session, event_id: int, payload: DateConfirm) -> int:
    if payload.proposed_date_id is not None:
        return payload.proposed_date_id

    tally = voting_service.get_tally(session, event_id)
    if tally.leading_date_id is None:
        raise ConflictError("No one has voted yes or maybe yet, so there is no leading date.")
    if tally.is_tie:
        raise ConflictError(
            "Several dates are tied; pass proposed_date_id explicitly to break the tie."
        )
    return tally.leading_date_id


def _create_attendance_list(session: Session, event: Event, proposed_date_id: int) -> None:
    """Everyone available on the winning slot is expected, and so is the host."""
    votes = vote_repository.list_for_date(session, proposed_date_id)
    expected = {vote.person_id for vote in votes if vote.availability in ("yes", "maybe")}
    expected.add(event.host_id)

    already = {
        attendance.person_id
        for attendance, _ in attendance_repository.list_for_event(session, event.id)
    }
    attendance_repository.create_many(session, event.id, sorted(expected - already))


def set_attendance(session: Session, event_id: int, payload: AttendanceSet) -> None:
    """Reconcile the expected list with who actually turned up."""
    event = event_service.require_event(session, event_id)
    if event.status not in ("confirmed", "completed"):
        raise ConflictError(
            f"Event {event_id} is {event.status}; attendance only exists once a date is confirmed."
        )
    event_service.require_active_member(session, event.group_id, payload.person_id)
    attendance_repository.set_status(session, event_id, payload.person_id, payload.status)


def list_attendance(session: Session, event_id: int) -> list[AttendanceOut]:
    event_service.require_event(session, event_id)
    return [
        AttendanceOut(person_id=person.id, name=person.name, status=attendance.status)
        for attendance, person in attendance_repository.list_for_event(session, event_id)
    ]


def complete_event(session: Session, event_id: int, person_id: int) -> Event:
    """Close the event so games played and ratings become the only remaining input."""
    event = event_service.require_event(session, event_id)
    event_service.require_host(event, person_id)
    if event.status != "confirmed":
        raise ConflictError(
            f"Event {event_id} is {event.status}; only a confirmed event completes."
        )
    event_repository.set_status(session, event, "completed")

    # Ratings are the step people forget, so the ask goes out the moment the night closes
    # rather than waiting for someone to open the app.
    announcement_service.request_ratings(session, event_id)
    return event
