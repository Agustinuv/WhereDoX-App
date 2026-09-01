"""The 1-5 buttons that close the loop after a game night.

Rating is the step people skip, so it costs exactly one tap and no typing. The event and
the game travel in the button, so the handler never has to ask "which game?".
"""

import logging

from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import ContextTypes

from app.core.callbacks import decode
from app.core.errors import DomainError
from app.domain.models import RatingCreate
from app.repositories import game_repository, person_repository
from app.services import rating_service
from bot.session import in_session

logger = logging.getLogger(__name__)

PATTERN = r"^rate:"
NOT_LINKED = "No reconozco tu cuenta. Vuelve a abrir tu enlace personal para vincularla."


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None or update.effective_user is None:
        return
    await query.answer()

    try:
        callback = decode(query.data)
    except ValueError as error:
        logger.warning("Discarding malformed callback_data: %s", error)
        return

    text = await in_session(
        lambda session: _record(
            session,
            update.effective_user.id,
            callback.event_id,
            callback.game_id,
            callback.score,
        )
    )
    # Replacing the message removes the buttons too, so a second tap cannot double-report.
    await query.edit_message_text(text)


def _record(
    session: Session, telegram_user_id: int, event_id: int, game_id: int, score: int
) -> str:
    person = person_repository.get_by_telegram_user_id(session, telegram_user_id)
    if person is None:
        return NOT_LINKED

    try:
        rating_service.record_rating(
            session, event_id, RatingCreate(person_id=person.id, game_id=game_id, score=score)
        )
    except DomainError as error:
        return f"No pude anotar tu nota: {error.message}"

    game = game_repository.get(session, game_id)
    name = game.name if game else "ese juego"
    return f"¡Anotado! {name}: {score}/5 ⭐"
