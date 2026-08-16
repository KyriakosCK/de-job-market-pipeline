-- Raw landing zone DDL for the SkillScope job-market pipeline.
-- This runs once (via ingestion/db.py :: ensure_schema, or manually) before
-- the first ingestion run. dbt only ever reads from the `raw` schema, it
-- never writes to it -- that boundary is what keeps EL (ingestion) and T
-- (dbt) cleanly separated.

CREATE SCHEMA IF NOT EXISTS raw;

-- One row per job posting seen from the RemoteOK API.
-- We keep the full payload as JSONB ("land it raw, model it later") so that
-- schema drift on the source side never breaks ingestion -- only dbt models
-- need updating when a new field needs to be surfaced.
CREATE TABLE IF NOT EXISTS raw.remoteok_jobs (
    job_id          TEXT PRIMARY KEY,
    payload         JSONB NOT NULL,
    source          TEXT NOT NULL DEFAULT 'remoteok',
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per job posting seen from the Arbeitnow API.
CREATE TABLE IF NOT EXISTS raw.arbeitnow_jobs (
    job_id          TEXT PRIMARY KEY,
    payload         JSONB NOT NULL,
    source          TEXT NOT NULL DEFAULT 'arbeitnow',
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Lightweight run log so the Airflow DAG (and anyone reading the warehouse)
-- can see ingestion history without digging through Airflow's own logs.
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
CREATE INDEX IF NOT EXISTS idx_arbeitnow_last_seen ON raw.arbeitnow_jobs (last_seen_at);
