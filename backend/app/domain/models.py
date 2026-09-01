"""Request and response schemas.

Every endpoint that acts on behalf of someone takes an explicit person_id: the prototype
has no authentication, so the caller states who they are. A Telegram bot would resolve
this from telegram_user_id instead, and nothing below the API layer would change.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import MAX_PROPOSED_DATES, MAX_RATING, MIN_RATING

Availability = Literal["yes", "maybe", "no"]
EventStatus = Literal["draft", "voting", "confirmed", "completed", "cancelled"]
AttendanceStatus = Literal["expected", "attended", "absent"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- people and groups -------------------------------------------------------------


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    telegram_user_id: int | None = None


class PersonOut(ORMModel):
    id: int
    name: str
    telegram_user_id: int | None


class TelegramLinkOut(BaseModel):
    person_id: int
    name: str
    url: str = Field(description="Deep link that binds the scanner's Telegram account.")
    linked: bool = Field(description="Whether this person has already bound an account.")


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class GroupOut(ORMModel):
    id: int
    name: str


class MemberAdd(BaseModel):
    person_id: int
    last_hosted_at: date | None = Field(
        default=None,
        description="Seed a rotation history for this member. Leave null for a new member, "
        "who then takes priority as next host.",
    )


class MemberOut(BaseModel):
    person_id: int
    name: str
    is_active: bool
    last_hosted_at: date | None


# --- games -------------------------------------------------------------------------


class GameCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    min_players: int = Field(ge=1, le=99)
    max_players: int = Field(ge=1, le=99)
    duration_minutes: int | None = Field(default=None, ge=1)


class GameOut(ORMModel):
    id: int
    name: str
    min_players: int
    max_players: int
    duration_minutes: int | None


# --- events ------------------------------------------------------------------------


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=140)
    host_id: int | None = Field(
        default=None,
        description="Override the rotation. Leave null to let the system pick the next host.",
    )


class EventOut(ORMModel):
    id: int
    group_id: int
    host_id: int
    title: str
    status: EventStatus
    confirmed_date_id: int | None


class NextHostOut(BaseModel):
    person_id: int
    name: str
    last_hosted_at: date | None
    reason: str


class DatesPropose(BaseModel):
    person_id: int = Field(description="Must be the event host.")
    starts_at: list[datetime] = Field(
        min_length=1,
        max_length=MAX_PROPOSED_DATES,
        description=f"Between 1 and {MAX_PROPOSED_DATES} slots. The limit applies to the "
        "event as a whole, so a second call cannot push the total past it.",
    )


class ProposedDateOut(ORMModel):
    id: int
    event_id: int
    starts_at: datetime


# --- voting ------------------------------------------------------------------------


class VoteCast(BaseModel):
    person_id: int
    availability: Availability


class VoteOut(BaseModel):
    person_id: int
    person_name: str
    proposed_date_id: int
    availability: Availability
    voted_at: datetime


class DateTally(BaseModel):
    proposed_date_id: int
    starts_at: datetime
    yes: int
    maybe: int
    no: int
    score: float = Field(description="yes + 0.5 * maybe. Ranks the slots.")
    missing_voters: list[str] = Field(description="Active members who have not voted yet.")


class EventTally(BaseModel):
    event_id: int
    status: EventStatus
    eligible_voters: int
    dates: list[DateTally]
    leading_date_id: int | None
    is_tie: bool


class DateConfirm(BaseModel):
    person_id: int = Field(description="Must be the event host.")
    proposed_date_id: int | None = Field(
        default=None,
        description="Leave null to accept the leading date from the tally.",
    )


# --- attendance and post-session ---------------------------------------------------


class AttendanceOut(BaseModel):
    person_id: int
    name: str
    status: AttendanceStatus


class AttendanceSet(BaseModel):
    person_id: int
    status: AttendanceStatus


class GamePlayedAdd(BaseModel):
    game_id: int


class GamePlayedOut(BaseModel):
    id: int
    game_id: int
    game_name: str


class RatingCreate(BaseModel):
    person_id: int
    game_id: int
    score: int = Field(ge=MIN_RATING, le=MAX_RATING)


class RatingOut(ORMModel):
    id: int
    event_id: int
    game_id: int
    person_id: int
    score: int


class GameRatingSummary(BaseModel):
    game_id: int
    game_name: str
    average_score: float
    votes: int


class GameRecommendation(BaseModel):
    game_id: int
    game_name: str
    score: float
    owners: list[str] = Field(description="Attendees who can physically bring a copy.")
    reasons: list[str] = Field(description="Why the system ranked it here, in plain words.")


class RecommendationOut(BaseModel):
    event_id: int
    player_count: int
    recommendations: list[GameRecommendation]
    excluded: dict[str, str] = Field(
        default_factory=dict,
        description="Game name -> why it did not qualify.",
    )


class EventSummary(BaseModel):
    event: EventOut
    host_name: str
    confirmed_starts_at: datetime | None
    attendees: list[AttendanceOut]
    games_played: list[GamePlayedOut]
    ratings: list[GameRatingSummary]
