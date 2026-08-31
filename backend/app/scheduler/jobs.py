"""Scheduled jobs.

Deliberately a stub: the reminder logs what it *would* send instead of sending anything.
Nothing else in the project imports a delivery channel, so replacing this body with a
Telegram call — driven by a real cron such as Cloud Scheduler — touches only this module.
"""

import logging
from datetime import timedelta

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.clock import now
from app.core.config import get_settings
from app.repositories import attendance_repository, event_repository

logger = logging.getLogger(__name__)


class ReminderPreview(BaseModel):
    event_id: int
    title: str
    starts_at: str
    recipients: list[str]


def send_event_reminders(session: Session) -> list[ReminderPreview]:
    """Log a reminder for every confirmed event starting inside the lead window."""
    lead_hours = get_settings().reminder_lead_hours
    horizon = now() + timedelta(hours=lead_hours)

    reminders: list[ReminderPreview] = []
    for event, proposed in event_repository.list_upcoming_confirmed(session, horizon):
        if proposed.starts_at < now():
            continue
        recipients = [
            person.name
            for attendance, person in attendance_repository.list_for_event(session, event.id)
            if attendance.status == "expected"
        ]
        logger.info(
            "Reminder for event %s (%s) starting %s: would notify %s",
            event.id,
            event.title,
            proposed.starts_at.isoformat(),
            ", ".join(recipients) or "nobody",
        )
        reminders.append(
            ReminderPreview(
                event_id=event.id,
                title=event.title,
                starts_at=proposed.starts_at.isoformat(),
                recipients=recipients,
            )
        )
    return reminders
