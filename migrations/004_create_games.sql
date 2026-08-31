-- Game catalogue, shared across groups. Player ranges are what the future
-- recommender filters on once the confirmed attendee count is known.
CREATE TABLE IF NOT EXISTS games (
    id               BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name             TEXT        NOT NULL UNIQUE CHECK (length(trim(name)) > 0),
    min_players      SMALLINT    NOT NULL CHECK (min_players > 0),
    max_players      SMALLINT    NOT NULL CHECK (max_players > 0),
    duration_minutes SMALLINT    CHECK (duration_minutes > 0),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (max_players >= min_players)
);
