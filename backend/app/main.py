from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import attendance, events, games, groups, jobs, ratings, votes
from app.core.database import engine
from app.core.errors import DomainError
from app.core.logs import configure_logging

configure_logging()

DESCRIPTION = """
WhereDoX coordinates recurring board game nights: it picks the next host by rotation,
collects availability on proposed dates, and closes the loop with attendance and ratings.

**There is no authentication.** Endpoints that act on someone's behalf take an explicit
`person_id` — you are whoever you say you are. A Telegram bot would resolve identity from
`telegram_user_id` instead, and only this API layer would change.

Suggested tour: create a group and members, `GET /groups/{id}/next-host`, create an event,
propose dates, vote, check the tally, confirm, then log games and ratings.
"""

app = FastAPI(title="WhereDoX", description=DESCRIPTION, version="0.1.0")

for router in (
    groups.router,
    games.router,
    events.router,
    votes.router,
    attendance.router,
    ratings.router,
    jobs.router,
):
    app.include_router(router)


@app.exception_handler(DomainError)
async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
    """Single place where domain failures become HTTP responses."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health", tags=["meta"], summary="Liveness plus a real database round trip")
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
