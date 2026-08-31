"""The game catalogue and who owns which copy."""

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.domain.models import GameCreate
from app.domain.tables import Game
from app.repositories import game_repository, person_repository


def create_game(session: Session, payload: GameCreate) -> Game:
    if payload.max_players < payload.min_players:
        raise ValidationError("max_players cannot be smaller than min_players.")
    return game_repository.create(
        session,
        payload.name,
        payload.min_players,
        payload.max_players,
        payload.duration_minutes,
    )


def list_games(session: Session) -> list[Game]:
    return game_repository.list_all(session)


def add_to_library(session: Session, person_id: int, game_id: int) -> None:
    if person_repository.get(session, person_id) is None:
        raise NotFoundError(f"Person {person_id} does not exist.")
    if game_repository.get(session, game_id) is None:
        raise NotFoundError(f"Game {game_id} does not exist.")
    game_repository.add_to_library(session, person_id, game_id)
