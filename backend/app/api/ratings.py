from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.domain.models import (
    GamePlayedAdd,
    GamePlayedOut,
    RatingCreate,
    RatingOut,
    RecommendationOut,
)
from app.services import rating_service, recommender_service

router = APIRouter(tags=["post-session"])


@router.get(
    "/events/{event_id}/recommendations",
    response_model=RecommendationOut,
    summary="What should we play, given who is coming and what they own",
)
def recommend_games(
    event_id: int, limit: int = 5, session: Session = Depends(get_session)
) -> RecommendationOut:
    return recommender_service.recommend(session, event_id, limit)


@router.post(
    "/events/{event_id}/games-played",
    response_model=GamePlayedOut,
    status_code=status.HTTP_201_CREATED,
    summary="Log a game that made it to the table",
)
def add_game_played(
    event_id: int, payload: GamePlayedAdd, session: Session = Depends(get_session)
) -> GamePlayedOut:
    return rating_service.add_game_played(session, event_id, payload.game_id)


@router.get("/events/{event_id}/games-played", response_model=list[GamePlayedOut])
def list_games_played(
    event_id: int, session: Session = Depends(get_session)
) -> list[GamePlayedOut]:
    return rating_service.list_games_played(session, event_id)


@router.post(
    "/events/{event_id}/ratings",
    response_model=RatingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Rate a game played that night (1-5)",
)
def record_rating(
    event_id: int, payload: RatingCreate, session: Session = Depends(get_session)
) -> RatingOut:
    return RatingOut.model_validate(rating_service.record_rating(session, event_id, payload))
