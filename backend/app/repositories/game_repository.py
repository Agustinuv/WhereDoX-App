from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.tables import Game, GameLibrary


def create(
    session: Session, name: str, min_players: int, max_players: int, duration_minutes: int | None
) -> Game:
    game = Game(
        name=name,
        min_players=min_players,
        max_players=max_players,
        duration_minutes=duration_minutes,
    )
    session.add(game)
    session.flush()
    return game


def get(session: Session, game_id: int) -> Game | None:
    return session.get(Game, game_id)


def list_all(session: Session) -> list[Game]:
    return list(session.scalars(select(Game).order_by(Game.name)))


def add_to_library(session: Session, person_id: int, game_id: int) -> GameLibrary:
    entry = GameLibrary(person_id=person_id, game_id=game_id)
    session.add(entry)
    session.flush()
    return entry


def list_owned_by(session: Session, person_ids: list[int]) -> list[tuple[int, Game]]:
    """(owner_id, game) for a set of people — which games could physically be on the table."""
    if not person_ids:
        return []
    stmt = (
        select(GameLibrary.person_id, Game)
        .join(Game, Game.id == GameLibrary.game_id)
        .where(GameLibrary.person_id.in_(person_ids))
    )
    return [(person_id, game) for person_id, game in session.execute(stmt)]
