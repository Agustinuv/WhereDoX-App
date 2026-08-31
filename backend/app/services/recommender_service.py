"""Which game should this group play tonight.

A transparent heuristic, not a model: three signals, fixed weights, and every result
carries the reasons that produced it. The point is a decision the group can argue with —
an opaque score would be worse product even if it ranked better.

Hard filter (a game is excluded outright):
  * nobody attending owns a copy
  * the confirmed head count falls outside the game's player range

Ranking among the survivors:
  * taste   - the group's own average rating, 3/5 when they have never rated it
  * novelty - decays with how often this group has already played it
"""

from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.constants import MAX_RATING, NEUTRAL_RATING, NOVELTY_WEIGHT, TASTE_WEIGHT
from app.core.errors import ConflictError
from app.domain.models import GameRecommendation, RecommendationOut
from app.repositories import attendance_repository, game_repository, rating_repository
from app.services import event_service


def recommend(session: Session, event_id: int, limit: int = 5) -> RecommendationOut:
    event = event_service.require_event(session, event_id)
    if event.confirmed_date_id is None:
        raise ConflictError(
            f"Event {event_id} has no confirmed date, so there is no attendee list to plan for."
        )

    attendees = [
        (attendance, person)
        for attendance, person in attendance_repository.list_for_event(session, event_id)
        if attendance.status in ("expected", "attended")
    ]
    player_count = len(attendees)
    owner_names = {person.id: person.name for _, person in attendees}

    owned = game_repository.list_owned_by(session, list(owner_names))
    owners_by_game: dict[int, list[str]] = defaultdict(list)
    games = {}
    for person_id, game in owned:
        owners_by_game[game.id].append(owner_names[person_id])
        games[game.id] = game

    averages = _average_scores(rating_repository.list_scores_by_group(session, event.group_id))
    play_counts = _play_counts(
        rating_repository.list_played_game_ids_by_group(session, event.group_id)
    )

    ranked: list[GameRecommendation] = []
    excluded: dict[str, str] = {}
    for game_id, game in games.items():
        if not game.min_players <= player_count <= game.max_players:
            excluded[game.name] = (
                f"necesita {game.min_players}-{game.max_players} jugadores "
                f"y hay {player_count} confirmados"
            )
            continue
        ranked.append(
            _score(game, sorted(set(owners_by_game[game_id])), averages, play_counts, player_count)
        )

    ranked.sort(key=lambda item: (-item.score, item.game_name))
    return RecommendationOut(
        event_id=event_id,
        player_count=player_count,
        recommendations=ranked[:limit],
        excluded=excluded,
    )


def _score(game, owners, averages, play_counts, player_count) -> GameRecommendation:
    average = averages.get(game.id)
    times_played = play_counts.get(game.id, 0)

    taste = (average if average is not None else NEUTRAL_RATING) / MAX_RATING
    novelty = 1 / (1 + times_played)
    score = TASTE_WEIGHT * taste + NOVELTY_WEIGHT * novelty

    # Product copy shown to end users (in the UI and in Swagger), not log or error text,
    # so it follows the product's language instead of the codebase's English.
    reasons = [
        (
            f"promedio {average} de 5 en este grupo"
            if average is not None
            else "nunca lo han valorado acá, cuenta como neutro"
        ),
        (
            "nunca lo han jugado acá"
            if times_played == 0
            else f"ya lo jugaron {times_played} {'vez' if times_played == 1 else 'veces'}"
        ),
        f"sirve para {player_count} jugadores (admite {game.min_players}-{game.max_players})",
        f"lo puede traer {', '.join(owners)}",
    ]
    return GameRecommendation(
        game_id=game.id,
        game_name=game.name,
        score=round(score, 3),
        owners=owners,
        reasons=reasons,
    )


def _average_scores(scores: list[tuple[int, int]]) -> dict[int, float]:
    grouped: dict[int, list[int]] = defaultdict(list)
    for game_id, score in scores:
        grouped[game_id].append(score)
    return {game_id: round(sum(v) / len(v), 2) for game_id, v in grouped.items()}


def _play_counts(game_ids: list[int]) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    for game_id in game_ids:
        counts[game_id] += 1
    return counts
