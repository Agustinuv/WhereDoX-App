-- Cross-table constraints and the indexes that are not already implied by a UNIQUE.
-- A UNIQUE (a, b) already indexes a, so only trailing columns and bare foreign keys
-- are listed here.

-- Deferred foreign key: events and proposed_dates reference each other, so this one
-- could not be declared in 006. ADD CONSTRAINT has no IF NOT EXISTS, hence the guard.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'events_confirmed_date_id_fkey'
    ) THEN
        ALTER TABLE events
            ADD CONSTRAINT events_confirmed_date_id_fkey
            FOREIGN KEY (confirmed_date_id) REFERENCES proposed_dates (id) ON DELETE SET NULL;
    END IF;
END
$$;

-- Host rotation reads the active roster of one group ordered by last_hosted_at.
CREATE INDEX IF NOT EXISTS idx_group_members_group_active
    ON group_members (group_id, last_hosted_at NULLS FIRST)
    WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_group_members_person
    ON group_members (person_id);

CREATE INDEX IF NOT EXISTS idx_events_group_status ON events (group_id, status);
CREATE INDEX IF NOT EXISTS idx_events_host          ON events (host_id);

-- The vote tally groups by proposed date and counts by availability.
CREATE INDEX IF NOT EXISTS idx_availability_votes_tally
    ON availability_votes (proposed_date_id, availability);
CREATE INDEX IF NOT EXISTS idx_availability_votes_person
    ON availability_votes (person_id);

CREATE INDEX IF NOT EXISTS idx_attendances_person ON attendances (person_id);

CREATE INDEX IF NOT EXISTS idx_games_played_event ON games_played (event_id);
CREATE INDEX IF NOT EXISTS idx_games_played_game  ON games_played (game_id);

CREATE INDEX IF NOT EXISTS idx_ratings_game   ON ratings (game_id);
CREATE INDEX IF NOT EXISTS idx_ratings_person ON ratings (person_id);

CREATE INDEX IF NOT EXISTS idx_game_libraries_game ON game_libraries (game_id);
