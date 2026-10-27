"""Pure functions that shape raw API payloads before they're landed (no I/O)."""
from __future__ import annotations

import html
import re
from typing import Any

from ingestion.config import RELEVANT_KEYWORDS, REMOTIVE_TECH_CATEGORIES

# UTF-8 text wrongly decoded as Latin-1 ("mojibake") turns each non-ASCII
# character into a run of U+0080-U+00FF characters: "دبي" arrives as
# "Ø¯Ø¨Ù\x8a", "Macaé" as "MacaÃ©".
_LATIN1_RUN_RE = re.compile(r"[\u0080-ÿ]+")

# RemoteOK fields that arrive HTML-escaped ("Localiza&amp;Co"). The
# description is real HTML and is left alone.
_REMOTEOK_PLAIN_TEXT_FIELDS = ("position", "company", "location")


def _decode_run(match: re.Match[str]) -> str:
    run = match.group(0)
    try:
        return run.encode("latin-1").decode("utf-8")
    except UnicodeDecodeError:
        return run  # a genuine "é" or "ü", not mojibake


def repair_mojibake(text: str) -> str:
    """Undo UTF-8-read-as-Latin-1 corruption, leaving clean text untouched.

    RemoteOK double-encodes non-ASCII text at the source. Each Latin-1 run
    is repaired on its own, so mixed clean/corrupted strings are fixed and
    runs that aren't valid UTF-8 are kept. The loop handles text encoded
    more than once; on clean text this is a no-op.
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
    """Fix RemoteOK's text defects before landing.

    The only place ingestion changes payload content: the corruption is a
    source defect, and undoing it in SQL would fail on any string that
    isn't valid UTF-8.
    """
    job = repair_payload_text(raw_job)
    for field in _REMOTEOK_PLAIN_TEXT_FIELDS:
        if isinstance(job.get(field), str):
            job[field] = html.unescape(job[field])
    return job


def is_relevant(title: str, description: str, tags: list[str]) -> bool:
    """Keyword filter for RemoteOK, which mixes every industry and has no category."""
    haystack = " ".join([title or "", " ".join(tags or []), description or ""]).lower()
    return any(keyword in haystack for keyword in RELEVANT_KEYWORDS)


def remoteok_job_id(raw_job: dict) -> str:
    job_id = raw_job.get("id") or raw_job.get("slug")
    if not job_id:
        raise ValueError("RemoteOK job payload missing both 'id' and 'slug'")
    return f"remoteok_{job_id}"


def remotive_job_id(raw_job: dict) -> str:
    job_id = raw_job.get("id")
    if not job_id:
        raise ValueError("Remotive job payload missing 'id'")
    return f"remotive_{job_id}"


def filter_remoteok_jobs(raw_jobs: list[dict]) -> list[dict]:
    """Drop RemoteOK's leading legal-notice record and irrelevant postings."""
    return [
        job for job in raw_jobs
        if ("id" in job or "slug" in job)
        and is_relevant(job.get("position", ""), job.get("description", ""), job.get("tags", []))
    ]


def filter_remotive_jobs(raw_jobs: list[dict]) -> list[dict]:
    """Keep Remotive postings by the source's own category label.

    Not is_relevant(): keyword matching free text let a Fire Fighter through
    on one "data" in its GDPR boilerplate.
    """
    return [job for job in raw_jobs if job.get("category") in REMOTIVE_TECH_CATEGORIES]
