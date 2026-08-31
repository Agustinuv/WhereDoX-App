"""The tally, tested without a database.

ORM objects are plain Python here: instantiating them needs no session.
"""

from datetime import UTC, datetime

from app.domain.tables import AvailabilityVote, ProposedDate
from app.services.voting_service import build_tally

FRIDAY = datetime(2026, 3, 6, 20, 0, tzinfo=UTC)
SATURDAY = datetime(2026, 3, 7, 20, 0, tzinfo=UTC)

VOTERS = {1: "Camila", 2: "Diego", 3: "Fernanda"}


def dates() -> list[ProposedDate]:
    return [
        ProposedDate(id=10, event_id=1, starts_at=FRIDAY),
        ProposedDate(id=11, event_id=1, starts_at=SATURDAY),
    ]


def vote(date_id: int, person_id: int, availability: str) -> AvailabilityVote:
    return AvailabilityVote(
        proposed_date_id=date_id, person_id=person_id, availability=availability
    )


def test_counts_and_score_per_date():
    tally = build_tally(
        1,
        "voting",
        dates(),
        [vote(10, 1, "yes"), vote(10, 2, "maybe"), vote(10, 3, "no")],
        VOTERS,
    )
    friday = tally.dates[0]
    assert (friday.yes, friday.maybe, friday.no) == (1, 1, 1)
    assert friday.score == 1.5


def test_a_maybe_is_worth_half_a_yes_and_breaks_a_tie():
    tally = build_tally(
        1,
        "voting",
        dates(),
        [
            vote(10, 1, "yes"),
            vote(10, 2, "maybe"),
            vote(11, 1, "yes"),
            vote(11, 2, "no"),
        ],
        VOTERS,
    )
    assert tally.leading_date_id == 10
    assert tally.is_tie is False


def test_people_who_have_not_voted_are_reported_per_date():
    tally = build_tally(1, "voting", dates(), [vote(10, 1, "yes")], VOTERS)
    assert tally.dates[0].missing_voters == ["Diego", "Fernanda"]
    assert tally.dates[1].missing_voters == ["Camila", "Diego", "Fernanda"]
    assert tally.eligible_voters == 3


def test_an_exact_tie_is_flagged_and_the_earliest_date_leads():
    tally = build_tally(
        1,
        "voting",
        dates(),
        [vote(10, 1, "yes"), vote(11, 2, "yes")],
        VOTERS,
    )
    assert tally.is_tie is True
    assert tally.leading_date_id == 10


def test_no_leader_when_nobody_is_available():
    tally = build_tally(
        1,
        "voting",
        dates(),
        [vote(10, 1, "no"), vote(11, 1, "no")],
        VOTERS,
    )
    assert tally.leading_date_id is None
    assert tally.is_tie is False


def test_votes_for_another_event_are_ignored():
    tally = build_tally(1, "voting", dates(), [vote(999, 1, "yes")], VOTERS)
    assert all(date.score == 0 for date in tally.dates)
