-- A group is the unit of coordination: host rotation and the voter roll are both
-- scoped to a group, so the same person can be mid-rotation in one and brand new in another.
CREATE TABLE IF NOT EXISTS groups (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       TEXT        NOT NULL CHECK (length(trim(name)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
