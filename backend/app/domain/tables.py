"""SQLAlchemy mappings.

These mirror migrations/*.sql by hand — the SQL is the source of truth, not these classes.
Nothing here creates schema; there is no create_all anywhere in the project.

Columns that the schema fills in (created_at, status, is_active) declare a server_default
so SQLAlchemy leaves them out of the INSERT and lets Postgres apply its own default,
instead of sending an explicit NULL.
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    SmallInteger,
    Text,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def timestamp_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = timestamp_column()


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = timestamp_column()


class GroupMember(Base):
    __tablename__ = "group_members"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    group_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("groups.id"))
    person_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("people.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    last_hosted_at: Mapped[date | None] = mapped_column(Date)
    joined_at: Mapped[datetime] = timestamp_column()


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    min_players: Mapped[int] = mapped_column(SmallInteger)
    max_players: Mapped[int] = mapped_column(SmallInteger)
    duration_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = timestamp_column()


class GameLibrary(Base):
    __tablename__ = "game_libraries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    person_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("people.id"))
    game_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("games.id"))
    added_at: Mapped[datetime] = timestamp_column()


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    group_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("groups.id"))
    host_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("people.id"))
    title: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=text("'draft'"))
    confirmed_date_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = timestamp_column()


class ProposedDate(Base):
    __tablename__ = "proposed_dates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("events.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = timestamp_column()


class AvailabilityVote(Base):
    __tablename__ = "availability_votes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    proposed_date_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("proposed_dates.id"))
    person_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("people.id"))
    availability: Mapped[str] = mapped_column(Text)
    voted_at: Mapped[datetime] = timestamp_column()


class Attendance(Base):
    __tablename__ = "attendances"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("events.id"))
    person_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("people.id"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'expected'"))
    created_at: Mapped[datetime] = timestamp_column()


class GamePlayed(Base):
    __tablename__ = "games_played"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("events.id"))
    game_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("games.id"))
    created_at: Mapped[datetime] = timestamp_column()


class Rating(Base):
    __tablename__ = "ratings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("events.id"))
    game_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("games.id"))
    person_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("people.id"))
    score: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = timestamp_column()
