"""What the group hears, and when.

Each function turns one domain moment into an outbound message, then hands it to the
NotificationPort — so this module knows about game nights and nothing about Telegram, and
notification_service knows about Telegram and nothing about game nights.

The text here is copy read by end users, so it is Spanish rather than the codebase's
English, same rule as the recommender's reasons.

Nothing in here is allowed to fail the caller: a member who never linked Telegram, or a
chat the bot cannot write to, must not stop dates being proposed or a date being confirmed.
Every function reports how many people it actually reached instead of raising.
"""

import logging
from functools import wraps

from sqlalchemy.orm import Session

from app.core.callbacks import Callback, encode
from app.core.constants import MAX_RATING, MIN_RATING
from app.core.formatting import format_slot
from app.domain.tables import Event, Person
from app.repositories import (
    event_repository,
    group_repository,
    person_repository,
    rating_repository,
    telegram_poll_repository,
)
from app.services.notification_service import get_notifier
from app.services.ports import Button

logger = logging.getLogger(__name__)

# Telegram refuses a poll with fewer than two options, and an event may legitimately have
# a single proposed date. A closing "none of these" option fixes both the API limit and a
# real gap: saying "I can't make any of them" becomes an act instead of silence.
NO_SLOT_WORKS = "Ninguna me sirve"


def never_fails(announce):
    """Broad by design: announcing is a side channel, and it does not get a vote.

    A date is confirmed whether or not the group heard about it. Letting a chat failure
    propagate would roll back the transaction that made the decision, which is a far worse
    outcome than an undelivered message.
    """

    @wraps(announce)
    def guarded(*args, **kwargs) -> int:
        try:
            return announce(*args, **kwargs)
        except Exception:
            logger.exception("Could not announce via %s", announce.__name__)
            return 0

    return guarded


@never_fails
def announce_host_assignment(session: Session, event_id: int) -> int:
    """Tell the host the rotation picked them. Only them — nobody else needs this yet.

    The message does not repeat *why* they were picked. The reason is produced by
    select_next_host and re-deriving it here would duplicate the rule in a second place,
    which is exactly what the pure-function split exists to prevent; GET /next-host and
    the web client already show it verbatim.
    """
    event = event_repository.get(session, event_id)
    if event is None:
        return 0

    host = person_repository.get(session, event.host_id)
    if host is None or host.telegram_user_id is None:
        return 0

    get_notifier().send_message(
        host.telegram_user_id,
        f"🎲 Te tocó ser anfitrión/a de «{event.title}».\n"
        "Fue por rotación. Propón las fechas y el grupo vota.",
    )
    return 1


@never_fails
def announce_vote(session: Session, event_id: int) -> int:
    """Send everyone the availability poll for this event. Returns how many were reached."""
    event = event_repository.get(session, event_id)
    dates = event_repository.list_proposed_dates(session, event_id)
    if event is None or not dates:
        return 0

    question = f"{event.title}: ¿qué fechas te sirven? (marca todas las que puedas)"
    options = [format_slot(date.starts_at) for date in dates] + [NO_SLOT_WORKS]
    date_ids = [date.id for date in dates]

    notifier = get_notifier()
    reached = 0
    for person in _reachable_members(session, event.group_id):
        poll_id = notifier.send_choice_poll(person.telegram_user_id, question, options)
        if poll_id is None:
            continue
        telegram_poll_repository.record(
            session, poll_id, event_id, person.telegram_user_id, date_ids
        )
        reached += 1
    return reached


@never_fails
def announce_confirmation(session: Session, event_id: int) -> int:
    """Tell the group the date is locked, so an answered poll does not vanish into silence."""
    event = event_repository.get(session, event_id)
    if event is None or event.confirmed_date_id is None:
        return 0

    confirmed = event_repository.get_proposed_date(session, event.confirmed_date_id)
    if confirmed is None:
        return 0

    host = person_repository.get(session, event.host_id)
    text = (
        f"✅ Confirmado: {event.title}\n"
        f"📅 {format_slot(confirmed.starts_at)}\n"
        f"🏠 Anfitrión/a: {host.name if host else 'por definir'}"
    )
    return _broadcast(text, _reachable_members(session, event.group_id))


@never_fails
def remind(session: Session, event: Event, recipients: list[Person]) -> int:
    """The reminder, with the buttons that let someone ask what to play without typing."""
    if event.confirmed_date_id is None:
        return 0
    confirmed = event_repository.get_proposed_date(session, event.confirmed_date_id)
    if confirmed is None:
        return 0

    host = person_repository.get(session, event.host_id)
    text = (
        f"⏰ Se viene {event.title}\n"
        f"📅 {format_slot(confirmed.starts_at)}\n"
        f"🏠 En casa de {host.name if host else 'quien organiza'}"
    )
    buttons = [
        [Button(label="👍 Lo tengo claro", data=encode(Callback(kind="clear", event_id=event.id)))],
        [
            Button(
                label="🎲 Dame sugerencias",
                data=encode(Callback(kind="suggest", event_id=event.id)),
            )
        ],
        [
            Button(
                label="⏳ Recuérdame más tarde",
                data=encode(Callback(kind="later", event_id=event.id)),
            )
        ],
    ]

    notifier = get_notifier()
    reached = 0
    for person in _with_telegram(recipients):
        notifier.send_message(person.telegram_user_id, text, buttons)
        reached += 1
    return reached


@never_fails
def request_ratings(session: Session, event_id: int, only_game_id: int | None = None) -> int:
    """One message per game played, with the 1-5 scale as a single row of buttons.

    only_game_id narrows it to a single game, for the host who logs what was played *after*
    closing the night. Without it that game would never be asked about, because the ask
    fires on completion and there was nothing to ask about yet.
    """
    event = event_repository.get(session, event_id)
    if event is None:
        return 0

    games = rating_repository.list_games_played(session, event_id)
    if only_game_id is not None:
        games = [(played, game) for played, game in games if game.id == only_game_id]
    if not games:
        return 0

    notifier = get_notifier()
    people = _reachable_members(session, event.group_id)
    reached = 0
    for person in people:
        for _, game in games:
            scale = [
                Button(
                    label=str(score),
                    data=encode(
                        Callback(kind="rate", event_id=event_id, game_id=game.id, score=score)
                    ),
                )
                for score in range(MIN_RATING, MAX_RATING + 1)
            ]
            notifier.send_message(
                person.telegram_user_id,
                f"¿Qué te pareció {game.name}? (1 = malo, {MAX_RATING} = excelente)",
                [scale],
            )
        reached += 1
    return reached


def _reachable_members(session: Session, group_id: int) -> list[Person]:
    """Active members who have linked Telegram. Everyone else is simply unreachable."""
    members = group_repository.list_members(session, group_id, active_only=True)
    return _with_telegram([person for _, person in members])


def _with_telegram(people: list[Person]) -> list[Person]:
    return [person for person in people if person.telegram_user_id is not None]


def _broadcast(text: str, recipients: list[Person]) -> int:
    notifier = get_notifier()
    for person in recipients:
        notifier.send_message(person.telegram_user_id, text)
    return len(recipients)
