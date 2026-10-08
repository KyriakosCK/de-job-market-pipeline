"""
The fetch -> filter -> upsert -> log sequence every extractor shares.

Each extract_*.py only describes what is specific to its source (URL,
pagination, filter, job ID, any payload cleanup) and hands it to
run_extractor, so run logging and failure handling behave the same for
every source.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable

from ingestion import db
from ingestion.config import DBConfig

logger = logging.getLogger(__name__)


def run_extractor(
    *,
    source: str,
    table: str,
    fetch: Callable[[], list[dict]],
    filter_jobs: Callable[[list[dict]], list[dict]],
    job_id: Callable[[dict], str],
    clean: Callable[[dict], dict] | None = None,
    config: DBConfig | None = None,
) -> int:
    """Fetch, filter, and upsert one source's jobs. Returns the number of rows upserted.

    Every run is logged to raw.load_runs, success or failure. A failure is
    re-raised afterwards so the caller (Airflow, run_pipeline.bat) sees it.
    """
    started_at = datetime.now(timezone.utc)
    config = config or DBConfig.from_env()
    # Kept outside the try so a failed run still records how many postings
    # were fetched before the error, e.g. when only the database write failed.
    records_fetched = 0

    try:
        raw_jobs = fetch()
        records_fetched = len(raw_jobs)
        relevant_jobs = filter_jobs(raw_jobs)
        logger.info(
            "%s: fetched %d postings, %d relevant", source, records_fetched, len(relevant_jobs)
        )

        records = [
            (job_id(job), clean(job) if clean else job) for job in relevant_jobs
        ]

        with db.get_connection(config) as conn:
            db.ensure_schema(conn)
            upserted = db.upsert_raw_jobs(conn, table, records)
            db.log_run(conn, source, records_fetched, upserted, started_at, status="success")
        logger.info("%s: upserted %d rows into raw.%s", source, upserted, table)
        return upserted

    except Exception as exc:  # noqa: BLE001 - log + re-raise so the scheduler sees the failure
        logger.exception("%s extraction failed", source)
        try:
            with db.get_connection(config) as conn:
                db.ensure_schema(conn)
                db.log_run(
                    conn, source, records_fetched, 0, started_at, status="failed",
                    error_message=str(exc),
                )
        except Exception:  # noqa: BLE001 - never let logging mask the real error
            logger.exception("Additionally failed to write the failure to raw.load_runs")
        raise
