"""Availability voting and the tally that ranks the proposed slots.

build_tally is a pure function: it takes rows and returns a result, touching no session.
That is what lets the ranking rule — including how ties and non-voters are treated — be
unit tested without a database.
"""

from sqlalchemy.orm import Session

from app.core.constants import MAYBE_WEIGHT
from app.core.errors import ConflictError, NotFoundError
from app.domain.models import DateTally, EventTally, VoteCast, VoteOut
from app.domain.tables import AvailabilityVote, ProposedDate
from app.repositories import event_repository, group_repository, vote_repository
from app.services import event_service


def build_tally(
    event_id: int,
    status: str,
    dates: list[ProposedDate],
    votes: list[AvailabilityVote],
    voter_names: dict[int, str],
) -> EventTally:
    votes_by_date: dict[int, list[AvailabilityVote]] = {date.id: [] for date in dates}
    for vote in votes:
        if vote.proposed_date_id in votes_by_date:
            votes_by_date[vote.proposed_date_id].append(vote)

    tallies: list[DateTally] = []
    for proposed in dates:
        date_votes = votes_by_date[proposed.id]
        counts = {"yes": 0, "maybe": 0, "no": 0}
        for vote in date_votes:
            counts[vote.availability] += 1

        voted_ids = {vote.person_id for vote in date_votes}
        tallies.append(
            DateTally(
                proposed_date_id=proposed.id,
                starts_at=proposed.starts_at,
                yes=counts["yes"],
                maybe=counts["maybe"],
                no=counts["no"],
                score=counts["yes"] + MAYBE_WEIGHT * counts["maybe"],
                missing_voters=sorted(
                    name for person_id, name in voter_names.items() if person_id not in voted_ids
                ),
            )
        )

    leading_date_id, is_tie = _rank(tallies)
    return EventTally(
        event_id=event_id,
        status=status,
        eligible_voters=len(voter_names),
        dates=tallies,
        leading_date_id=leading_date_id,
        is_tie=is_tie,
    )


def _rank(tallies: list[DateTally]) -> tuple[int | None, bool]:
    """Best slot by score; earliest date wins a tie, but the tie is still reported.

    Auto-resolving silently would hide a real disagreement from the host, so the flag is
    surfaced and the API refuses to auto-confirm on a tie.
    """
    scored = [tally for tally in tallies if tally.score > 0]
    if not scored:
        return None, False

    best_score = max(tally.score for tally in scored)
    winners = [tally for tally in scored if tally.score == best_score]
    winners.sort(key=lambda tally: tally.starts_at)
    return winners[0].proposed_date_id, len(winners) > 1


def cast_vote(session: Session, event_id: int, proposed_date_id: int, payload: VoteCast) -> None:
    event = event_service.require_event(session, event_id)
    if event.status != "voting":
        raise ConflictError(f"Event {event_id} is {event.status}; voting is closed.")

    proposed = event_repository.get_proposed_date(session, proposed_date_id)
    if proposed is None or proposed.event_id != event_id:
        raise NotFoundError(
            f"Proposed date {proposed_date_id} does not belong to event {event_id}."
        )

    event_service.require_active_member(session, event.group_id, payload.person_id)
    vote_repository.upsert(session, proposed_date_id, payload.person_id, payload.availability)


def list_votes(session: Session, event_id: int) -> list[VoteOut]:
    """Who answered what, in the order they answered — the raw material for a timeline."""
    event_service.require_event(session, event_id)
    return [
        VoteOut(
            person_id=vote.person_id,
            person_name=person.name,
            proposed_date_id=vote.proposed_date_id,
            availability=vote.availability,
            voted_at=vote.voted_at,
        )
        for vote, person in vote_repository.list_for_event_with_people(session, event_id)
    ]


def get_tally(session: Session, event_id: int) -> EventTally:
    event = event_service.require_event(session, event_id)
    dates = event_repository.list_proposed_dates(session, event_id)
    votes = vote_repository.list_for_event(session, event_id)
    voter_names = {
        member.person_id: person.name
        for member, person in group_repository.list_members(
            session, event.group_id, active_only=True
        )
    }
    return build_tally(event_id, event.status, dates, votes, voter_names)
