-- Who physically owns which game. A game is only playable at an event if someone
-- attending brings it, which is the availability constraint the recommender uses.
CREATE TABLE IF NOT EXISTS game_libraries (
    id        BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    person_id BIGINT      NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    game_id   BIGINT      NOT NULL REFERENCES games (id) ON DELETE CASCADE,
    added_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (person_id, game_id)
);
