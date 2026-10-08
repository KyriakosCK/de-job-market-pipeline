"""
Extract job postings from the RemoteOK public API and land them in
raw.remoteok_jobs.

Run directly:
    python -m ingestion.extract_remoteok

Called by Airflow via a PythonOperator (see airflow/dags/job_market_pipeline_dag.py).
"""
from __future__ import annotations

import logging

from ingestion.config import DBConfig
from ingestion.http_utils import get_json
from ingestion.runner import run_extractor
from ingestion.transform import clean_remoteok_job, filter_remoteok_jobs, remoteok_job_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

API_URL = "https://remoteok.com/api"
SOURCE_NAME = "remoteok"
TABLE_NAME = "remoteok_jobs"


def run(config: DBConfig | None = None) -> int:
    """Fetch, filter, and upsert RemoteOK jobs. Returns the number of rows upserted."""
    return run_extractor(
        source=SOURCE_NAME,
        table=TABLE_NAME,
        fetch=lambda: get_json(API_URL),
        filter_jobs=filter_remoteok_jobs,
        job_id=remoteok_job_id,
        # RemoteOK double-encodes non-ASCII text and HTML-escapes plain-text
        # fields; see transform.clean_remoteok_job.
        clean=clean_remoteok_job,
        config=config,
    )


if __name__ == "__main__":
    run()
