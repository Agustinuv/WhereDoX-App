from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.domain.models import AttendanceOut, AttendanceSet, DateConfirm, EventOut
from app.services import attendance_service

router = APIRouter(tags=["attendance"])


@router.post(
    "/events/{event_id}/confirm",
    response_model=EventOut,
    summary="Host locks the date, which freezes the guest list and advances the rotation",
)
def confirm_date(
    event_id: int, payload: DateConfirm, session: Session = Depends(get_session)
) -> EventOut:
    return EventOut.model_validate(attendance_service.confirm_date(session, event_id, payload))


@router.get("/events/{event_id}/attendance", response_model=list[AttendanceOut])
def list_attendance(event_id: int, session: Session = Depends(get_session)) -> list[AttendanceOut]:
    return attendance_service.list_attendance(session, event_id)


@router.put(
    "/events/{event_id}/attendance",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark who actually turned up",
)
def set_attendance(
    event_id: int, payload: AttendanceSet, session: Session = Depends(get_session)
) -> None:
    attendance_service.set_attendance(session, event_id, payload)


@router.post(
    "/events/{event_id}/complete",
    response_model=EventOut,
    summary="Close the night so games and ratings can be logged",
)
def complete_event(
    event_id: int, person_id: int, session: Session = Depends(get_session)
) -> EventOut:
    return EventOut.model_validate(attendance_service.complete_event(session, event_id, person_id))
