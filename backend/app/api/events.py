from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.domain.models import (
    DatesPropose,
    EventCreate,
    EventOut,
    EventSummary,
    ProposedDateOut,
)
from app.services import event_service

router = APIRouter(tags=["events"])


@router.post(
    "/groups/{group_id}/events",
    response_model=EventOut,
    status_code=status.HTTP_201_CREATED,
    summary="Start a game night (host assigned by rotation)",
)
def create_event(
    group_id: int, payload: EventCreate, session: Session = Depends(get_session)
) -> EventOut:
    return EventOut.model_validate(event_service.create_event(session, group_id, payload))


@router.get("/groups/{group_id}/events", response_model=list[EventOut])
def list_events(group_id: int, session: Session = Depends(get_session)) -> list[EventOut]:
    return [
        EventOut.model_validate(event) for event in event_service.list_events(session, group_id)
    ]


@router.get("/events/{event_id}", response_model=EventOut)
def get_event(event_id: int, session: Session = Depends(get_session)) -> EventOut:
    return EventOut.model_validate(event_service.require_event(session, event_id))


@router.post(
    "/events/{event_id}/proposed-dates",
    response_model=list[ProposedDateOut],
    status_code=status.HTTP_201_CREATED,
    summary="Host proposes candidate dates, which opens voting",
)
def propose_dates(
    event_id: int, payload: DatesPropose, session: Session = Depends(get_session)
) -> list[ProposedDateOut]:
    dates = event_service.propose_dates(session, event_id, payload.person_id, payload.starts_at)
    return [ProposedDateOut.model_validate(date) for date in dates]


@router.get("/events/{event_id}/proposed-dates", response_model=list[ProposedDateOut])
def list_proposed_dates(
    event_id: int, session: Session = Depends(get_session)
) -> list[ProposedDateOut]:
    return [
        ProposedDateOut.model_validate(date)
        for date in event_service.list_proposed_dates(session, event_id)
    ]


@router.get(
    "/events/{event_id}/summary",
    response_model=EventSummary,
    summary="Everything about one game night in a single response",
)
def event_summary(event_id: int, session: Session = Depends(get_session)) -> EventSummary:
    return event_service.build_summary(session, event_id)


@router.post("/events/{event_id}/cancel", response_model=EventOut)
def cancel_event(
    event_id: int, person_id: int, session: Session = Depends(get_session)
) -> EventOut:
    return EventOut.model_validate(event_service.cancel_event(session, event_id, person_id))
