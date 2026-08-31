from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.domain.models import GameCreate, GameOut
from app.services import game_service

router = APIRouter(tags=["games"])


@router.post("/games", response_model=GameOut, status_code=status.HTTP_201_CREATED)
def create_game(payload: GameCreate, session: Session = Depends(get_session)) -> GameOut:
    return GameOut.model_validate(game_service.create_game(session, payload))


@router.get("/games", response_model=list[GameOut])
def list_games(session: Session = Depends(get_session)) -> list[GameOut]:
    return [GameOut.model_validate(game) for game in game_service.list_games(session)]


@router.post(
    "/people/{person_id}/library/{game_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Record that this person owns a copy of this game",
)
def add_to_library(person_id: int, game_id: int, session: Session = Depends(get_session)) -> None:
    game_service.add_to_library(session, person_id, game_id)
