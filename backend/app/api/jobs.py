from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.scheduler.jobs import ReminderPreview, send_event_reminders

router = APIRouter(tags=["jobs"])


@router.post(
    "/jobs/reminders",
    response_model=list[ReminderPreview],
    summary="Run the reminder job now (logs instead of sending)",
)
def run_reminders(session: Session = Depends(get_session)) -> list[ReminderPreview]:
    """Manual trigger standing in for the cron that would call this on a schedule."""
    return send_event_reminders(session)
