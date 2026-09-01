# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A time-boxed case study for a Product Engineer role at Wherex (~36 hours, code plus a
45-minute presentation). **WhereDoX** ("where do X") coordinates recurring board game
nights: it picks the next host by rotation, collects availability on proposed dates,
confirms one, and closes the loop with attendance, games played and ratings.

Two facts shape every decision:

- **Evaluators grade product criterion, not technical completeness.** The interesting code
  is the part that *makes decisions* — that is `services/`. Depth belongs there, not in
  CRUD or coverage.
- **There is a live demo.** Phases in `docs/initial-project-plan.md` are ordered so every
  boundary is demoable. Cuts come from the end, never from the core flow.

`docs/initial-project-plan.md` (Spanish) is the agreed plan and the reason behind most
structural choices; `docs/Caso práctico - Wherex.pdf` is the assignment brief.

## Commands

```bash
# Local stack
cp .env.example .env
docker compose up -d db
for f in migrations/*.sql; do docker compose exec -T db psql -U wheredox -d wheredox -q < "$f"; done
docker compose up -d api web        # :3000 chat client, :8000/docs Swagger
docker compose up -d bot            # needs TELEGRAM_BOT_TOKEN in .env
docker compose exec api python -m seed.seed_data --reset

# Live-demo state: no event open, presenter's Telegram re-bound to the next host.
# See docs/demo-runbook.md — the 4-minute script and the settings that silently break it.
docker compose exec api python -m seed.seed_data --reset --demo --telegram-user-id <id>
# API_PORT / WEB_PORT in .env override the host ports.

# Frontend
cd frontend && npm install && npm run dev   # BACKEND_URL defaults to http://localhost:8010
npx tsc --noEmit && npm run build

# Host-side dev (venv already at backend/.venv)
cd backend
DATABASE_URL=postgresql+psycopg://wheredox:wheredox@localhost:5432/wheredox \
  .venv/bin/uvicorn app.main:app --reload

# Bot on the host
cd backend && .venv/bin/python -m bot.main

# Tests
export TEST_DATABASE_URL=postgresql+psycopg://wheredox:wheredox@localhost:5432/wheredox_test
.venv/bin/pytest                              # all 69
.venv/bin/pytest -m "not integration"         # unit only, no database
.venv/bin/pytest tests/unit/test_voting_service.py::test_counts_and_score_per_date
.venv/bin/black app bot seed tests
```

Integration tests apply `migrations/*.sql` to `TEST_DATABASE_URL` and truncate between
tests. **Always point it at a throwaway database** (`wheredox_test`). It falls back to
`DATABASE_URL`, whose guard only rejects non-local URLs — running against the local
`wheredox` database passes that guard and destroys the demo seed. Re-seed with
`docker compose exec api python -m seed.seed_data --reset` if it happens.

## Architecture

```text
backend/app/
  api/          thin HTTP adapter — translates requests to service calls, no logic
  services/     every decision: rotation, tally, confirmation, recommendation
  repositories/ the only code that touches the database
  scheduler/    reminder job, triggered by hand instead of by cron
backend/bot/    Telegram adapter — long polling, handlers, no rules
  handlers/     onboarding, voting, game_check, rating, status (/junta)
  keyboards.py  the only place that turns port Buttons into Telegram markup
  session.py    runs the sync data layer off the asyncio event loop
frontend/       Next.js 16 (App Router) + Tailwind v4, chat-style client
  lib/timeline.ts  pure: API data -> chat messages
  hooks/useWorkspace.ts  all server state, refetched wholesale after each action
  components/   presentation only
```

**`bot/` imports `app/`, never the reverse.** That is load-bearing: it is why the API runs
with no bot, why the bot added zero business rules, and why the substitutability argument
survived contact with a second real channel. A handler that grows an `if` about who may
vote has moved a decision out of `services/` and broken the story.

The boundaries exist to make pieces swappable, and that substitutability *is* the argument
being presented — a router that reaches into a repository breaks the story, not just the
style guide. Domain exceptions (`core/errors.py`) are raised by services and mapped to HTTP
by one handler in `main.py`; services never import fastapi.

**The two core decisions are pure functions**, deliberately: `select_next_host` takes
candidates and returns one, `build_tally` takes rows and returns standings. Neither takes a
session. Repositories return *unranked* data so the ranking stays in the service where it is
unit tested. Keep it that way — moving a tally into SQL would be faster and would cost the
demo its most testable moment.

**Groups are the unit of multi-tenancy.** `last_hosted_at` lives on `group_members`, not on
`people`, so hosting in one group never disturbs another's rotation. The live demo depends
on this: a seeded group with history plus a new group created in front of the interviewers.

Event state machine: `draft → voting → confirmed → completed`, plus `cancelled`.

## Deliberate simplifications — do not "fix" these

Each is argued for and will be defended out loud:

- **No authentication in the REST API.** Every endpoint takes an explicit `person_id`. The
  bot resolves identity implicitly from `telegram_user_id` instead, and adding it changed
  only the adapter — no service, repository or rule moved.
- **The deep-link token is the bare `person_id`.** `t.me/<bot>?start=3` binds you as person
  3. Guessable, deliberately: the REST API already accepts any `person_id` from anyone, so
  encrypting this one door would not secure a building with no walls. Do not "harden" it in
  isolation — the fix is auth everywhere or nowhere.
- **Telegram has no "maybe".** A native poll only reports checked/unchecked, so a tap is
  `yes` and a blank is `no`. `MAYBE_WEIGHT` still governs the tally and the web client
  still produces maybes; the poll was judged worth more than the half point. Agreed
  explicitly — do not "fix" it by replacing the poll with buttons.
- **Outbound Telegram calls are plain HTTPS via httpx, not python-telegram-bot.** Sending
  needs only the token, so the API process notifies without any channel to the bot process.
  The bot library is used solely for *receiving*.
- **"Remind me later" is an in-memory job** in the bot process; a restart forgets it.
  Persisting it means a job table plus a policy for missed jobs — not something to add
  silently.
- **`REMINDER_LEAD_HOURS` gates the reminder job silently.** An event outside the window
  is skipped and the endpoint returns `[]` with no error. It is the single likeliest way
  to lose the reminder beat in a demo — `docs/demo-runbook.md` sets it to 240.
- **The host announcement does not repeat the rotation's reason.** Re-deriving *why*
  someone was picked in `announcement_service` would duplicate `select_next_host`'s rule
  in a second place. `GET /next-host` and the web client already show it verbatim.
- **Announcements fan out synchronously inside the request.** `POST /confirm` and
  `POST /complete` send one Telegram call per recipient before responding — a second or
  two at six members. A queue is the right answer at real scale and the wrong one here.
  `announcement_service.never_fails` guarantees a delivery failure can never roll back the
  decision that triggered it.
- **Hand-written, numbered plain-SQL migrations**, applied by hand, no Alembic. They are
  idempotent, so re-running the folder is safe. `012` closes the circular
  `events ↔ proposed_dates` foreign key and adds indexes a `UNIQUE` does not already imply.
- **No cron.** `POST /jobs/reminders` triggers the reminder manually. The job does send now
  — through `NotificationPort` (`services/ports.py`), which resolves to Telegram when
  `TELEGRAM_BOT_TOKEN` is set and to a logger when it is not. Leaving the token unset is a
  supported mode, and the whole test suite runs in it.
- **Rotation advances on confirmation, not completion.** The slot is taken when the date is
  locked.
- **Ties are reported, not auto-resolved.** `POST /confirm` refuses a tie unless the host
  names a date. The seed is tuned to have a clear leader so the demo's happy path flows.
- **There is no voting deadline.** Voting closes only when the host confirms a date; nothing
  expires on its own and nothing auto-confirms. The tally names who still owes a vote, which
  is the social nudge that stands in for a timer. Adding a real deadline means a schema
  column plus a decision about what happens when it passes — do not add one silently.

## Frontend specifics

- Two routes: `/` (home — the groups the selected person belongs to) and
  `/groups/[groupId]` (the chat workspace). Identity lives in `ViewerProvider` (React
  context + localStorage), not in either page, so it survives navigation and reloads.
- **Membership gates the workspace**: `Workspace` redirects to `/` when the selected person
  is not an active member of that group. It waits for `membersLoaded` first — otherwise the
  initial empty roster would bounce every visitor straight back home.
- Theme: `data-theme` on `<html>`, set before first paint by a script in `layout.tsx` so a
  light-mode reload never flashes dark. Dark is the default.
- The browser only ever calls `/api/*` on the Next origin; `next.config.ts` rewrites that
  to FastAPI **server-side**, which is why the backend has no CORS setup. Next resolves
  rewrites at *build* time into its routes manifest, so `BACKEND_URL` is a Docker **build
  arg** — setting it only at runtime silently does nothing.
- Tailwind v4: tokens live in `@theme` inside `app/globals.css` and generate utilities
  (`bg-panel`, `border-edge`, `text-ink`, `bg-warn-soft`). Do not use the v3
  `bg-[--color-panel]` form, and there is no `tailwind.config.js`. **Colours must go through
  these semantic tokens** — the light theme works by redefining the variables under
  `:root[data-theme="light"]`, so a hardcoded `text-slate-400` silently breaks it. Solid
  saturated buttons (`bg-emerald-600 text-white`) are the deliberate exception; they read
  correctly on both.
- `agentRules: false` in `next.config.ts` stops Next regenerating its own
  `AGENTS.md`/`CLAUDE.md` inside `frontend/` on every dev run.
- `useWorkspace` refetches everything after each action rather than patching local state.
  Deliberate: the data is tiny and the screen can then never disagree with what the backend
  decided, which is the point of the demo.
- Timestamps are UTC over the wire and local on screen (`toUtcIso` / `formatDateTime`).

## Conventions

- **Identifiers, comments and error messages are English**, per the IMFD team standard,
  even though the plan doc is Spanish. The exception the standard grants is copy shown to
  end users: UI strings and the recommender's `reasons`/`excluded` text are Spanish, because
  they are product copy rather than logs. Tables: `people`, `groups`, `group_members`, `games`,
  `game_libraries`, `events`, `proposed_dates`, `availability_votes`, `attendances`,
  `games_played`, `ratings`, `telegram_polls`.
- Domain tuning knobs live in `app/core/constants.py` (`MAX_PROPOSED_DATES`, `MAYBE_WEIGHT`,
  recommender weights); per-deployment values live in `app/core/config.py` via
  `pydantic-settings` (`TELEGRAM_BOT_TOKEN`, `DISPLAY_TIMEZONE`, `REMINDER_SNOOZE_MINUTES`).
  `frontend/lib/constants.ts` mirrors the few the UI needs — the backend stays the
  authority and re-validates.
- `app/core/callbacks.py` is the button wire format, shared by both ends: `app/` builds the
  buttons, `bot/` reads the taps. It lives in `core/` rather than `bot/` precisely so `app/`
  never has to import the adapter. Decoding is strict — a bad parse must raise, because a
  malformed `callback_data` fails *silently* in Telegram.
- `app/core/database.py` builds its engine at import time, so importing anything that pulls
  it in needs a valid `DATABASE_URL`. `bot/session.py` imports it inside the function for
  that reason; keep it that way or the bot's unit tests start needing a database.
- `migrations/*.sql` is the schema's source of truth. `app/domain/tables.py` mirrors it by
  hand; there is no `create_all` anywhere. Columns the schema defaults (`created_at`,
  `status`, `is_active`) declare a `server_default` so SQLAlchemy omits them from INSERTs
  rather than sending an explicit NULL.
- `black` (line length 100), not `ruff`. Pydantic `BaseModel` over dataclasses.
- The team standard forbids hand-written migrations; this repo departs from it knowingly
  (see above). Everything else in that standard applies.

## Deviation from the plan worth knowing

The plan says `docker-compose.yml` only needs the backend because Supabase is cloud. A local
`db` service was added anyway so the project runs and tests without cloud credentials —
pointing `DATABASE_URL` at Supabase and leaving `db` down is still fully supported.
