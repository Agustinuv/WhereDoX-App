-- Maps a Telegram native poll back to the domain, so an incoming poll_answer can be
-- turned into availability votes.
--
-- This has to be persisted rather than kept in memory because the two halves of the
-- exchange run in different processes: the API sends the poll when the host proposes
-- dates, and the bot receives the answer over long polling. The database is the only
-- thing they share.
--
-- One row per recipient: every member gets their own poll in their own private chat,
-- so each has a distinct poll id.
CREATE TABLE IF NOT EXISTS telegram_polls (
    id                BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    telegram_poll_id  TEXT        NOT NULL UNIQUE,
    event_id          BIGINT      NOT NULL REFERENCES events (id) ON DELETE CASCADE,
    chat_id           BIGINT      NOT NULL,
    -- Option i of the poll is proposed_date_ids[i]. Telegram reports answers by index,
    -- never by label, so the order is the mapping and must be stored as sent.
    proposed_date_ids BIGINT[]    NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_telegram_polls_event ON telegram_polls (event_id);
