"""The rotation rule, tested without a database.

Candidates always arrive most-senior-first, which is what the repository guarantees.
"""

from datetime import date

import pytest

from app.core.errors import ConflictError
from app.services.host_rotation_service import RotationCandidate, select_next_host


def candidate(person_id: int, name: str, last_hosted_at: date | None) -> RotationCandidate:
    return RotationCandidate(person_id=person_id, name=name, last_hosted_at=last_hosted_at)


def test_someone_who_never_hosted_beats_everyone_who_has():
    chosen = select_next_host(
        [
            candidate(1, "Camila", date(2020, 1, 1)),
            candidate(2, "Diego", None),
            candidate(3, "Fernanda", date(2019, 1, 1)),
        ]
    )
    assert chosen.candidate.name == "Diego"
    assert chosen.reason == "has never hosted in this group"


def test_the_most_senior_never_host_goes_first():
    chosen = select_next_host(
        [
            candidate(1, "Josefa", None),
            candidate(2, "Matias", None),
        ]
    )
    assert chosen.candidate.name == "Josefa"


def test_otherwise_the_longest_wait_wins():
    chosen = select_next_host(
        [
            candidate(1, "Camila", date(2024, 5, 1)),
            candidate(2, "Diego", date(2024, 1, 15)),
            candidate(3, "Fernanda", date(2024, 3, 1)),
        ]
    )
    assert chosen.candidate.name == "Diego"
    assert "2024-01-15" in chosen.reason


def test_a_tie_on_the_same_date_goes_to_the_most_senior():
    chosen = select_next_host(
        [
            candidate(1, "Camila", date(2024, 1, 1)),
            candidate(2, "Diego", date(2024, 1, 1)),
        ]
    )
    assert chosen.candidate.name == "Camila"


def test_a_group_with_no_active_members_cannot_pick_a_host():
    with pytest.raises(ConflictError):
        select_next_host([])


def test_rotation_advances_when_the_previous_host_is_marked():
    """Confirming an event sets last_hosted_at, which hands the turn to the next person."""
    roster = [
        candidate(1, "Camila", date(2024, 1, 1)),
        candidate(2, "Diego", date(2024, 2, 1)),
    ]
    assert select_next_host(roster).candidate.name == "Camila"

    roster[0] = candidate(1, "Camila", date(2024, 3, 1))
    assert select_next_host(roster).candidate.name == "Diego"
