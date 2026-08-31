from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.domain.models import EventTally, VoteCast, VoteOut
from app.services import voting_service

router = APIRouter(tags=["voting"])


@router.post(
    "/events/{event_id}/proposed-dates/{proposed_date_id}/votes",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Say whether you can make this date",
)
def cast_vote(
    event_id: int,
    proposed_date_id: int,
    payload: VoteCast,
    session: Session = Depends(get_session),
) -> None:
    """Voting again on the same date replaces the earlier answer."""
    voting_service.cast_vote(session, event_id, proposed_date_id, payload)


@router.get(
    "/events/{event_id}/votes",
    response_model=list[VoteOut],
    summary="Who answered what, individually",
)
def list_votes(event_id: int, session: Session = Depends(get_session)) -> list[VoteOut]:
    """The tally gives totals; this gives the individual answers a timeline needs."""
    return voting_service.list_votes(session, event_id)


@router.get(
    "/events/{event_id}/tally",
    response_model=EventTally,
    summary="Current standings, with the leading date and who still owes a vote",
)
def get_tally(event_id: int, session: Session = Depends(get_session)) -> EventTally:
    return voting_service.get_tally(session, event_id)
