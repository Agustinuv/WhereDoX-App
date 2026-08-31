-- One vote per person per proposed slot. 'maybe' is kept distinct from 'no' on purpose:
-- the tally breaks ties with it instead of discarding the signal.
CREATE TABLE IF NOT EXISTS availability_votes (
    id               BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    proposed_date_id BIGINT      NOT NULL REFERENCES proposed_dates (id) ON DELETE CASCADE,
    person_id        BIGINT      NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    availability     TEXT        NOT NULL CHECK (availability IN ('yes', 'maybe', 'no')),
    voted_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (proposed_date_id, person_id)
);
