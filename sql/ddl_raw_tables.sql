-- Raw landing zone. Ingestion runs this before every load (db.ensure_schema);
-- dbt only reads from `raw`, never writes to it.

CREATE SCHEMA IF NOT EXISTS raw;

-- Full API payloads as JSONB, one row per posting ever seen, so source
-- schema changes break a dbt model rather than ingestion.
CREATE TABLE IF NOT EXISTS raw.remoteok_jobs (
    job_id          TEXT PRIMARY KEY,
    payload         JSONB NOT NULL,
    source          TEXT NOT NULL DEFAULT 'remoteok',
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.remotive_jobs (
    job_id          TEXT PRIMARY KEY,
    payload         JSONB NOT NULL,
    source          TEXT NOT NULL DEFAULT 'remotive',
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per extractor run, success or failure.
CREATE TABLE IF NOT EXISTS raw.load_runs (
    run_id          BIGSERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    records_fetched INTEGER NOT NULL,
    records_upserted INTEGER NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    finished_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    status          TEXT NOT NULL,
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS idx_remoteok_last_seen ON raw.remoteok_jobs (last_seen_at);
CREATE INDEX IF NOT EXISTS idx_remotive_last_seen ON raw.remotive_jobs (last_seen_at);
