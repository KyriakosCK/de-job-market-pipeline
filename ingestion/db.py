"""
Thin Postgres helper layer used by every extractor.

Deliberately not an ORM: for a raw JSONB landing zone, plain SQL with
`execute_values` upserts is simpler, faster, and easier to reason about
than an abstraction layer that would just get in the way.
"""
from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator

import psycopg2
import psycopg2.extras

from ingestion.config import DBConfig

logger = logging.getLogger(__name__)

DDL_PATH = Path(__file__).resolve().parent.parent / "sql" / "ddl_raw_tables.sql"


@contextmanager
def get_connection(config: DBConfig | None = None) -> Iterator[psycopg2.extensions.connection]:
    config = config or DBConfig.from_env()
    conn = psycopg2.connect(config.dsn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_schema(conn: psycopg2.extensions.connection) -> None:
    """Create the raw schema/tables if they don't already exist (idempotent)."""
    ddl = DDL_PATH.read_text()
    with conn.cursor() as cur:
        cur.execute(ddl)


def upsert_raw_jobs(
    conn: psycopg2.extensions.connection,
    table: str,
    records: Iterable[tuple[str, dict]],
) -> int:
    """Upsert (job_id, payload) pairs into `raw.<table>`.

    On conflict we refresh the payload and last_seen_at, but keep the
    original first_seen_at -- that's what lets downstream dbt models
    compute "how long has this posting been live" style metrics.
    """
    records = list(records)
    if not records:
        return 0

    now = datetime.now(timezone.utc)
    rows = [(job_id, json.dumps(payload), now, now) for job_id, payload in records]

    query = f"""
        INSERT INTO raw.{table} (job_id, payload, first_seen_at, last_seen_at)
        VALUES %s
        ON CONFLICT (job_id) DO UPDATE
        SET payload = EXCLUDED.payload,
            last_seen_at = EXCLUDED.last_seen_at
    """
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur, query, rows, template="(%s, %s::jsonb, %s, %s)"
        )
    return len(rows)


def log_run(
    conn: psycopg2.extensions.connection,
    source: str,
    records_fetched: int,
    records_upserted: int,
    started_at: datetime,
    status: str,
    error_message: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO raw.load_runs
                (source, records_fetched, records_upserted, started_at, status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (source, records_fetched, records_upserted, started_at, status, error_message),
        )
