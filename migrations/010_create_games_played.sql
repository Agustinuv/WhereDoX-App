-- Which games actually made it to the table. No unique constraint on (event_id, game_id):
-- a group can play the same game twice in one night.
CREATE TABLE IF NOT EXISTS games_played (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id   BIGINT      NOT NULL REFERENCES events (id) ON DELETE CASCADE,
    game_id    BIGINT      NOT NULL REFERENCES games (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
