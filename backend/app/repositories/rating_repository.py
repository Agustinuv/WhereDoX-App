from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.tables import Event, Game, GamePlayed, Rating


def add_game_played(session: Session, event_id: int, game_id: int) -> GamePlayed:
    played = GamePlayed(event_id=event_id, game_id=game_id)
    session.add(played)
    session.flush()
    return played


def list_games_played(session: Session, event_id: int) -> list[tuple[GamePlayed, Game]]:
    stmt = (
        select(GamePlayed, Game)
        .join(Game, Game.id == GamePlayed.game_id)
        .where(GamePlayed.event_id == event_id)
        .order_by(GamePlayed.id)
    )
    return [(played, game) for played, game in session.execute(stmt)]


def upsert_rating(
    session: Session, event_id: int, game_id: int, person_id: int, score: int
) -> Rating:
    stmt = select(Rating).where(
        Rating.event_id == event_id,
        Rating.game_id == game_id,
        Rating.person_id == person_id,
    )
    rating = session.scalars(stmt).first()
    if rating is None:
        rating = Rating(event_id=event_id, game_id=game_id, person_id=person_id, score=score)
        session.add(rating)
    else:
        rating.score = score
    session.flush()
    return rating


def list_for_event(session: Session, event_id: int) -> list[tuple[Rating, Game]]:
    stmt = (
        select(Rating, Game)
        .join(Game, Game.id == Rating.game_id)
        .where(Rating.event_id == event_id)
    )
    return [(rating, game) for rating, game in session.execute(stmt)]


def list_played_game_ids_by_group(session: Session, group_id: int) -> list[int]:
    """Every game_id ever played in one group, one entry per play, for the novelty signal."""
    stmt = (
        select(GamePlayed.game_id)
        .join(Event, Event.id == GamePlayed.event_id)
        .where(Event.group_id == group_id)
    )
    return list(session.scalars(stmt))


def list_scores_by_group(session: Session, group_id: int) -> list[tuple[int, int]]:
    """(game_id, score) for every rating ever given inside one group.

    Feeds the recommender's taste signal; aggregation happens in the service.
    """
    stmt = (
        select(Rating.game_id, Rating.score)
        .join(Event, Event.id == Rating.event_id)
        .where(Event.group_id == group_id)
    )
    return [(game_id, score) for game_id, score in session.execute(stmt)]
