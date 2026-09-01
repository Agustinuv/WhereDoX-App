"""poll_answer — a native Telegram poll turned into availability votes.

Telegram reports an answer as a list of option *indices*, so the mapping recorded when the
poll was sent (telegram_polls.proposed_date_ids) is what gives those numbers meaning.

A selected option means "yes" and an unselected one means "no". The domain's third value,
"maybe", is unreachable from here: a native poll only knows checked and unchecked. That is
a deliberate trade — the poll is worth more than the half point, and "maybe" is still
available on the web client, which is where the tally's yes + 0.5 x maybe keeps mattering.
"""

import logging

from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import ContextTypes

from app.core.errors import ConflictError, DomainError
from app.domain.models import VoteCast
from app.repositories import person_repository, telegram_poll_repository
from app.services import voting_service
from bot.session import in_session

logger = logging.getLogger(__name__)


def _record_answer(
    session: Session, poll_id: str, telegram_user_id: int, selected: set[int]
) -> tuple[int, str] | None:
    """Returns the chat to answer in and what to say, or None when there is nothing to do."""
    poll = telegram_poll_repository.get_by_telegram_poll_id(session, poll_id)
    if poll is None:
        logger.warning("Poll %s is not one of ours; ignoring.", poll_id)
        return None

    person = person_repository.get_by_telegram_user_id(session, telegram_user_id)
    if person is None:
        logger.warning("Poll answer from an unlinked Telegram account; ignoring.")
        return None

    try:
        for index, proposed_date_id in enumerate(poll.proposed_date_ids):
            availability = "yes" if index in selected else "no"
            voting_service.cast_vote(
                session,
                poll.event_id,
                proposed_date_id,
                VoteCast(person_id=person.id, availability=availability),
            )
    except ConflictError as error:
        return poll.chat_id, f"No pude registrar tu respuesta: {error.message}"
    except DomainError as error:
        logger.warning("Rejected poll answer: %s", error.message)
        return poll.chat_id, "No pude registrar tu respuesta."

    available = len([index for index in selected if index < len(poll.proposed_date_ids)])
    if available == 0:
        return poll.chat_id, "Anotado: no te sirve ninguna de esas fechas. 🙏"
    return poll.chat_id, f"Anotado: puedes en {available} de las fechas propuestas. 🙌"


async def on_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    answer = update.poll_answer
    if answer is None or answer.user is None:
        return

    outcome = await in_session(
        lambda session: _record_answer(
            session, answer.poll_id, answer.user.id, set(answer.option_ids)
        )
    )
    if outcome is None:
        return

    chat_id, text = outcome
    await context.bot.send_message(chat_id=chat_id, text=text)
