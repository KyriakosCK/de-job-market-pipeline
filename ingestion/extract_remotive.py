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

Unlike RemoteOK, Remotive labels every posting with its own
`category`, so relevance is decided from that label rather than by
keyword-matching free text -- see transform.filter_remotive_jobs.
"""
from __future__ import annotations

import logging

from ingestion.config import DBConfig
from ingestion.http_utils import get_json
from ingestion.runner import run_extractor
from ingestion.transform import filter_remotive_jobs, remotive_job_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

API_URL = "https://remotive.com/api/remote-jobs"
SOURCE_NAME = "remotive"
TABLE_NAME = "remotive_jobs"


def run(config: DBConfig | None = None) -> int:
    """Fetch, filter, and upsert Remotive jobs. Returns the number of rows upserted."""
    return run_extractor(
        source=SOURCE_NAME,
        table=TABLE_NAME,
        fetch=lambda: get_json(API_URL).get("jobs", []),
        filter_jobs=filter_remotive_jobs,
        job_id=remotive_job_id,
        config=config,
    )


if __name__ == "__main__":
    run()
