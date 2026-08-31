# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status: planning only, no code yet

The repository currently contains `docs/` and nothing else. There is no source tree, no
`docker-compose.yml`, no dependency manifest, no tests, and no git history. Do not go looking
for them — the build/lint/test commands below are **planned**, not available.

- `docs/Caso práctico - Wherex.pdf` — the assignment brief from Wherex.
- `docs/initial-project-plan.md` — the agreed development plan (written in Spanish). **Read this
  first for any implementation task**; it fixes the stack, the layering, the phase order, and the
  deliberate simplifications listed below.

When starting a phase, follow the plan's structure rather than inventing a new one, and update the
plan if a decision changes during implementation.

## What this project is

A time-boxed case study for a Product Engineer role at Wherex (36 hours total, ~28h of code + 8h of
presentation). The product is a **coordinator for recurring board-game nights**: the system picks
the next host by rotation, the host proposes dates, the group votes availability, the host confirms,
and the group logs attendance, games played and ratings afterwards.

Two consequences shape every decision:

- **The evaluators grade criterion and product thinking, not technical completeness.** The
  interesting code is the part that *makes decisions* (host rotation, vote tally, optional game
  recommender) — that is `services/`. Depth belongs there, not in CRUD or coverage.
- **The deliverable includes a live 45-minute demo.** Phases in the plan are ordered so that every
  phase boundary is a demoable stopping point. If time runs short, cut from the end (phase 7, the
  recommender) — never phases 0–5.

## Planned architecture

Monorepo. Backend-only; Supabase (cloud Postgres) is the database, so Docker runs just the API
service. The interface *is* FastAPI's Swagger UI at `/docs` — there is no frontend, and a Telegram
bot is explicitly deferred to the roadmap.

Strict one-way layering, which is the core of the "simple architecture" argument in the
presentation:

```text
api/          thin HTTP adapter — translates requests to service calls, no logic
services/     all decision logic (host rotation, vote tally, recommender)
repositories/ the only code that touches the database
scheduler/    reminder job stub, isolated so a real cron can replace it untouched
```

The point of the boundaries is substitutability: swapping the API layer for a Telegram webhook, or
the scheduler stub for Cloud Scheduler, must not require touching `services/`. Keep it that way —
a router that reaches into a repository breaks the story being presented.

### Multi-tenancy is not optional

Every event belongs to a **group**. Host rotation and the voter roll are both scoped by `group_id`,
and `last_hosted_at` lives on the person↔group membership — not on the person — so someone's
hosting turn in one group never affects another. The live demo depends on this: a seeded group with
existing rotation history, plus a brand-new group created in front of the interviewers.

### Schema names

The plan doc writes the schema in Spanish; the code and database use **English**, per the team
standard. Translate as you go, using these names:

```text
people
groups
group_members     (last_hosted_at)
games
game_libraries
events            (group_id, host_id, status)
proposed_dates
availability_votes
attendances
games_played
ratings
```

## Deliberate simplifications — do not "fix" these

These look like oversights and are not. They are argued for in the plan and will be defended out
loud in the presentation:

- **No authentication.** Every endpoint takes an explicit `person_id`; whoever calls the API acts
  as that person. With Telegram this becomes implicit (`telegram_user_id` → person lookup).
- **Hand-written, numbered plain-SQL migrations** in `migrations/`, applied once by hand via the
  Supabase SQL editor or `psql`. No Alembic.
- **The scheduler is a stub** that logs instead of sending. It is intentionally untested.
- **Tests are pragmatic, not exhaustive**: unit tests on pure service logic (rotation, tally),
  integration tests on 2–3 critical endpoints only. `api/` is not tested line by line.

## Relationship to the IMFD team standard

The team standard is injected into every session. It applies here, with one agreed exception:

- **Migrations** are hand-written plain SQL applied manually, as the plan specifies — the standard
  forbids this, but Alembic does not pay for itself at prototype scale. Decided, not an oversight.
- **Identifiers are English**, per the standard, even though the plan doc is written in Spanish.
  See "Schema names" above.

Everything else in the standard applies normally — layered separation (which the plan already
follows), ORM over raw SQL in application code, pydantic models, `black`, config from environment,
and the Platanus commit convention.

## Planned commands

None of these work yet; they describe the intended setup so later phases stay consistent.

- `docker compose up` — brings up the backend against the Supabase connection string from `.env`.
- Migrations: apply `migrations/*.sql` in numeric order via `psql` or the Supabase SQL editor.
- `seed/seed_data.py` — loads the demo group with rotation history already in progress.

Formatting is `black` (not `ruff`), per the team standard.
