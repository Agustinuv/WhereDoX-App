"""The recommender's two rules, end to end: a hard filter and a ranking."""

from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.integration

NIGHT = (datetime.now(UTC) + timedelta(days=3)).replace(microsecond=0).isoformat()


def confirmed_event(client, member_names):
    """A group whose members all confirm one date, so an attendee list exists."""
    people = {}
    for name in member_names:
        people[name] = client.post("/people", json={"name": name}).json()["id"]

    group_id = client.post("/groups", json={"name": "Group"}).json()["id"]
    for person_id in people.values():
        client.post(f"/groups/{group_id}/members", json={"person_id": person_id})

    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()
    date_id = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": event["host_id"], "starts_at": [NIGHT]},
    ).json()[0]["id"]
    for person_id in people.values():
        client.post(
            f"/events/{event['id']}/proposed-dates/{date_id}/votes",
            json={"person_id": person_id, "availability": "yes"},
        )
    client.post(f"/events/{event['id']}/confirm", json={"person_id": event["host_id"]})
    return event["id"], group_id, people


def add_game(client, owner_id, name, min_players, max_players):
    game_id = client.post(
        "/games",
        json={"name": name, "min_players": min_players, "max_players": max_players},
    ).json()["id"]
    client.post(f"/people/{owner_id}/library/{game_id}")
    return game_id


def test_games_nobody_owns_are_never_recommended(client):
    event_id, _, people = confirmed_event(client, ["Camila", "Diego"])
    client.post("/games", json={"name": "Unowned", "min_players": 2, "max_players": 4})

    result = client.get(f"/events/{event_id}/recommendations").json()
    assert result["recommendations"] == []


def test_games_that_do_not_fit_the_head_count_are_excluded_with_a_reason(client):
    event_id, _, people = confirmed_event(client, ["Camila", "Diego"])
    add_game(client, people["Camila"], "Too big", 5, 8)
    add_game(client, people["Camila"], "Just right", 2, 4)

    result = client.get(f"/events/{event_id}/recommendations").json()
    assert result["player_count"] == 2
    assert [game["game_name"] for game in result["recommendations"]] == ["Just right"]
    assert "necesita 5-8 jugadores y hay 2 confirmados" in result["excluded"]["Too big"]


def test_a_game_the_group_loves_outranks_one_it_dislikes(client):
    event_id, _, people = confirmed_event(client, ["Camila", "Diego"])
    loved = add_game(client, people["Camila"], "Loved", 2, 4)
    disliked = add_game(client, people["Camila"], "Disliked", 2, 4)

    # Both were played once before, so novelty cancels out and only taste separates them.
    client.post(f"/events/{event_id}/games-played", json={"game_id": loved})
    client.post(f"/events/{event_id}/games-played", json={"game_id": disliked})
    client.post(
        f"/events/{event_id}/ratings",
        json={"person_id": people["Camila"], "game_id": loved, "score": 5},
    )
    client.post(
        f"/events/{event_id}/ratings",
        json={"person_id": people["Camila"], "game_id": disliked, "score": 1},
    )

    names = [
        game["game_name"]
        for game in client.get(f"/events/{event_id}/recommendations").json()["recommendations"]
    ]
    assert names == ["Loved", "Disliked"]


def test_recommendations_need_a_confirmed_date(client):
    people = {"Camila": client.post("/people", json={"name": "Camila"}).json()["id"]}
    group_id = client.post("/groups", json={"name": "Group"}).json()["id"]
    client.post(f"/groups/{group_id}/members", json={"person_id": people["Camila"]})
    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()

    response = client.get(f"/events/{event['id']}/recommendations")
    assert response.status_code == 409
