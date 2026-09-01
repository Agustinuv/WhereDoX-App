"""The /start handler, with Telegram and the database both faked.

What is worth testing here is the branching: a missing token, an unknown person and a
successful bind must each say something different. The bind itself is exercised for real
in tests/integration/test_telegram_bot.py.
"""

import pytest

from app.core.errors import NotFoundError
from bot.handlers import onboarding


class FakeMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


class FakeUpdate:
    def __init__(self, message, telegram_user_id: int | None) -> None:
        self.effective_message = message
        self.effective_user = _FakeUser(telegram_user_id) if telegram_user_id else None


class _FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


class FakeContext:
    def __init__(self, args: list[str]) -> None:
        self.args = args


@pytest.mark.parametrize("token", ["", "abc", "0", "-4", "3.a91f", " "])
def test_only_a_positive_integer_is_a_token(token):
    assert onboarding.parse_start_token(token) is None


def test_a_person_id_is_the_token():
    assert onboarding.parse_start_token("12") == 12
    assert onboarding.parse_start_token(" 12 ") == 12


async def run_start(monkeypatch, args, linker):
    monkeypatch.setattr(onboarding, "in_session", lambda work: linker())
    message = FakeMessage()
    await onboarding.start(FakeUpdate(message, 555), FakeContext(args))
    return message.replies


@pytest.mark.asyncio
async def test_an_unknown_account_with_no_token_is_asked_for_the_link(monkeypatch):
    async def unlinked():
        return None

    replies = await run_start(monkeypatch, [], unlinked)
    assert replies == [onboarding.NO_TOKEN]


@pytest.mark.asyncio
async def test_a_bare_start_from_a_linked_account_says_so_instead_of_sending_them_away(
    monkeypatch,
):
    async def linked():
        return "Agustín"

    replies = await run_start(monkeypatch, [], linked)
    assert "Agustín" in replies[0]
    assert "/junta" in replies[0]


@pytest.mark.asyncio
async def test_an_unknown_person_is_reported_rather_than_bound(monkeypatch):
    async def missing():
        raise NotFoundError("Person 99 does not exist.")

    replies = await run_start(monkeypatch, ["99"], missing)
    assert replies == [onboarding.UNKNOWN_PERSON]


@pytest.mark.asyncio
async def test_a_successful_bind_greets_the_person_by_name(monkeypatch):
    class Person:
        name = "Camila"

    async def found():
        return Person()

    replies = await run_start(monkeypatch, ["7"], found)
    assert "Camila" in replies[0]
