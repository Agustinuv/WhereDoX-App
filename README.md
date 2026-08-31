# WhereDoX

*"Where do X"* — a coordinator for recurring board game nights.

Getting six people around a table is not a calendar problem, it is a decision problem:
somebody has to host, somebody has to pick a date that most people can make, and somebody
has to remember what happened afterwards. In practice that job rotates badly, the group
chat fills with "I can do Friday or maybe Saturday", and the same person ends up hosting
three times in a row.

WhereDoX makes those decisions explicitly and says why it made them.

## What the system decides

| Decision | Rule | Endpoint |
|---|---|---|
| Who hosts next | Longest without hosting **in this group**; never-hosted always wins | `GET /groups/{id}/next-host` |
| Which date wins | `yes + 0.5 × maybe`, ties reported rather than silently resolved | `GET /events/{id}/tally` |
| Who is expected | Everyone available on the winning slot, plus the host | `POST /events/{id}/confirm` |
| What to play | Owned by an attendee, fits the head count, then group taste vs. novelty | `GET /events/{id}/recommendations` |

Every one of these returns its reasoning, not just its answer — `next-host` says *"has
never hosted in this group"*, the recommender says *"rated 4.75 by this group / already
played 1x here"*, and the tally names who still owes a vote.

## Interfaces

Two, on purpose:

- **Swagger UI** (`/docs`) — every decision the system makes, endpoint by endpoint, with
  its reasoning in the response.
- **A chat client** (Next.js + Tailwind) that renders one game night as a conversation:
  system announcements, the availability poll with live results, each person's answer, the
  scheduler's reminder, and the post-session ratings. It is a stand-in for the Telegram bot
  that would be the real channel. Its home screen lists the groups the selected person
  belongs to; picking someone who is not in the open group sends you back there. Dark and
  light themes, toggled in the corner.

**There is no authentication.** A dropdown picks who you are "viewing as", and that
`person_id` is what the frontend sends. The available actions change with the selection:
the host can propose dates, close the vote and log games; everyone else votes and rates.
That is a deliberate prototype simplification, not an oversight — see *Known
simplifications*. With Telegram the same identity would come from `telegram_user_id`, and
only the `api/` layer would change.

## Run it

```bash
cp .env.example .env
docker compose up -d db          # local Postgres
for f in migrations/*.sql; do
  docker compose exec -T db psql -U wheredox -d wheredox -q < "$f"
done
docker compose up -d api web
```

Then open <http://localhost:3000> for the chat client and
<http://localhost:8000/docs> for Swagger. If those ports are taken, set `WEB_PORT` /
`API_PORT` in `.env`.

To point at Supabase instead, set `DATABASE_URL` to its pooler URI in `.env`, apply
`migrations/` there once (see `migrations/README.md`), and leave the `db` service down.

### Demo data

```bash
docker compose exec api python -m seed.seed_data --reset
```

Loads one group with rotation history already in progress, a finished night with ratings,
and an event mid-vote — so a demo never opens on an empty screen. The interviewers' own
group is meant to be created live, through the API, to show nothing is hardcoded to a
single group.

### Without Docker

```bash
# Backend
python3 -m venv backend/.venv && backend/.venv/bin/pip install -e "backend[dev]"
cd backend
DATABASE_URL=postgresql+psycopg://wheredox:wheredox@localhost:5432/wheredox \
  .venv/bin/uvicorn app.main:app --reload

# Frontend (BACKEND_URL defaults to http://localhost:8010)
cd frontend && npm install && npm run dev
```

## Tests

```bash
cd backend
.venv/bin/pytest                      # everything
.venv/bin/pytest -m "not integration" # unit only, no database needed
.venv/bin/pytest tests/unit/test_host_rotation_service.py::test_a_tie_on_the_same_date_goes_to_the_most_senior
```

Integration tests apply the real migrations to `TEST_DATABASE_URL` (falling back to
`DATABASE_URL`) and truncate between tests. Formatting is `black`.

## Architecture

```text
backend/app/
  api/          thin HTTP adapter — translates requests to service calls, no logic
  services/     every decision: rotation, tally, confirmation, recommendation
  repositories/ the only code that touches the database
  scheduler/    reminder job, currently a stub that logs instead of sending
frontend/
  lib/timeline  pure: turns API data into chat messages
  hooks/        server state, refetched wholesale after every action
  components/   presentation only
```

The browser talks only to the Next server, which proxies `/api/*` to FastAPI. That is why
the backend carries no CORS configuration. Next resolves that rewrite at **build** time,
so `BACKEND_URL` is a Docker build argument, not a runtime variable.

The layering exists to make pieces swappable, and the two decisions worth showing are
pure functions with no database at all: `select_next_host` takes a list of candidates and
returns one, `build_tally` takes rows and returns standings. Both are unit tested without
a session, which is why the rules can be argued about directly.

Groups are the unit of multi-tenancy. `last_hosted_at` lives on the **membership**, not on
the person, so hosting in one group never disturbs another group's rotation.

## Known simplifications

Deliberate, and each one has a reason:

- **No authentication.** Endpoints take an explicit `person_id`. Telegram would make this
  implicit; adding a login to a prototype would have cost demo time and proved nothing.
- **Plain SQL migrations**, numbered and applied by hand. A migration tool does not pay
  for itself at this scale. They are idempotent, so re-running the folder is safe.
- **The scheduler logs instead of sending.** `POST /jobs/reminders` triggers it manually,
  standing in for a real cron. No delivery channel is wired anywhere else in the code.
- **The rotation advances on confirmation, not on completion.** The hosting slot is taken
  as soon as the date is locked; a cancelled event is rare enough to fix by hand.
- **No voting deadline.** A poll stays open until the host closes it. Instead of a timer the
  tally names who has not answered yet — for a group of six friends, being listed as the
  person holding everyone up works better than an expiry nobody agreed to. A real deadline
  is a roadmap item, not an oversight.

## Roadmap

- A Telegram bot as the real channel.
- One-off activity groups (a tennis match, a hike): no host rotation, and the organiser
  closes the invitation by choice instead of by tally. Likely a separate state machine
  reusing `groups`/`group_members` — see `docs/initial-project-plan.md`.
