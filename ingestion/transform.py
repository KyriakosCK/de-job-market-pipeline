"""
Pure functions for shaping raw API payloads before they hit Postgres.

Kept separate from db.py / the extract_*.py entrypoints on purpose: pure
functions with no I/O are trivial to unit test (see tests/test_transform.py),
which is exactly the part of an ingestion job that's worth covering --
the parts that silently produce wrong data instead of loudly failing.
"""
from __future__ import annotations

from ingestion.config import RELEVANT_KEYWORDS


def is_relevant(title: str, description: str, tags: list[str]) -> bool:
    """Keep only postings that plausibly belong to data/software roles.

    Both source APIs return postings from every job category (a sandblaster
    role shows up in RemoteOK's feed right next to a data engineer role), so
    we filter on keywords across title + tags + description rather than
    trusting either source's own category labels.
    """
    haystack = " ".join([title or "", " ".join(tags or []), description or ""]).lower()
    return any(keyword in haystack for keyword in RELEVANT_KEYWORDS)


def remoteok_job_id(raw_job: dict) -> str:
    job_id = raw_job.get("id") or raw_job.get("slug")
    if not job_id:
        raise ValueError("RemoteOK job payload missing both 'id' and 'slug'")
    return f"remoteok_{job_id}"


def arbeitnow_job_id(raw_job: dict) -> str:
    slug = raw_job.get("slug")
    if not slug:
        raise ValueError("Arbeitnow job payload missing 'slug'")
    return f"arbeitnow_{slug}"


def filter_remoteok_jobs(raw_jobs: list[dict]) -> list[dict]:
    """RemoteOK's feed starts with a non-job 'legal notice' record and mixes
    in postings from unrelated industries -- filter both out.
    """
    relevant = []
    for job in raw_jobs:
        if "id" not in job and "slug" not in job:
            continue  # the legal-notice / metadata record
        if is_relevant(
            job.get("position", ""), job.get("description", ""), job.get("tags", [])
        ):
            relevant.append(job)
    return relevant


def filter_arbeitnow_jobs(raw_jobs: list[dict]) -> list[dict]:
    relevant = []
    for job in raw_jobs:
        if is_relevant(
            job.get("title", ""), job.get("description", ""), job.get("tags", [])
        ):
            relevant.append(job)
    return relevant
