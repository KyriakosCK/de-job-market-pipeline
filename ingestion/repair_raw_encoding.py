"""
One-off backfill: apply transform.clean_remoteok_job to RemoteOK payloads
that were landed before ingestion started repairing them.

Run directly:
    python -m ingestion.repair_raw_encoding --dry-run   # report only
    python -m ingestion.repair_raw_encoding             # apply

Idempotent: clean_remoteok_job is a no-op on already-clean payloads, so
only rows whose payload actually changes are updated, and a second run
updates nothing. Postings that are still live get repaired on their own
by the next extract (the upsert overwrites the payload); this script is
for the ones that have since dropped out of the feed.
"""
from __future__ import annotations

import argparse
import json
import logging

from ingestion import db
from ingestion.config import DBConfig
from ingestion.transform import clean_remoteok_job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run(config: DBConfig | None = None, dry_run: bool = False) -> int:
    """Repair raw.remoteok_jobs in place. Returns the number of rows changed."""
    config = config or DBConfig.from_env()

    with db.get_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute("select job_id, payload from raw.remoteok_jobs")
            rows = cur.fetchall()

        changed = []
        for job_id, payload in rows:
            cleaned = clean_remoteok_job(payload)
            if cleaned != payload:
                changed.append((job_id, payload, cleaned))

        for job_id, before, after in changed[:5]:
            logger.info(
                "%s location: %r -> %r", job_id, before.get("location"), after.get("location")
            )
        logger.info("%d of %d RemoteOK payloads need repair", len(changed), len(rows))

        if dry_run or not changed:
            return len(changed)

        # last_seen_at is deliberately left alone: this fixes the stored
        # text, it isn't evidence the posting is still live.
        with conn.cursor() as cur:
            cur.executemany(
                "update raw.remoteok_jobs set payload = %s::jsonb where job_id = %s",
                [(json.dumps(after), job_id) for job_id, _, after in changed],
            )
        logger.info("Repaired %d rows in raw.remoteok_jobs", len(changed))
        return len(changed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="report without writing")
    run(dry_run=parser.parse_args().dry_run)
