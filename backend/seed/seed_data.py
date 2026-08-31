"""Demo data.

Loads one group that already has rotation history, a played night with ratings, and a
live event mid-vote — so a demo never starts from an empty screen. The second group of
the demo (the interviewers') is created through the API, on the spot, not from here.

    python -m seed.seed_data --reset
"""

import argparse
from datetime import timedelta

from sqlalchemy import text

from app.core.clock import now
from app.core.database import SessionFactory, engine
from app.repositories import (
    attendance_repository,
    event_repository,
    game_repository,
    group_repository,
    person_repository,
    rating_repository,
    vote_repository,
)

TABLES = [
    "ratings",
    "games_played",
    "attendances",
    "availability_votes",
    "proposed_dates",
    "events",
    "game_libraries",
    "group_members",
    "groups",
    "games",
    "people",
]

# (name, days since they last hosted). None means they have never hosted, so they are
# next in the rotation regardless of everyone else's dates.
MEMBERS = [
    ("Camila", 90),
    ("Diego", 60),
    ("Fernanda", 30),
    ("Ignacio", 12),
    ("Josefa", None),
    ("Matías", None),
]

GAMES = [
    ("Catan", 3, 4, 90),
    ("Carcassonne", 2, 5, 45),
    ("Dixit", 3, 6, 30),
    ("Terraforming Mars", 1, 5, 120),
    ("Codenames", 4, 8, 20),
    ("Azul", 2, 4, 40),
    ("7 Wonders", 3, 7, 40),
    ("Pandemic", 2, 4, 60),
    ("Wingspan", 1, 5, 70),
    ("The Crew", 3, 5, 25),
]


def reset(connection) -> None:
    connection.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))


def seed() -> None:
    session = SessionFactory()
    try:
        group = group_repository.create(session, "Junta de Juegos")
        today = now().date()

        people = {}
        for name, days_ago in MEMBERS:
            person = person_repository.create(session, name, telegram_user_id=None)
            people[name] = person
            last_hosted = None if days_ago is None else today - timedelta(days=days_ago)
            group_repository.add_member(session, group.id, person.id, last_hosted)

        games = {
            name: game_repository.create(session, name, low, high, minutes)
            for name, low, high, minutes in GAMES
        }
        _seed_libraries(session, people, games)
        _seed_past_event(session, group.id, people, games)
        _seed_live_event(session, group.id, people)

        session.commit()
        _report(group.id, people)
    finally:
        session.close()


def _seed_libraries(session, people, games) -> None:
    """Spread ownership so the recommender has a real availability constraint."""
    ownership = {
        "Camila": ["Catan", "Azul"],
        "Diego": ["Carcassonne", "7 Wonders"],
        "Fernanda": ["Dixit", "Wingspan"],
        "Ignacio": ["Terraforming Mars", "Pandemic"],
        "Josefa": ["Codenames"],
        "Matías": ["The Crew", "Catan"],
    }
    for owner, titles in ownership.items():
        for title in titles:
            game_repository.add_to_library(session, people[owner].id, games[title].id)


def _seed_past_event(session, group_id, people, games) -> None:
    """A finished night, so ratings and the summary endpoint have something to show."""
    host = people["Ignacio"]
    event = event_repository.create(session, group_id, host.id, "Junta de noviembre")
    played_on = (now() - timedelta(days=12)).replace(hour=20, minute=0, second=0, microsecond=0)
    proposed = event_repository.add_proposed_dates(session, event.id, [played_on])[0]
    event_repository.confirm_date(session, event, proposed.id)
    event_repository.set_status(session, event, "completed")

    attendees = ["Ignacio", "Camila", "Diego", "Fernanda"]
    attendance_repository.create_many(session, event.id, [people[n].id for n in attendees])
    for name in attendees:
        attendance_repository.set_status(session, event.id, people[name].id, "attended")

    # Both titles also fit a five-player night, so the taste signal they produce is still
    # live for the next event instead of being filtered out by the player-count rule.
    # One is loved and one is not, which is what makes the recommender's ranking visible.
    scores = {"7 Wonders": [5, 5, 4, 5], "Codenames": [2, 3, 2, 2]}
    for title, values in scores.items():
        rating_repository.add_game_played(session, event.id, games[title].id)
        for name, score in zip(attendees, values):
            rating_repository.upsert_rating(
                session, event.id, games[title].id, people[name].id, score
            )


def _seed_live_event(session, group_id, people) -> None:
    """An event mid-vote: the demo can open on a tally that already has signal."""
    host = people["Fernanda"]
    event = event_repository.create(session, group_id, host.id, "Junta de diciembre")
    base = (now() + timedelta(days=7)).replace(hour=20, minute=0, second=0, microsecond=0)
    dates = event_repository.add_proposed_dates(
        session, event.id, [base, base + timedelta(days=1), base + timedelta(days=2)]
    )
    event_repository.set_status(session, event, "voting")

    # The first slot leads outright (4.0), the second is close behind (3.5) and the third
    # is unpopular. A clear leader matters: the demo confirms without naming a date, and
    # a tie would (correctly) be refused. Matías has not voted, so the tally also shows a
    # pending voter.
    answers = {
        "Fernanda": ["yes", "yes", "no"],
        "Camila": ["yes", "maybe", "no"],
        "Diego": ["yes", "no", "maybe"],
        "Ignacio": ["maybe", "yes", "no"],
        "Josefa": ["maybe", "yes", "yes"],
    }
    for name, availabilities in answers.items():
        for proposed, availability in zip(dates, availabilities):
            vote_repository.upsert(session, proposed.id, people[name].id, availability)


def _report(group_id: int, people: dict) -> None:
    print(f"Seeded group {group_id} with {len(people)} members.")
    print("Next host should be Josefa (never hosted, longest-standing of the two).")
    print(f"Try: GET /groups/{group_id}/next-host")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load WhereDoX demo data.")
    parser.add_argument("--reset", action="store_true", help="Truncate every table before seeding.")
    args = parser.parse_args()

    if args.reset:
        with engine.begin() as connection:
            reset(connection)
        print("Tables truncated.")
    seed()


if __name__ == "__main__":
    main()
