"""Event lifecycle: creation (with the host chosen by rotation), date proposal, summary."""

from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.clock import ensure_utc
from app.core.constants import MAX_PROPOSED_DATES
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.domain.models import (
    AttendanceOut,
    EventCreate,
    EventOut,
    EventSummary,
    GamePlayedOut,
    GameRatingSummary,
)
from app.domain.tables import Event, ProposedDate
from app.repositories import (
    attendance_repository,
    event_repository,
    group_repository,
    person_repository,
    rating_repository,
)
from app.services import host_rotation_service


def require_event(session: Session, event_id: int) -> Event:
    event = event_repository.get(session, event_id)
    if event is None:
        raise NotFoundError(f"Event {event_id} does not exist.")
    return event


def require_host(event: Event, person_id: int) -> None:
    if event.host_id != person_id:
        raise ConflictError(
            f"Only the host (person {event.host_id}) can do this; person {person_id} cannot."
        )


def require_active_member(session: Session, group_id: int, person_id: int) -> None:
    membership = group_repository.get_membership(session, group_id, person_id)
    if membership is None:
        raise ConflictError(f"Person {person_id} is not a member of group {group_id}.")
    if not membership.is_active:
        raise ConflictError(f"Person {person_id} is not an active member of group {group_id}.")


def create_event(session: Session, group_id: int, payload: EventCreate) -> Event:
    """Create an event and assign its host, by rotation unless one is named explicitly."""
    if group_repository.get(session, group_id) is None:
        raise NotFoundError(f"Group {group_id} does not exist.")

    if payload.host_id is not None:
        require_active_member(session, group_id, payload.host_id)
        host_id = payload.host_id
    else:
        candidates = host_rotation_service.load_candidates(session, group_id)
        host_id = host_rotation_service.select_next_host(candidates).candidate.person_id

    return event_repository.create(session, group_id, host_id, payload.title)


def propose_dates(
    session: Session, event_id: int, person_id: int, starts_at: list[datetime]
) -> list[ProposedDate]:
    """The host offers candidate slots, which opens voting."""
    event = require_event(session, event_id)
    require_host(event, person_id)
    if event.status not in ("draft", "voting"):
        raise ConflictError(f"Event {event_id} is {event.status}; dates can no longer be proposed.")

    wanted = {ensure_utc(moment) for moment in starts_at}
    existing = {
        proposed.starts_at for proposed in event_repository.list_proposed_dates(session, event_id)
    }
    fresh = sorted(wanted - existing)
    if not fresh:
        raise ValidationError("Every proposed date is already on this event.")

    # The schema caps one request; this caps the event. Without it a host could call the
    # endpoint repeatedly and end up with an unvotable wall of dates.
    if len(existing) + len(fresh) > MAX_PROPOSED_DATES:
        raise ValidationError(
            f"An event can hold at most {MAX_PROPOSED_DATES} proposed dates: "
            f"it already has {len(existing)} and you are adding {len(fresh)}."
        )

    event_repository.add_proposed_dates(session, event_id, fresh)
    if event.status == "draft":
        event_repository.set_status(session, event, "voting")
    return event_repository.list_proposed_dates(session, event_id)


def list_events(session: Session, group_id: int) -> list[Event]:
    if group_repository.get(session, group_id) is None:
        raise NotFoundError(f"Group {group_id} does not exist.")
    return event_repository.list_by_group(session, group_id)


def list_proposed_dates(session: Session, event_id: int) -> list[ProposedDate]:
    require_event(session, event_id)
    return event_repository.list_proposed_dates(session, event_id)


def cancel_event(session: Session, event_id: int, person_id: int) -> Event:
    event = require_event(session, event_id)
    require_host(event, person_id)
    if event.status == "completed":
        raise ConflictError(f"Event {event_id} is already completed and cannot be cancelled.")
    event_repository.set_status(session, event, "cancelled")
    return event


def build_summary(session: Session, event_id: int) -> EventSummary:
    event = require_event(session, event_id)

    host = person_repository.get(session, event.host_id)
    confirmed_starts_at = _confirmed_start(session, event)

    attendees = [
        AttendanceOut(person_id=person.id, name=person.name, status=attendance.status)
        for attendance, person in attendance_repository.list_for_event(session, event_id)
    ]
    games_played = [
        GamePlayedOut(id=played.id, game_id=game.id, game_name=game.name)
        for played, game in rating_repository.list_games_played(session, event_id)
    ]

    return EventSummary(
        event=EventOut.model_validate(event),
        host_name=host.name if host else "unknown",
        confirmed_starts_at=confirmed_starts_at,
        attendees=attendees,
        games_played=games_played,
        ratings=_summarise_ratings(session, event_id),
    )


def _confirmed_start(session: Session, event: Event) -> datetime | None:
    if event.confirmed_date_id is None:
        return None
    confirmed: ProposedDate | None = event_repository.get_proposed_date(
        session, event.confirmed_date_id
    )
    return confirmed.starts_at if confirmed else None


def _summarise_ratings(session: Session, event_id: int) -> list[GameRatingSummary]:
    scores: dict[int, list[int]] = defaultdict(list)
    names: dict[int, str] = {}
    for rating, game in rating_repository.list_for_event(session, event_id):
        scores[game.id].append(rating.score)
        names[game.id] = game.name

    return [
        GameRatingSummary(
            game_id=game_id,
            game_name=names[game_id],
            average_score=round(sum(values) / len(values), 2),
            votes=len(values),
        )
        for game_id, values in sorted(scores.items(), key=lambda item: names[item[0]])
    ]
