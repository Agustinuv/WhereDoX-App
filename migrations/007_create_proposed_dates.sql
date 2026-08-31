-- Candidate slots the host offers for one event. Members vote on these, not on the event.
CREATE TABLE IF NOT EXISTS proposed_dates (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id   BIGINT      NOT NULL REFERENCES events (id) ON DELETE CASCADE,
    starts_at  TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (event_id, starts_at)
);
