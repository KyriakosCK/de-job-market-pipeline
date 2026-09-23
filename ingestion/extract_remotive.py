"""
Extract job postings from the Remotive public API and land them in
raw.remotive_jobs.

Run directly:
    python -m ingestion.extract_remotive

Remotive's API terms ask consumers to credit Remotive as the source and link
back to the posting URL, not to republish their listings on third-party job
boards, and to keep request volume low (they suggest no more than ~4 calls a
day). This pipeline calls the endpoint once per scheduled run and stores the
canonical Remotive `url` for every posting, so attribution is always possible
downstream.

Unlike RemoteOK and Arbeitnow, Remotive labels every posting with its own
`category`, so relevance is decided from that label rather than by
keyword-matching free text -- see transform.filter_remotive_jobs.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ingestion import db
from ingestion.config import DBConfig
from ingestion.http_utils import get_json
from ingestion.transform import filter_remotive_jobs, remotive_job_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

API_URL = "https://remotive.com/api/remote-jobs"
SOURCE_NAME = "remotive"
TABLE_NAME = "remotive_jobs"


def run(config: DBConfig | None = None) -> int:
    """Fetch, filter, and upsert Remotive jobs. Returns the number of rows upserted."""
    started_at = datetime.now(timezone.utc)
    config = config or DBConfig.from_env()

    try:
        payload = get_json(API_URL)
        raw_jobs = payload.get("jobs", [])
        relevant_jobs = filter_remotive_jobs(raw_jobs)
        logger.info(
            "Remotive: fetched %d postings, %d in tech categories",
            len(raw_jobs), len(relevant_jobs),
        )

        records = [(remotive_job_id(job), job) for job in relevant_jobs]

        with db.get_connection(config) as conn:
            db.ensure_schema(conn)
            upserted = db.upsert_raw_jobs(conn, TABLE_NAME, records)
            db.log_run(
                conn, SOURCE_NAME, len(raw_jobs), upserted, started_at, status="success"
            )
        logger.info("Remotive: upserted %d rows into raw.%s", upserted, TABLE_NAME)
        return upserted

    except Exception as exc:  # noqa: BLE001 - log + re-raise so Airflow sees the failure
        logger.exception("Remotive extraction failed")
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
