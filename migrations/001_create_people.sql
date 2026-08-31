-- People are global: a person exists once and may belong to several groups.
-- telegram_user_id is nullable because the prototype has no Telegram integration yet;
-- it is the hook the future bot will use to resolve identity implicitly.
CREATE TABLE IF NOT EXISTS people (
    id               BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name             TEXT        NOT NULL CHECK (length(trim(name)) > 0),
    telegram_user_id BIGINT      UNIQUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
