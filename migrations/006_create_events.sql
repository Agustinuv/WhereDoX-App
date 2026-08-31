-- One game night. The status column is the state machine the whole flow turns on:
--   draft     -> host assigned by rotation, no dates proposed yet
--   voting    -> host proposed dates, members are voting availability
--   confirmed -> host picked a date, attendance list exists
--   completed -> session happened, games played and ratings recorded
--   cancelled -> abandoned at any point
-- confirmed_date_id gets its foreign key in 012, because proposed_dates does not
-- exist yet at this point and the two tables reference each other.
CREATE TABLE IF NOT EXISTS events (
    id                BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    group_id          BIGINT      NOT NULL REFERENCES groups (id) ON DELETE CASCADE,
    host_id           BIGINT      NOT NULL REFERENCES people (id),
    title             TEXT        NOT NULL CHECK (length(trim(title)) > 0),
    status            TEXT        NOT NULL DEFAULT 'draft'
                                  CHECK (status IN ('draft', 'voting', 'confirmed', 'completed', 'cancelled')),
    confirmed_date_id BIGINT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
