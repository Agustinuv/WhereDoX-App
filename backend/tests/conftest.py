"""Shared fixtures.

Unit tests import nothing that touches a database. The integration fixtures below build
their own engine, apply the same migrations the real database uses, and truncate between
tests — so a run leaves no state behind and needs no separate schema.
"""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"

TABLES = [
    "ratings",
    "games_played",
    "attendances",
    "availability_votes",
    "proposed_dates",
    "events",
    "game_libraries",
    "group_members",
    "groups",
    "games",
    "people",
]

DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://wheredox:wheredox@localhost:5432/wheredox"

# These tests TRUNCATE every table, so falling back to DATABASE_URL is only safe while it
# points at a throwaway local database. Anything else — Supabase above all — must be named
# explicitly through TEST_DATABASE_URL, or a test run would wipe the demo data.
LOCAL_HOSTS = ("localhost", "127.0.0.1", "@db:", "@db/")


def _database_url() -> str:
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        return explicit

    fallback = os.environ.get("DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    if not any(host in fallback for host in LOCAL_HOSTS):
        pytest.exit(
            "Refusing to run: DATABASE_URL does not look local and these tests truncate "
            "every table. Set TEST_DATABASE_URL to a disposable database instead.",
            returncode=2,
        )
    return fallback


@pytest.fixture(scope="session")
def database_url() -> str:
    url = _database_url()
    # app.core.database builds its engine at import time, so this must be set before the
    # application package is imported anywhere in the test session.
    os.environ["DATABASE_URL"] = url
    return url


@pytest.fixture(scope="session")
def engine(database_url):
    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment problem, not a test failure
        pytest.skip(f"No database at {database_url}: {exc}")

    with engine.begin() as connection:
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            connection.execute(text(path.read_text()))
    yield engine
    engine.dispose()


@pytest.fixture
def clean_database(engine):
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
    return engine


@pytest.fixture
def client(clean_database):
    from fastapi.testclient import TestClient

    from app.core.database import get_session
    from app.main import app

    factory = sessionmaker(bind=clean_database, autoflush=False, expire_on_commit=False)

    def override() -> object:
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_session] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
