"""The bot's two database-facing decisions: binding an account, and turning a poll answer
into votes the existing tally already knows how to rank.

Everything above these two points is Telegram's, and is verified by hand against the real
bot before a demo — the same line the project already draws around the REST API.
"""

import pytest

from app.repositories import telegram_poll_repository
from app.services import announcement_service, group_service
from app.services.ports import NotificationPort
from bot.handlers import status, voting
from tests.integration.test_events_api import FRIDAY, SATURDAY, build_group

pytestmark = pytest.mark.integration

CAMILA_TELEGRAM_ID = 555
DIEGO_TELEGRAM_ID = 666


class RecordingNotifier(NotificationPort):
    """A channel that keeps what it was asked to send instead of sending it."""

    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []
        self.polls: list[tuple[int, str, list[str]]] = []

    def send_message(self, chat_id, text, buttons=None) -> None:
        self.messages.append((chat_id, text))

    def send_choice_poll(self, chat_id, question, options) -> str:
        self.polls.append((chat_id, question, options))
        return f"poll-{len(self.polls)}"


@pytest.fixture
def notifier(monkeypatch) -> RecordingNotifier:
    recorder = RecordingNotifier()
    monkeypatch.setattr(announcement_service, "get_notifier", lambda: recorder)
    return recorder


def test_the_deep_link_is_the_person_id(client):
    person_id = client.post("/people", json={"name": "Camila"}).json()["id"]

    link = client.get(f"/people/{person_id}/telegram-link").json()

    assert link["url"].endswith(f"?start={person_id}")
    assert link["linked"] is False


def test_the_link_reports_an_account_that_is_already_bound(client, session):
    person_id = client.post("/people", json={"name": "Camila"}).json()["id"]
    group_service.link_telegram_account(session, person_id, CAMILA_TELEGRAM_ID)
    session.commit()

    assert client.get(f"/people/{person_id}/telegram-link").json()["linked"] is True


def test_unknown_person_has_no_link(client):
    assert client.get("/people/9999/telegram-link").status_code == 404


def test_scanning_someone_elses_link_moves_the_binding(client, session):
    """telegram_user_id is UNIQUE, so a re-scan has to release the old row, not fail.

    Re-scanning is how somebody fixes a mis-scan in front of a room, so it cannot 500.
    """
    camila = client.post("/people", json={"name": "Camila"}).json()["id"]
    diego = client.post("/people", json={"name": "Diego"}).json()["id"]

    group_service.link_telegram_account(session, camila, CAMILA_TELEGRAM_ID)
    session.commit()
    group_service.link_telegram_account(session, diego, CAMILA_TELEGRAM_ID)
    session.commit()

    assert client.get(f"/people/{camila}/telegram-link").json()["linked"] is False
    assert client.get(f"/people/{diego}/telegram-link").json()["linked"] is True


def open_vote_with_a_poll(client, session, telegram_id: int = CAMILA_TELEGRAM_ID):
    """A group mid-vote, with Camila linked and holding a poll for both dates.

    The commit after linking is load-bearing: this fixture and the TestClient run on two
    connections, and an uncommitted UPDATE on `people` makes the API's INSERT into `events`
    wait on the foreign key's lock over that same row.
    """
    group_id, people = build_group(client, ["Camila", "Diego"])
    group_service.link_telegram_account(session, people["Camila"], telegram_id)
    session.commit()

    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()
    dates = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": event["host_id"], "starts_at": [FRIDAY, SATURDAY]},
    ).json()

    telegram_poll_repository.record(
        session, "poll-1", event["id"], telegram_id, [date["id"] for date in dates]
    )
    session.commit()
    return event, dates, people


def test_a_selected_option_is_a_yes_and_an_unselected_one_is_a_no(client, session):
    event, dates, _ = open_vote_with_a_poll(client, session)

    outcome = voting._record_answer(session, "poll-1", CAMILA_TELEGRAM_ID, {0})
    session.commit()

    assert outcome is not None
    tally = client.get(f"/events/{event['id']}/tally").json()
    friday, saturday = tally["dates"]
    assert (friday["yes"], friday["no"]) == (1, 0)
    assert (saturday["yes"], saturday["no"]) == (0, 1)
    assert tally["leading_date_id"] == dates[0]["id"]


def test_picking_only_the_closing_option_records_a_no_on_every_date(client, session):
    """ "Ninguna me sirve" is index len(dates): past the mapping, so nothing is a yes."""
    event, dates, _ = open_vote_with_a_poll(client, session)

    _, text = voting._record_answer(session, "poll-1", CAMILA_TELEGRAM_ID, {len(dates)})
    session.commit()

    assert "no te sirve ninguna" in text
    tally = client.get(f"/events/{event['id']}/tally").json()
    assert [date["no"] for date in tally["dates"]] == [1, 1]
    assert tally["leading_date_id"] is None


def test_answering_again_replaces_the_earlier_answer(client, session):
    event, dates, _ = open_vote_with_a_poll(client, session)

    voting._record_answer(session, "poll-1", CAMILA_TELEGRAM_ID, {0})
    voting._record_answer(session, "poll-1", CAMILA_TELEGRAM_ID, {1})
    session.commit()

    votes = client.get(f"/events/{event['id']}/votes").json()
    assert len(votes) == 2
    assert {(vote["proposed_date_id"], vote["availability"]) for vote in votes} == {
        (dates[0]["id"], "no"),
        (dates[1]["id"], "yes"),
    }


def test_answering_after_the_host_confirmed_says_so_instead_of_crashing(client, session):
    event, dates, people = open_vote_with_a_poll(client, session)
    client.post(
        f"/events/{event['id']}/proposed-dates/{dates[0]['id']}/votes",
        json={"person_id": people["Camila"], "availability": "yes"},
    )
    client.post(f"/events/{event['id']}/confirm", json={"person_id": event["host_id"]})

    outcome = voting._record_answer(session, "poll-1", CAMILA_TELEGRAM_ID, {1})

    assert outcome is not None
    assert "No pude registrar tu respuesta" in outcome[1]


def test_proposing_dates_polls_only_the_members_who_linked_telegram(client, session, notifier):
    group_id, people = build_group(client, ["Camila", "Diego"])
    group_service.link_telegram_account(session, people["Camila"], CAMILA_TELEGRAM_ID)
    session.commit()

    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()
    client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": event["host_id"], "starts_at": [FRIDAY, SATURDAY]},
    )

    # Diego never linked an account, so he is simply unreachable — not an error.
    assert [chat_id for chat_id, _, _ in notifier.polls] == [CAMILA_TELEGRAM_ID]
    _, _, options = notifier.polls[0]
    assert len(options) == 3
    assert options[-1] == announcement_service.NO_SLOT_WORKS


def test_the_poll_that_was_sent_is_the_one_an_answer_resolves_against(client, session, notifier):
    group_id, people = build_group(client, ["Camila"])
    group_service.link_telegram_account(session, people["Camila"], CAMILA_TELEGRAM_ID)
    session.commit()

    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()
    dates = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": event["host_id"], "starts_at": [FRIDAY, SATURDAY]},
    ).json()

    recorded = telegram_poll_repository.get_by_telegram_poll_id(session, "poll-1")
    assert recorded is not None
    assert recorded.event_id == event["id"]
    assert recorded.proposed_date_ids == [date["id"] for date in dates]


def test_a_single_proposed_date_still_makes_a_valid_poll(client, session, notifier):
    """Telegram refuses a one-option poll, and one date is a legitimate proposal."""
    group_id, people = build_group(client, ["Camila"])
    group_service.link_telegram_account(session, people["Camila"], CAMILA_TELEGRAM_ID)
    session.commit()

    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()
    client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": event["host_id"], "starts_at": [FRIDAY]},
    )

    _, _, options = notifier.polls[0]
    assert len(options) == 2


def test_confirming_tells_the_group_which_date_won(client, session, notifier):
    group_id, people = build_group(client, ["Camila"])
    group_service.link_telegram_account(session, people["Camila"], CAMILA_TELEGRAM_ID)
    session.commit()

    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()
    dates = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": event["host_id"], "starts_at": [FRIDAY]},
    ).json()
    client.post(
        f"/events/{event['id']}/proposed-dates/{dates[0]['id']}/votes",
        json={"person_id": people["Camila"], "availability": "yes"},
    )
    # Creating the event already told Camila she is hosting; this test is about confirming.
    notifier.messages.clear()

    client.post(f"/events/{event['id']}/confirm", json={"person_id": event["host_id"]})

    assert len(notifier.messages) == 1
    chat_id, text = notifier.messages[0]
    assert chat_id == CAMILA_TELEGRAM_ID
    assert "Confirmado" in text


def close_a_night(client, session):
    """A completed event with one linked member, ready to be asked about."""
    group_id, people = build_group(client, ["Camila"])
    group_service.link_telegram_account(session, people["Camila"], CAMILA_TELEGRAM_ID)
    session.commit()

    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()
    dates = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": event["host_id"], "starts_at": [FRIDAY]},
    ).json()
    client.post(
        f"/events/{event['id']}/proposed-dates/{dates[0]['id']}/votes",
        json={"person_id": people["Camila"], "availability": "yes"},
    )
    client.post(f"/events/{event['id']}/confirm", json={"person_id": event["host_id"]})
    return event


def a_game(client, name: str = "Azul") -> int:
    return client.post("/games", json={"name": name, "min_players": 2, "max_players": 4}).json()[
        "id"
    ]


def test_closing_the_night_asks_about_every_game_already_logged(client, session, notifier):
    event = close_a_night(client, session)
    client.post(f"/events/{event['id']}/games-played", json={"game_id": a_game(client)})
    notifier.messages.clear()

    client.post(f"/events/{event['id']}/complete", params={"person_id": event["host_id"]})

    assert [text for _, text in notifier.messages] == [
        "¿Qué te pareció Azul? (1 = malo, 5 = excelente)"
    ]


def test_a_game_logged_after_closing_is_still_asked_about(client, session, notifier):
    """The ask fires on completion, so a game logged later would otherwise be skipped."""
    event = close_a_night(client, session)
    client.post(f"/events/{event['id']}/complete", params={"person_id": event["host_id"]})
    notifier.messages.clear()

    client.post(
        f"/events/{event['id']}/games-played", json={"game_id": a_game(client, "Codenames")}
    )

    assert len(notifier.messages) == 1
    assert "Codenames" in notifier.messages[0][1]


def test_only_the_late_game_is_asked_about_not_the_whole_night_again(client, session, notifier):
    event = close_a_night(client, session)
    client.post(f"/events/{event['id']}/games-played", json={"game_id": a_game(client)})
    client.post(f"/events/{event['id']}/complete", params={"person_id": event["host_id"]})
    notifier.messages.clear()

    client.post(
        f"/events/{event['id']}/games-played", json={"game_id": a_game(client, "Codenames")}
    )

    assert len(notifier.messages) == 1
    assert "Codenames" in notifier.messages[0][1]


def test_creating_an_event_tells_the_host_the_rotation_picked_them(client, session, notifier):
    group_id, people = build_group(client, ["Camila", "Diego"], last_hosted={"Diego": "2024-01-10"})
    group_service.link_telegram_account(session, people["Camila"], CAMILA_TELEGRAM_ID)
    session.commit()

    # Camila has never hosted, so the rotation picks her and only she hears about it.
    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()

    assert event["host_id"] == people["Camila"]
    assert [chat_id for chat_id, _ in notifier.messages] == [CAMILA_TELEGRAM_ID]
    assert "Te tocó ser anfitrión/a" in notifier.messages[0][1]


def test_a_host_without_telegram_is_simply_not_told(client, session, notifier):
    group_id, people = build_group(client, ["Camila"])
    client.post(f"/groups/{group_id}/events", json={"title": "Night"})
    assert notifier.messages == []


def test_junta_reports_the_vote_in_progress(client, session):
    event, dates, people = open_vote_with_a_poll(client, session)
    voting._record_answer(session, "poll-1", CAMILA_TELEGRAM_ID, {0})
    session.commit()

    text, buttons = status._load(session, CAMILA_TELEGRAM_ID)

    assert "votando" in text
    assert "Han votado 1 de 2" in text
    assert "Faltan: Diego" in text
    assert buttons == []


def test_junta_re_offers_the_suggestions_button_once_the_date_is_locked(client, session):
    event = close_a_night(client, session)

    text, buttons = status._load(session, CAMILA_TELEGRAM_ID)

    assert "confirmada" in text
    assert [button.label for row in buttons for button in row] == ["🎲 Dame sugerencias"]


def test_junta_re_offers_the_rating_scale_once_the_night_is_closed(client, session):
    event = close_a_night(client, session)
    client.post(f"/events/{event['id']}/games-played", json={"game_id": a_game(client)})
    client.post(f"/events/{event['id']}/complete", params={"person_id": event["host_id"]})

    text, buttons = status._load(session, CAMILA_TELEGRAM_ID)

    assert "cerrada" in text
    assert "Valora Azul" in text
    assert [button.label for button in buttons[0]] == ["1", "2", "3", "4", "5"]


def test_junta_prefers_the_night_still_being_organised_over_the_one_already_played(client, session):
    event = close_a_night(client, session)
    client.post(f"/events/{event['id']}/complete", params={"person_id": event["host_id"]})
    group_id = event["group_id"]

    # A brand new night with no dates yet is still the one the group cares about.
    fresh = client.post(f"/groups/{group_id}/events", json={"title": "La próxima"}).json()

    text, _ = status._load(session, CAMILA_TELEGRAM_ID)

    assert fresh["status"] == "draft"
    assert "La próxima" in text


def test_junta_from_an_unlinked_account_returns_nothing_to_show(client, session):
    open_vote_with_a_poll(client, session)
    assert status._load(session, DIEGO_TELEGRAM_ID) is None


def test_a_poll_we_never_sent_is_ignored(client, session):
    open_vote_with_a_poll(client, session)
    assert voting._record_answer(session, "someone-elses-poll", CAMILA_TELEGRAM_ID, {0}) is None


def test_an_answer_from_an_unlinked_account_is_ignored(client, session):
    open_vote_with_a_poll(client, session)
    assert voting._record_answer(session, "poll-1", DIEGO_TELEGRAM_ID, {0}) is None
