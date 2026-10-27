"""Land RemoteOK postings in raw.remoteok_jobs: python -m ingestion.extract_remoteok"""
from __future__ import annotations

import logging

from ingestion.config import DBConfig
from ingestion.http_utils import get_json
from ingestion.runner import run_extractor
from ingestion.transform import clean_remoteok_job, filter_remoteok_jobs, remoteok_job_id


def run(config: DBConfig | None = None) -> int:
    return run_extractor(
        source="remoteok",
        table="remoteok_jobs",
        fetch=lambda: get_json("https://remoteok.com/api"),
        filter_jobs=filter_remoteok_jobs,
        job_id=remoteok_job_id,
        clean=clean_remoteok_job,  # repairs RemoteOK's double-encoded text
        config=config,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
