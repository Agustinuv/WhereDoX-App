"""Demo data.

Loads one group that already has rotation history, a played night with ratings, and a
live event mid-vote — so a demo never starts from an empty screen. The second group of
the demo (the interviewers') is created through the API, on the spot, not from here.

    python -m seed.seed_data --reset

For the live run-through, where the presenter drives one member from Telegram and the
others from the web:

    python -m seed.seed_data --reset --demo --telegram-user-id 123456789

`--demo` leaves no event open, so the rehearsal starts by creating one and the rotation
decision is the first thing on screen. `--telegram-user-id` re-binds the presenter's
account to the next host, which a plain --reset would otherwise destroy along with the
rest of `people`.
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
    "telegram_polls",
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
#
# Agustín is the only one who has never hosted, so the rotation picks him for one clear
# reason rather than on a seniority tiebreak. Martín is the longest ago of the rest, which
# makes him the visible next pick once Agustín's night is confirmed — so a single run shows
# both halves of the rule.
MEMBERS = [
    ("Agustín", None),
    ("Martín", 90),
    ("Vale", 60),
    ("Max", 30),
    ("Iñaki", 12),
]

GAMES = [
    ("7 Wonders", 3, 7, 40),
    ("Flip 7", 2, 8, 20),
    ("Fantasma Blitz", 2, 8, 20),
    ("Magic Maze", 1, 8, 15),
    ("Risk", 2, 6, 120),
    ("Código Secreto", 4, 8, 20),
    ("Truco", 2, 6, 30),
    ("Cachos", 2, 6, 30),
]


def reset(connection) -> None:
    connection.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))


# Whoever the rotation is about to pick. The presenter plays this member from Telegram,
# so the very first beat of the demo is the system choosing them out loud.
NEXT_HOST = "Agustín"


def seed(demo: bool = False, telegram_user_id: int | None = None) -> None:
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
        if not demo:
            _seed_live_event(session, group.id, people)

        if telegram_user_id is not None:
            person_repository.set_telegram_user_id(session, people[NEXT_HOST], telegram_user_id)

        session.commit()
        _report(group.id, people, demo, telegram_user_id)
    finally:
        session.close()


def _seed_libraries(session, people, games) -> None:
    """Who physically owns a copy — the recommender's hard filter, not a preference.

    Tuned for the three who attend in the live run (Agustín, Martín, Vale): between them
    they own the loved game, the disliked one, a few neutrals, and Código Secreto, which
    needs four players and is therefore excluded out loud. Duplicated titles are on
    purpose: two owners is realistic and the recommender names both.
    """
    ownership = {
        "Agustín": ["Código Secreto", "Cachos"],
        "Martín": ["7 Wonders", "Truco"],
        "Vale": ["Risk", "Flip 7"],
        "Max": ["Magic Maze", "Fantasma Blitz"],
        "Iñaki": ["Cachos", "7 Wonders"],
    }
    for owner, titles in ownership.items():
        for title in titles:
            game_repository.add_to_library(session, people[owner].id, games[title].id)


def _seed_past_event(session, group_id, people, games) -> None:
    """A finished night, so ratings and the summary endpoint have something to show."""
    host = people["Iñaki"]
    event = event_repository.create(session, group_id, host.id, "Junta de agosto")
    played_on = (now() - timedelta(days=12)).replace(hour=20, minute=0, second=0, microsecond=0)
    proposed = event_repository.add_proposed_dates(session, event.id, [played_on])[0]
    event_repository.confirm_date(session, event, proposed.id)
    event_repository.set_status(session, event, "completed")

    attendees = ["Iñaki", "Martín", "Vale", "Max"]
    attendance_repository.create_many(session, event.id, [people[n].id for n in attendees])
    for name in attendees:
        attendance_repository.set_status(session, event.id, people[name].id, "attended")

    # One loved, one disliked, and both still playable by a three-person table — otherwise
    # the taste signal is filtered out by the player-count rule before it can rank anything
    # and every candidate comes back neutral, which reads as a recommender that does not
    # work. Risk carries the negative signal because Vale owns it and she attends.
    scores = {"7 Wonders": [5, 5, 4, 5], "Risk": [2, 3, 2, 2]}
    for title, values in scores.items():
        rating_repository.add_game_played(session, event.id, games[title].id)
        for name, score in zip(attendees, values):
            rating_repository.upsert_rating(
                session, event.id, games[title].id, people[name].id, score
            )


def _seed_live_event(session, group_id, people) -> None:
    """An event mid-vote: the demo can open on a tally that already has signal."""
    host = people["Max"]
    event = event_repository.create(session, group_id, host.id, "Junta de septiembre")
    base = (now() + timedelta(days=7)).replace(hour=20, minute=0, second=0, microsecond=0)
    dates = event_repository.add_proposed_dates(
        session, event.id, [base, base + timedelta(days=1), base + timedelta(days=2)]
    )
    event_repository.set_status(session, event, "voting")

    # The first slot leads outright (3.5), the second trails (2.5) and the third is
    # unpopular. A clear leader matters: the demo confirms without naming a date, and a tie
    # would (correctly) be refused. Iñaki has not voted, so the tally also names someone
    # who still owes an answer.
    answers = {
        "Max": ["yes", "yes", "no"],
        "Agustín": ["yes", "maybe", "no"],
        "Martín": ["yes", "no", "maybe"],
        "Vale": ["maybe", "yes", "no"],
    }
    for name, availabilities in answers.items():
        for proposed, availability in zip(dates, availabilities):
            vote_repository.upsert(session, proposed.id, people[name].id, availability)


def _report(group_id: int, people: dict, demo: bool, telegram_user_id: int | None) -> None:
    print(f"Seeded group {group_id} with {len(people)} members.")
    print(f"Next host should be {NEXT_HOST} (the only member who has never hosted).")
    print(f"Try: GET /groups/{group_id}/next-host")

    if demo:
        print("\nDemo mode: no event is open, so the run starts by creating one.")
    if telegram_user_id is not None:
        host = people[NEXT_HOST]
        print(f"Telegram bound: {NEXT_HOST} (person {host.id}) -> account {telegram_user_id}.")
        print("The presenter plays that member; everyone else is driven from the web.")
    else:
        print("\nNobody is bound to Telegram. Pass --telegram-user-id to play a member there.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load WhereDoX demo data.")
    parser.add_argument("--reset", action="store_true", help="Truncate every table before seeding.")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Leave no event open, so a rehearsal starts on the rotation decision.",
    )
    parser.add_argument(
        "--telegram-user-id",
        type=int,
        default=None,
        help=f"Re-bind this Telegram account to {NEXT_HOST}, which --reset would wipe.",
    )
    args = parser.parse_args()

    if args.reset:
        with engine.begin() as connection:
            reset(connection)
        print("Tables truncated.")
    seed(demo=args.demo, telegram_user_id=args.telegram_user_id)


if __name__ == "__main__":
    main()
