"""/start <token> — binding a Telegram account to a person.

The token is the person_id, handed out as a link or a QR. Nothing is typed and nothing is
guessed from the account's display name, which is the whole point: a bot that asks "who
are you?" gets "Nacho" and has to map that to a row itself.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.core.errors import DomainError
from app.services import group_service
from bot.session import in_session

logger = logging.getLogger(__name__)

NO_TOKEN = (
    "Hola 👋 Para vincular tu cuenta necesito el enlace personal que te compartieron "
    "(o su código QR). Ábrelo y volvemos a empezar."
)
UNKNOWN_PERSON = "Ese enlace no corresponde a nadie en WhereDoX. Pide uno nuevo a quien organiza."


def parse_start_token(token: str) -> int | None:
    """The token is the person_id. Anything else is not a token — return None, never guess."""
    token = token.strip()
    if not token.isdigit():
        return None
    person_id = int(token)
    return person_id if person_id > 0 else None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    telegram_user = update.effective_user
    if message is None or telegram_user is None:
        return

    person_id = parse_start_token(context.args[0] if context.args else "")
    if person_id is None:
        await message.reply_text(NO_TOKEN)
        return

    try:
        person = await in_session(
            lambda session: group_service.link_telegram_account(
                session, person_id, telegram_user.id
            )
        )
    except DomainError:
        await message.reply_text(UNKNOWN_PERSON)
        return

    logger.info("Linked Telegram user to person %s", person_id)
    await message.reply_text(
        f"Listo, {person.name} 👋\n"
        "Desde acá te llegan las encuestas de fechas, los recordatorios y las "
        "valoraciones. No tienes que escribir nada: todo se responde con botones."
    )
