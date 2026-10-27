"""Land Remotive postings in raw.remotive_jobs: python -m ingestion.extract_remotive

Remotive's API terms ask for attribution (the posting `url` is stored for
that) and no more than ~4 calls a day; the pipeline makes one.
"""
from __future__ import annotations

import logging

from ingestion.config import DBConfig
from ingestion.http_utils import get_json
from ingestion.runner import run_extractor
from ingestion.transform import filter_remotive_jobs, remotive_job_id


def run(config: DBConfig | None = None) -> int:
    return run_extractor(
        source="remotive",
        table="remotive_jobs",
        fetch=lambda: get_json("https://remotive.com/api/remote-jobs").get("jobs", []),
        filter_jobs=filter_remotive_jobs,
        job_id=remotive_job_id,
        config=config,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
