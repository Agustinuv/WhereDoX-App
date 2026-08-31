"""Who hosts next.

The rule: whoever has gone longest without hosting *in this group*. Someone who has
never hosted always wins over someone who has, no matter how long ago. Ties are broken by
seniority in the group, which is the order the repository returns.

select_next_host is deliberately pure — it takes candidates and returns one, with no
database and no session. That is what makes the core decision of the product testable
in isolation, and it is the function worth showing in the presentation.
"""

from datetime import date

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.domain.models import NextHostOut
from app.repositories import group_repository


class RotationCandidate(BaseModel):
    person_id: int
    name: str
    last_hosted_at: date | None


class HostChoice(BaseModel):
    candidate: RotationCandidate
    reason: str


def select_next_host(candidates: list[RotationCandidate]) -> HostChoice:
    """Pick the next host from an ordered list of active members (most senior first)."""
    if not candidates:
        raise ConflictError("The group has no active members, so no host can be assigned.")

    never_hosted = [candidate for candidate in candidates if candidate.last_hosted_at is None]
    if never_hosted:
        # Candidates arrive most-senior-first, so [0] is the longest-standing never-host.
        chosen = never_hosted[0]
        return HostChoice(candidate=chosen, reason="has never hosted in this group")

    # Past this point no candidate has a null date. min() keeps the first on a tie,
    # which is again the most senior member.
    chosen = min(candidates, key=lambda candidate: candidate.last_hosted_at)
    return HostChoice(
        candidate=chosen,
        reason=f"last hosted on {chosen.last_hosted_at.isoformat()}, longest ago in the group",
    )


def load_candidates(session: Session, group_id: int) -> list[RotationCandidate]:
    if group_repository.get(session, group_id) is None:
        raise NotFoundError(f"Group {group_id} does not exist.")
    members = group_repository.list_members(session, group_id, active_only=True)
    return [
        RotationCandidate(
            person_id=member.person_id, name=person.name, last_hosted_at=member.last_hosted_at
        )
        for member, person in members
    ]


def peek_next_host(session: Session, group_id: int) -> NextHostOut:
    """Answer "whose turn is it?" without creating anything."""
    choice = select_next_host(load_candidates(session, group_id))
    return NextHostOut(
        person_id=choice.candidate.person_id,
        name=choice.candidate.name,
        last_hosted_at=choice.candidate.last_hosted_at,
        reason=choice.reason,
    )
