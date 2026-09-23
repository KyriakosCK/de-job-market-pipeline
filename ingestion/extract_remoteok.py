"""
Extract job postings from the RemoteOK public API and land them in
raw.remoteok_jobs.

Run directly:
    python -m ingestion.extract_remoteok

Called by Airflow via a PythonOperator (see airflow/dags/job_market_pipeline_dag.py).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ingestion import db
from ingestion.config import DBConfig
from ingestion.http_utils import get_json
from ingestion.transform import clean_remoteok_job, filter_remoteok_jobs, remoteok_job_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

API_URL = "https://remoteok.com/api"
SOURCE_NAME = "remoteok"
TABLE_NAME = "remoteok_jobs"


def run(config: DBConfig | None = None) -> int:
    """Fetch, filter, and upsert RemoteOK jobs. Returns the number of rows upserted."""
    started_at = datetime.now(timezone.utc)
    config = config or DBConfig.from_env()

    try:
        raw_jobs = get_json(API_URL)
        relevant_jobs = filter_remoteok_jobs(raw_jobs)
        logger.info(
            "RemoteOK: fetched %d postings, %d relevant to data/software roles",
            len(raw_jobs), len(relevant_jobs),
        )

        # RemoteOK double-encodes non-ASCII text and HTML-escapes plain-text
        # fields; see transform.clean_remoteok_job.
        records = [(remoteok_job_id(job), clean_remoteok_job(job)) for job in relevant_jobs]

        with db.get_connection(config) as conn:
            db.ensure_schema(conn)
            upserted = db.upsert_raw_jobs(conn, TABLE_NAME, records)
            db.log_run(
                conn, SOURCE_NAME, len(raw_jobs), upserted, started_at, status="success"
            )
        logger.info("RemoteOK: upserted %d rows into raw.%s", upserted, TABLE_NAME)
        return upserted

    except Exception as exc:  # noqa: BLE001 - we want to log + re-raise for Airflow
        logger.exception("RemoteOK extraction failed")
        try:
            with db.get_connection(config) as conn:
                db.ensure_schema(conn)
                db.log_run(
                    conn, SOURCE_NAME, 0, 0, started_at, status="failed",
                    error_message=str(exc),
                )
        except Exception:  # noqa: BLE001 - never let logging mask the real error
            logger.exception("Additionally failed to write the failure to raw.load_runs")
        raise


if __name__ == "__main__":
    run()
