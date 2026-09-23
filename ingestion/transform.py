"""
Pure functions for shaping raw API payloads before they hit Postgres.

Kept separate from db.py / the extract_*.py entrypoints on purpose: pure
functions with no I/O are trivial to unit test (see tests/test_transform.py),
which is exactly the part of an ingestion job that's worth covering --
the parts that silently produce wrong data instead of loudly failing.
"""
from __future__ import annotations

import html
import re
from typing import Any

from ingestion.config import RELEVANT_KEYWORDS, REMOTIVE_TECH_CATEGORIES

# A run of characters from the Latin-1 range (U+0080-U+00FF). Text that was
# UTF-8 encoded and then wrongly decoded as Latin-1 ("mojibake") turns every
# non-ASCII character into exactly such a run: "دبي" arrives as "Ø¯Ø¨Ù\x8a",
# "Macaé" as "MacaÃ©".
_LATIN1_RUN_RE = re.compile(r"[\u0080-ÿ]+")

# Short, human-facing RemoteOK fields that arrive HTML-escaped
# ("Localiza&amp;Co"). The description is real HTML and is left alone.
_REMOTEOK_PLAIN_TEXT_FIELDS = ("position", "company", "location")


def _decode_run(match: re.Match[str]) -> str:
    run = match.group(0)
    try:
        return run.encode("latin-1").decode("utf-8")
    except UnicodeDecodeError:
        # Not valid UTF-8 once re-encoded, so it was never mojibake: a
        # genuine "é" or "ü" on its own. Leave it exactly as it was.
        return run


def repair_mojibake(text: str) -> str:
    """Undo UTF-8-read-as-Latin-1 corruption, leaving clean text untouched.

    RemoteOK's API double-encodes non-ASCII text at the source (verified
    against the raw response bytes, so it isn't a client-side decoding bug
    we could fix in http_utils). Each Latin-1 run is repaired on its own,
    which means a string mixing clean and corrupted text is still fixed,
    and a run that doesn't decode as UTF-8 is kept verbatim. The loop covers
    text that was double-encoded more than once; repairing clean text is a
    no-op, so the function is idempotent.
    """
    for _ in range(3):
        repaired = _LATIN1_RUN_RE.sub(_decode_run, text)
        if repaired == text:
            break
        text = repaired
    return text


def repair_payload_text(value: Any) -> Any:
    """Apply repair_mojibake to every string anywhere in a JSON payload."""
    if isinstance(value, str):
        return repair_mojibake(value)
    if isinstance(value, list):
        return [repair_payload_text(item) for item in value]
    if isinstance(value, dict):
        return {key: repair_payload_text(item) for key, item in value.items()}
    return value


def clean_remoteok_job(raw_job: dict) -> dict:
    """Fix RemoteOK's known upstream text defects before the job is landed.

    This is the one place ingestion changes a payload's content rather than
    landing it verbatim. That's deliberate: the corruption is a defect in
    the source, no downstream consumer wants it, and it can't be reversed
    in SQL without risking a failed dbt run on the odd string that isn't
    valid UTF-8. Doing it here keeps the fix in a pure, unit-tested
    function.
    """
    job = repair_payload_text(raw_job)
    for field in _REMOTEOK_PLAIN_TEXT_FIELDS:
        if isinstance(job.get(field), str):
            job[field] = html.unescape(job[field])
    return job


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


def remotive_job_id(raw_job: dict) -> str:
    job_id = raw_job.get("id")
    if not job_id:
        raise ValueError("Remotive job payload missing 'id'")
    return f"remotive_{job_id}"


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


def filter_remotive_jobs(raw_jobs: list[dict]) -> list[dict]:
    """Filter Remotive postings on the source's own category label.

    Deliberately *not* using is_relevant() here. Remotive classifies every
    posting itself ("Software Development", "Marketing", "Writing", ...), and
    trusting that structured label beats guessing from free text -- which is
    what let a Fire Fighter and an Accounts Receivable Clerk through the
    RemoteOK filter, on the strength of one "data" in their GDPR boilerplate.
    """
    return [job for job in raw_jobs if job.get("category") in REMOTIVE_TECH_CATEGORIES]
