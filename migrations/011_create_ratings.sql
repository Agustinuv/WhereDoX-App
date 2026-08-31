-- Post-session feedback: one score per person per game per event. This is the table
-- the recommender reads to learn group taste, and the step with the most adoption friction.
CREATE TABLE IF NOT EXISTS ratings (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id   BIGINT      NOT NULL REFERENCES events (id) ON DELETE CASCADE,
    game_id    BIGINT      NOT NULL REFERENCES games (id) ON DELETE CASCADE,
    person_id  BIGINT      NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    score      SMALLINT    NOT NULL CHECK (score BETWEEN 1 AND 5),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (event_id, game_id, person_id)
);
