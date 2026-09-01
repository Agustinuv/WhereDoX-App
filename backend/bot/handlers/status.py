"""/junta — where does my next game night stand, and what can I still tap?

This exists for the live demo. Every other message the bot sends is a push, and a push
scrolls away; if the reminder with the "dame sugerencias" button is three screens up, the
demo stalls. /junta reprints the state and re-offers whatever buttons still apply, so
there is always a way back into the flow.

It decides nothing. Status, tally and recommendations all come from the services that the
REST API calls; what is written here is the phrasing.
"""

import logging

from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import ContextTypes

from app.core.callbacks import Callback, encode
from app.core.constants import MAX_RATING, MIN_RATING
from app.core.formatting import format_slot
from app.domain.tables import Event
from app.repositories import (
    attendance_repository,
    event_repository,
    group_repository,
    person_repository,
    rating_repository,
)
from app.services import voting_service
from app.services.ports import Button, ButtonRows
from bot.keyboards import to_markup
from bot.session import in_session

logger = logging.getLogger(__name__)

NOT_LINKED = (
    "No reconozco tu cuenta todavía. Abre tu enlace personal para vincularla y "
    "vuelve a intentar."
)
NO_EVENTS = "Todavía no hay ninguna junta en tus grupos."

STATUS_LABEL = {
    "draft": "sin fechas todavía",
    "voting": "votando",
    "confirmed": "confirmada",
    "completed": "cerrada",
    "cancelled": "cancelada",
}


async def junta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    telegram_user = update.effective_user
    if message is None or telegram_user is None:
        return

    payload = await in_session(lambda session: _load(session, telegram_user.id))
    if payload is None:
        await message.reply_text(NOT_LINKED)
        return

    text, buttons = payload
    await message.reply_text(text, reply_markup=to_markup(buttons))


def _load(session: Session, telegram_user_id: int) -> tuple[str, ButtonRows] | None:
    person = person_repository.get_by_telegram_user_id(session, telegram_user_id)
    if person is None:
        return None

    event = _latest_event(session, person.id)
    if event is None:
        return NO_EVENTS, []

    host = person_repository.get(session, event.host_id)
    lines = [f"📋 {event.title} — {STATUS_LABEL.get(event.status, event.status)}"]
    if host is not None:
        mine = " (tú)" if host.id == person.id else ""
        lines.append(f"🏠 Anfitrión/a: {host.name}{mine}")

    buttons: ButtonRows = []
    if event.status == "voting":
        lines.extend(_voting_lines(session, event))
    elif event.status == "confirmed":
        lines.extend(_confirmed_lines(session, event))
        buttons = [
            [
                Button(
                    label="🎲 Dame sugerencias",
                    data=encode(Callback(kind="suggest", event_id=event.id)),
                )
            ]
        ]
    elif event.status == "completed":
        lines.extend(_confirmed_lines(session, event))
        rating_lines, buttons = _rating_rows(session, event)
        lines.extend(rating_lines)

    return "\n".join(lines), buttons


OVER = ("completed", "cancelled")


def _latest_event(session: Session, person_id: int) -> Event | None:
    """ "My junta": the newest one still going, or the last one played if none is.

    Newest-overall would be wrong. A group that just closed a night and opened the next
    one would answer /junta with the closed one until somebody proposed a date, which is
    precisely when a person is most likely to be asking.
    """
    events: list[Event] = []
    for group in group_repository.list_for_person(session, person_id):
        events.extend(event_repository.list_by_group(session, group.id))
    if not events:
        return None

    live = [event for event in events if event.status not in OVER]
    return max(live or events, key=lambda event: event.id)


def _voting_lines(session: Session, event: Event) -> list[str]:
    tally = voting_service.get_tally(session, event.id)
    answered = tally.eligible_voters - _pending_count(tally)
    lines = [
        f"📅 {len(tally.dates)} fechas propuestas",
        f"🗳 Han votado {answered} de {tally.eligible_voters}",
    ]

    leading = next(
        (date for date in tally.dates if date.proposed_date_id == tally.leading_date_id), None
    )
    if leading is not None:
        note = " (empate, alguien tiene que elegir)" if tally.is_tie else ""
        lines.append(f"👉 Va ganando {format_slot(leading.starts_at)}{note}")

    pending = _pending_names(tally)
    if pending:
        lines.append(f"⏳ Faltan: {', '.join(pending)}")
    return lines


def _pending_names(tally) -> list[str]:
    """Someone who has not answered any date at all still owes a vote."""
    if not tally.dates:
        return []
    pending = set(tally.dates[0].missing_voters)
    for date in tally.dates[1:]:
        pending &= set(date.missing_voters)
    return sorted(pending)


def _pending_count(tally) -> int:
    return len(_pending_names(tally))


def _confirmed_lines(session: Session, event: Event) -> list[str]:
    lines = []
    if event.confirmed_date_id is not None:
        confirmed = event_repository.get_proposed_date(session, event.confirmed_date_id)
        if confirmed is not None:
            lines.append(f"📅 {format_slot(confirmed.starts_at)}")

    expected = [
        person
        for attendance, person in attendance_repository.list_for_event(session, event.id)
        if attendance.status in ("expected", "attended")
    ]
    lines.append(f"👥 Van {len(expected)}: {', '.join(person.name for person in expected)}")

    played = rating_repository.list_games_played(session, event.id)
    if played:
        lines.append(f"🎲 Se jugó: {', '.join(game.name for _, game in played)}")
    return lines


def _rating_rows(session: Session, event: Event) -> tuple[list[str], ButtonRows]:
    """One row of 1-5 per game.

    A row cannot carry a heading, and "7 Wonders: 4" repeated five times is unreadable on a
    phone. So the buttons stay bare numbers and the text above names the games in the same
    order the rows appear.
    """
    played = rating_repository.list_games_played(session, event.id)
    if not played:
        return [], []

    names = [game.name for _, game in played]
    heading = (
        f"⭐ Valora {names[0]}:" if len(names) == 1 else f"⭐ Valora, en orden: {', '.join(names)}"
    )

    rows: ButtonRows = [
        [
            Button(
                label=str(score),
                data=encode(Callback(kind="rate", event_id=event.id, game_id=game.id, score=score)),
            )
            for score in range(MIN_RATING, MAX_RATING + 1)
        ]
        for _, game in played
    ]
    return [heading], rows
