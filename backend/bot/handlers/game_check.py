"""The reminder's buttons: "lo tengo claro", "dame sugerencias", "recuérdame más tarde".

No conversational state is stored. Everything the handler needs travels inside the button
the reader tapped, so a bot restart mid-conversation loses nothing.
"""

import logging
from datetime import timedelta

from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import ContextTypes

from app.core.callbacks import decode
from app.core.config import get_settings
from app.core.errors import DomainError
from app.repositories import event_repository, person_repository
from app.services import announcement_service, recommender_service
from bot.session import in_session

logger = logging.getLogger(__name__)

PATTERN = r"^(clear|suggest|later):"
MAX_SUGGESTIONS = 3
MAX_REASONS = 2

ACKNOWLEDGED = "Perfecto, nos vemos ahí 🎲"
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

    if callback.kind == "clear":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(ACKNOWLEDGED)
        return

    if callback.kind == "suggest":
        text = await in_session(lambda session: _suggestions(session, callback.event_id))
        await query.message.reply_text(text)
        return

    await _snooze(update, context, callback.event_id)


def _suggestions(session: Session, event_id: int) -> str:
    event = event_repository.get(session, event_id)
    if event is None:
        return "Esa junta ya no existe."

    try:
        result = recommender_service.recommend(session, event_id, limit=MAX_SUGGESTIONS)
    except DomainError as error:
        return f"Todavía no puedo sugerir nada: {error.message}"

    if not result.recommendations:
        return (
            "No encontré ningún juego que calce: nadie de quienes van tiene uno que "
            f"sirva para {result.player_count} jugadores."
        )

    lines = [f"🎲 Para {event.title}, con {result.player_count} confirmados:", ""]
    for position, game in enumerate(result.recommendations, start=1):
        lines.append(f"{position}. {game.game_name}")
        lines.extend(f"   • {reason}" for reason in game.reasons[:MAX_REASONS])
    return "\n".join(lines)


async def _snooze(update: Update, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Re-send the same reminder later, through the same notification port.

    The job lives in the bot process's memory, so a restart forgets it. Persisting it means
    a job table and a decision about what a missed job should do on recovery — worth doing,
    not worth doing quietly.
    """
    minutes = get_settings().reminder_snooze_minutes
    person_id = await in_session(lambda session: _person_id_for(session, update.effective_user.id))
    if person_id is None:
        await update.callback_query.message.reply_text(NOT_LINKED)
        return

    if context.job_queue is None:
        logger.warning("No job queue available; cannot snooze the reminder.")
        await update.callback_query.message.reply_text(
            "No puedo reprogramarlo ahora, pero te va a llegar el recordatorio general."
        )
        return

    context.job_queue.run_once(
        _resend_reminder,
        when=timedelta(minutes=minutes),
        data={"event_id": event_id, "person_id": person_id},
        name=f"snooze:{event_id}:{person_id}",
    )
    unit = "minuto" if minutes == 1 else "minutos"
    await update.callback_query.message.reply_text(f"Dale, te lo recuerdo en {minutes} {unit} ⏳")


async def _resend_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data
    await in_session(lambda session: _remind_one(session, data["event_id"], data["person_id"]))


def _remind_one(session: Session, event_id: int, person_id: int) -> int:
    event = event_repository.get(session, event_id)
    person = person_repository.get(session, person_id)
    if event is None or person is None:
        return 0
    return announcement_service.remind(session, event, [person])


def _person_id_for(session: Session, telegram_user_id: int) -> int | None:
    person = person_repository.get_by_telegram_user_id(session, telegram_user_id)
    return person.id if person else None
