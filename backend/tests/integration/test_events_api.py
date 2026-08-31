"""End-to-end coordination flow against a real database.

One happy path covering the whole product loop, plus the refusals that protect it.
"""

from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.integration

FRIDAY = (datetime.now(UTC) + timedelta(days=7)).replace(microsecond=0).isoformat()
SATURDAY = (datetime.now(UTC) + timedelta(days=8)).replace(microsecond=0).isoformat()


def build_group(client, names, last_hosted=None):
    last_hosted = last_hosted or {}
    people = {}
    for name in names:
        response = client.post("/people", json={"name": name})
        assert response.status_code == 201
        people[name] = response.json()["id"]

    group_id = client.post("/groups", json={"name": "Test group"}).json()["id"]
    for name in names:
        payload = {"person_id": people[name], "last_hosted_at": last_hosted.get(name)}
        assert client.post(f"/groups/{group_id}/members", json=payload).status_code == 201
    return group_id, people


def test_health_reaches_the_database(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "reachable"


def test_full_coordination_loop(client):
    group_id, people = build_group(
        client,
        ["Camila", "Diego", "Fernanda"],
        last_hosted={"Camila": "2024-01-10", "Diego": "2024-02-10"},
    )

    # Fernanda has never hosted, so the rotation picks her over both others.
    next_host = client.get(f"/groups/{group_id}/next-host").json()
    assert next_host["person_id"] == people["Fernanda"]

    event = client.post(f"/groups/{group_id}/events", json={"title": "March night"}).json()
    assert event["host_id"] == people["Fernanda"]
    assert event["status"] == "draft"
    event_id = event["id"]

    dates = client.post(
        f"/events/{event_id}/proposed-dates",
        json={"person_id": people["Fernanda"], "starts_at": [FRIDAY, SATURDAY]},
    )
    assert dates.status_code == 201
    friday_id, saturday_id = [date["id"] for date in dates.json()]

    assert client.get(f"/events/{event_id}").json()["status"] == "voting"

    for person, availability in [("Camila", "yes"), ("Diego", "yes"), ("Fernanda", "yes")]:
        response = client.post(
            f"/events/{event_id}/proposed-dates/{friday_id}/votes",
            json={"person_id": people[person], "availability": availability},
        )
        assert response.status_code == 204
    client.post(
        f"/events/{event_id}/proposed-dates/{saturday_id}/votes",
        json={"person_id": people["Camila"], "availability": "maybe"},
    )

    tally = client.get(f"/events/{event_id}/tally").json()
    assert tally["leading_date_id"] == friday_id
    assert tally["is_tie"] is False
    assert tally["dates"][0]["score"] == 3.0

    # No proposed_date_id: the host accepts the leading date.
    confirmed = client.post(f"/events/{event_id}/confirm", json={"person_id": people["Fernanda"]})
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["confirmed_date_id"] == friday_id

    attendance = client.get(f"/events/{event_id}/attendance").json()
    assert {row["name"] for row in attendance} == {"Camila", "Diego", "Fernanda"}
    assert all(row["status"] == "expected" for row in attendance)

    client.put(
        f"/events/{event_id}/attendance",
        json={"person_id": people["Diego"], "status": "absent"},
    )

    assert (
        client.post(
            f"/events/{event_id}/complete", params={"person_id": people["Fernanda"]}
        ).status_code
        == 200
    )

    game_id = client.post(
        "/games", json={"name": "Azul", "min_players": 2, "max_players": 4}
    ).json()["id"]
    assert (
        client.post(f"/events/{event_id}/games-played", json={"game_id": game_id}).status_code
        == 201
    )
    assert (
        client.post(
            f"/events/{event_id}/ratings",
            json={"person_id": people["Camila"], "game_id": game_id, "score": 5},
        ).status_code
        == 201
    )

    summary = client.get(f"/events/{event_id}/summary").json()
    assert summary["host_name"] == "Fernanda"
    assert summary["event"]["status"] == "completed"
    assert summary["ratings"] == [
        {"game_id": game_id, "game_name": "Azul", "average_score": 5.0, "votes": 1}
    ]

    # Hosting advanced the rotation: Fernanda is no longer next, Camila is.
    assert client.get(f"/groups/{group_id}/next-host").json()["person_id"] == people["Camila"]


def test_only_the_host_can_propose_dates(client):
    group_id, people = build_group(client, ["Camila", "Diego"])
    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()

    intruder = people["Diego"] if event["host_id"] != people["Diego"] else people["Camila"]
    response = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": intruder, "starts_at": [FRIDAY]},
    )
    assert response.status_code == 409


def test_a_non_member_cannot_vote(client):
    group_id, people = build_group(client, ["Camila"])
    outsider = client.post("/people", json={"name": "Outsider"}).json()["id"]
    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()
    date_id = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": event["host_id"], "starts_at": [FRIDAY]},
    ).json()[0]["id"]

    response = client.post(
        f"/events/{event['id']}/proposed-dates/{date_id}/votes",
        json={"person_id": outsider, "availability": "yes"},
    )
    assert response.status_code == 409


def test_confirming_a_tie_without_naming_a_date_is_refused(client):
    group_id, people = build_group(client, ["Camila", "Diego"])
    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()
    host = event["host_id"]
    dates = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": host, "starts_at": [FRIDAY, SATURDAY]},
    ).json()

    for date, person in zip(dates, [people["Camila"], people["Diego"]]):
        client.post(
            f"/events/{event['id']}/proposed-dates/{date['id']}/votes",
            json={"person_id": person, "availability": "yes"},
        )

    assert client.get(f"/events/{event['id']}/tally").json()["is_tie"] is True

    refused = client.post(f"/events/{event['id']}/confirm", json={"person_id": host})
    assert refused.status_code == 409
    assert "tied" in refused.json()["detail"]

    # Naming the date explicitly resolves it.
    accepted = client.post(
        f"/events/{event['id']}/confirm",
        json={"person_id": host, "proposed_date_id": dates[1]["id"]},
    )
    assert accepted.status_code == 200


def test_voting_closes_once_the_date_is_confirmed(client):
    group_id, people = build_group(client, ["Camila", "Diego"])
    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()
    date_id = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": event["host_id"], "starts_at": [FRIDAY]},
    ).json()[0]["id"]
    client.post(
        f"/events/{event['id']}/proposed-dates/{date_id}/votes",
        json={"person_id": people["Camila"], "availability": "yes"},
    )
    client.post(f"/events/{event['id']}/confirm", json={"person_id": event["host_id"]})

    late = client.post(
        f"/events/{event['id']}/proposed-dates/{date_id}/votes",
        json={"person_id": people["Diego"], "availability": "yes"},
    )
    assert late.status_code == 409


def test_individual_votes_are_listed_with_names(client):
    """The tally gives totals; this endpoint backs the per-person view in the chat UI."""
    group_id, people = build_group(client, ["Camila", "Diego"])
    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()
    dates = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": event["host_id"], "starts_at": [FRIDAY, SATURDAY]},
    ).json()

    client.post(
        f"/events/{event['id']}/proposed-dates/{dates[0]['id']}/votes",
        json={"person_id": people["Camila"], "availability": "yes"},
    )
    client.post(
        f"/events/{event['id']}/proposed-dates/{dates[1]['id']}/votes",
        json={"person_id": people["Camila"], "availability": "maybe"},
    )

    votes = client.get(f"/events/{event['id']}/votes").json()
    assert [(v["person_name"], v["proposed_date_id"], v["availability"]) for v in votes] == [
        ("Camila", dates[0]["id"], "yes"),
        ("Camila", dates[1]["id"], "maybe"),
    ]


def test_changing_a_vote_replaces_it_instead_of_adding_one(client):
    group_id, people = build_group(client, ["Camila", "Diego"])
    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()
    date_id = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": event["host_id"], "starts_at": [FRIDAY]},
    ).json()[0]["id"]

    for availability in ("yes", "no"):
        client.post(
            f"/events/{event['id']}/proposed-dates/{date_id}/votes",
            json={"person_id": people["Camila"], "availability": availability},
        )

    votes = client.get(f"/events/{event['id']}/votes").json()
    assert len(votes) == 1
    assert votes[0]["availability"] == "no"


def test_proposed_dates_are_capped_across_requests(client):
    """The per-request schema limit is not enough: the cap belongs to the event."""
    group_id, people = build_group(client, ["Camila"])
    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()
    host = event["host_id"]
    base = datetime.now(UTC) + timedelta(days=30)
    slots = [
        (base + timedelta(days=offset)).replace(microsecond=0).isoformat() for offset in range(6)
    ]

    # Six in one request is refused by the schema itself.
    too_many = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": host, "starts_at": slots},
    )
    assert too_many.status_code == 422

    first = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": host, "starts_at": slots[:4]},
    )
    assert first.status_code == 201

    # Four already there plus two more would be six, so the service refuses.
    overflow = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": host, "starts_at": slots[4:6]},
    )
    assert overflow.status_code == 422
    assert "at most 5" in overflow.json()["detail"]

    # One more fits exactly.
    assert (
        client.post(
            f"/events/{event['id']}/proposed-dates",
            json={"person_id": host, "starts_at": [slots[4]]},
        ).status_code
        == 201
    )
    assert len(client.get(f"/events/{event['id']}/proposed-dates").json()) == 5


def test_a_single_proposed_date_is_allowed(client):
    group_id, _ = build_group(client, ["Camila"])
    event = client.post(f"/groups/{group_id}/events", json={"title": "Night"}).json()
    response = client.post(
        f"/events/{event['id']}/proposed-dates",
        json={"person_id": event["host_id"], "starts_at": [FRIDAY]},
    )
    assert response.status_code == 201
    assert len(response.json()) == 1


def test_a_person_only_sees_the_groups_they_belong_to(client):
    group_id, people = build_group(client, ["Camila", "Diego"])
    other_id = client.post("/groups", json={"name": "Otro grupo"}).json()["id"]
    client.post(f"/groups/{other_id}/members", json={"person_id": people["Diego"]})

    camila_groups = client.get(f"/people/{people['Camila']}/groups").json()
    diego_groups = client.get(f"/people/{people['Diego']}/groups").json()

    assert [group["id"] for group in camila_groups] == [group_id]
    assert sorted(group["id"] for group in diego_groups) == sorted([group_id, other_id])


def test_unknown_event_returns_404(client):
    assert client.get("/events/9999").status_code == 404
