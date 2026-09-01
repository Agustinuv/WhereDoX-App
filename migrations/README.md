# Migrations

Plain, numbered SQL applied **in ascending order, once**. There is no migration tool
(Alembic and friends) on purpose: at prototype scale the versioning machinery costs more
than it returns. Every file is idempotent (`IF NOT EXISTS`, guarded `ADD CONSTRAINT`), so
re-running the folder is safe.

## Apply

Against the local Docker database:

```bash
docker compose up -d db
for f in migrations/*.sql; do
  docker compose exec -T db psql -U wheredox -d wheredox < "$f"
done
```

Against Supabase (or any remote Postgres) — take the connection string from the project's
*Database → Connection string → URI* and use the pooler host on port `6543`:

```bash
for f in migrations/*.sql; do psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"; done
```

Or paste each file, in order, into the Supabase SQL editor.

## Order and dependencies

`001`–`011` create one table each and must run in numeric order — each references the
tables before it. `012` closes the loop: it adds the `events.confirmed_date_id` foreign
key (which cannot exist until `proposed_dates` does, since the two tables reference each
other) and creates the indexes that a `UNIQUE` constraint does not already provide.

`013` adds `telegram_polls`, the only table the bot needed. It maps a Telegram poll id
back to its event and each option index back to a proposed date. It has to be a table
rather than memory because the API process sends the poll and the bot process receives the
answer — the database is all they share.
