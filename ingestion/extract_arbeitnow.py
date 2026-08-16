"""
Extract job postings from the Arbeitnow public API and land them in
raw.arbeitnow_jobs.

Run directly:
    python -m ingestion.extract_arbeitnow

Called by Airflow via a PythonOperator (see airflow/dags/job_market_pipeline_dag.py).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ingestion import db
from ingestion.config import DBConfig
from ingestion.http_utils import get_json
from ingestion.transform import arbeitnow_job_id, filter_arbeitnow_jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

API_URL = "https://www.arbeitnow.com/api/job-board-api"
SOURCE_NAME = "arbeitnow"
TABLE_NAME = "arbeitnow_jobs"


def _fetch_all_pages(first_page_url: str, max_pages: int = 10) -> list[dict]:
    """Arbeitnow paginates via a `links.next` URL in the response body."""
    all_jobs: list[dict] = []
    url = first_page_url
    for _ in range(max_pages):
        if not url:
            break
        payload = get_json(url)
        all_jobs.extend(payload.get("data", []))
        url = (payload.get("links") or {}).get("next")
    return all_jobs


def run(config: DBConfig | None = None) -> int:
    """Fetch, filter, and upsert Arbeitnow jobs. Returns the number of rows upserted."""
    started_at = datetime.now(timezone.utc)
    config = config or DBConfig.from_env()

    try:
        raw_jobs = _fetch_all_pages(API_URL)
        relevant_jobs = filter_arbeitnow_jobs(raw_jobs)
        logger.info(
            "Arbeitnow: fetched %d postings, %d relevant to data/software roles",
            len(raw_jobs), len(relevant_jobs),
        )

        records = [(arbeitnow_job_id(job), job) for job in relevant_jobs]

        with db.get_connection(config) as conn:
            db.ensure_schema(conn)
            upserted = db.upsert_raw_jobs(conn, TABLE_NAME, records)
            db.log_run(
                conn, SOURCE_NAME, len(raw_jobs), upserted, started_at, status="success"
            )
        logger.info("Arbeitnow: upserted %d rows into raw.%s", upserted, TABLE_NAME)
        return upserted

    except Exception as exc:  # noqa: BLE001
        logger.exception("Arbeitnow extraction failed")
        try:
            with db.get_connection(config) as conn:
                db.ensure_schema(conn)
                db.log_run(
                    conn, SOURCE_NAME, 0, 0, started_at, status="failed",
                    error_message=str(exc),
                )
        except Exception:  # noqa: BLE001
            logger.exception("Additionally failed to write the failure to raw.load_runs")
        raise


if __name__ == "__main__":
    run()
