"""Scheduled jobs.

The reminder used to log what it would have sent. It now hands the message to a
NotificationPort, so with a bot token it reaches Telegram and without one it logs exactly
as before. What is still deliberately missing is a real cron: POST /jobs/reminders is the
manual trigger standing in for Cloud Scheduler.
"""

import logging
from datetime import timedelta

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.clock import now
from app.core.config import get_settings
from app.repositories import attendance_repository, event_repository
from app.services import announcement_service

logger = logging.getLogger(__name__)


class ReminderPreview(BaseModel):
    event_id: int
    title: str
    starts_at: str
    recipients: list[str]
    notified: int = 0


def send_event_reminders(session: Session) -> list[ReminderPreview]:
    """Remind every confirmed event starting inside the lead window."""
    lead_hours = get_settings().reminder_lead_hours
    horizon = now() + timedelta(hours=lead_hours)

    reminders: list[ReminderPreview] = []
    for event, proposed in event_repository.list_upcoming_confirmed(session, horizon):
        if proposed.starts_at < now():
            continue

        expected = [
            person
            for attendance, person in attendance_repository.list_for_event(session, event.id)
            if attendance.status == "expected"
        ]
        notified = announcement_service.remind(session, event, expected)
        logger.info(
            "Reminder for event %s (%s) starting %s: %s expected, %s reached",
            event.id,
            event.title,
            proposed.starts_at.isoformat(),
            len(expected),
            notified,
        )
        reminders.append(
            ReminderPreview(
                event_id=event.id,
                title=event.title,
                starts_at=proposed.starts_at.isoformat(),
                recipients=[person.name for person in expected],
                notified=notified,
            )
        )
    return reminders
