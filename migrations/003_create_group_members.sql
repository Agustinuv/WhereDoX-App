-- Membership carries everything that is specific to a person *within a group*.
-- last_hosted_at lives here and not on people: hosting in one group must never
-- affect the rotation of another. NULL means "has never hosted" and wins the rotation.
CREATE TABLE IF NOT EXISTS group_members (
    id             BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    group_id       BIGINT      NOT NULL REFERENCES groups (id) ON DELETE CASCADE,
    person_id      BIGINT      NOT NULL REFERENCES people (id) ON DELETE CASCADE,
    is_active      BOOLEAN     NOT NULL DEFAULT TRUE,
    last_hosted_at DATE,
    joined_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (group_id, person_id)
);
