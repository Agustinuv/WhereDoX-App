"""Post-session input: what got played and what people thought of it.

This is the step with the most adoption friction in the real world, so the rules are as
permissive as they can be without letting nonsense in: any active member can log a game,
and anyone can rate a game that was actually played.
"""

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.domain.models import GamePlayedOut, RatingCreate
from app.domain.tables import Rating
from app.repositories import game_repository, rating_repository
from app.services import event_service


def _require_played_event(session: Session, event_id: int):
    event = event_service.require_event(session, event_id)
    if event.status not in ("confirmed", "completed"):
        raise ConflictError(
            f"Event {event_id} is {event.status}; nothing can be logged before a date is confirmed."
        )
    return event


def add_game_played(session: Session, event_id: int, game_id: int) -> GamePlayedOut:
    _require_played_event(session, event_id)
    game = game_repository.get(session, game_id)
    if game is None:
        raise NotFoundError(f"Game {game_id} does not exist.")

    played = rating_repository.add_game_played(session, event_id, game_id)
    return GamePlayedOut(id=played.id, game_id=game.id, game_name=game.name)


def list_games_played(session: Session, event_id: int) -> list[GamePlayedOut]:
    event_service.require_event(session, event_id)
    return [
        GamePlayedOut(id=played.id, game_id=game.id, game_name=game.name)
        for played, game in rating_repository.list_games_played(session, event_id)
    ]


def record_rating(session: Session, event_id: int, payload: RatingCreate) -> Rating:
    event = _require_played_event(session, event_id)
    event_service.require_active_member(session, event.group_id, payload.person_id)

    played_ids = {game.id for _, game in rating_repository.list_games_played(session, event_id)}
    if payload.game_id not in played_ids:
        raise ConflictError(
            f"Game {payload.game_id} was not played at event {event_id}, so it cannot be rated."
        )

    return rating_repository.upsert_rating(
        session, event_id, payload.game_id, payload.person_id, payload.score
    )
