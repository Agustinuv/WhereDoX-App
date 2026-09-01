"""Outbound ports: what the domain needs from the outside world, stated as interfaces.

The scheduler and the announcement service depend on NotificationPort, never on Telegram.
Swapping in WhatsApp means writing one more implementation and changing nothing else —
which is the same substitutability argument the rest of the layering makes.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class Button(BaseModel):
    """One tappable choice. `data` is echoed back verbatim when the reader taps it."""

    label: str
    data: str


# Buttons are laid out as rows: [[a], [b], [c]] stacks them, [[a, b, c]] puts them side
# by side. Five rating buttons only read as a scale when they share a row.
ButtonRows = list[list[Button]]


class NotificationPort(ABC):
    @abstractmethod
    def send_message(self, chat_id: int, text: str, buttons: ButtonRows | None = None) -> None: ...

    @abstractmethod
    def send_choice_poll(self, chat_id: int, question: str, options: list[str]) -> str | None:
        """Ask a multiple-choice question.

        Returns the channel's own id for the poll, needed to match answers back to it, or
        None when the channel cannot poll or the send failed.
        """


class LoggingNotifier(NotificationPort):
    """The original stub, kept as the default when no channel is configured.

    Without a bot token the project still runs end to end and the reminder job still
    reports what it *would* have sent, exactly as before the bot existed.
    """

    def __init__(self, logger) -> None:
        self._logger = logger

    def send_message(self, chat_id: int, text: str, buttons: ButtonRows | None = None) -> None:
        labels = [button.label for row in buttons or [] for button in row]
        self._logger.info("Would send to chat %s: %s %s", chat_id, text, labels or "")

    def send_choice_poll(self, chat_id: int, question: str, options: list[str]) -> str | None:
        self._logger.info("Would poll chat %s: %s %s", chat_id, question, options)
        return None
