-- Materialised when the host confirms a date: everyone who voted yes/maybe on the
-- winning slot starts as 'expected', and is reconciled to attended/absent afterwards.
CREATE TABLE IF NOT EXISTS attendances (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id   BIGINT      NOT NULL REFERENCES events (id) ON DELETE CASCADE,
    person_id  BIGINT      NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    status     TEXT        NOT NULL DEFAULT 'expected'
                           CHECK (status IN ('expected', 'attended', 'absent')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (event_id, person_id)
);
