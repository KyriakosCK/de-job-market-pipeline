"""
Small HTTP helper with retry/backoff so a flaky public API doesn't fail an
entire Airflow run over a single dropped connection.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import requests

from ingestion.config import (
    REQUEST_BACKOFF_SECONDS,
    REQUEST_MAX_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
)

logger = logging.getLogger(__name__)


def get_json(url: str, params: dict[str, Any] | None = None) -> Any:
    """GET a URL and return parsed JSON, retrying transient failures.

    Raises the last exception if every attempt fails, so the caller (and
    Airflow) sees a real failure rather than silently returning nothing.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    last_exc: Exception | None = None

    for attempt in range(1, REQUEST_MAX_RETRIES + 1):
        try:
            response = requests.get(
                url, params=params, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            wait = REQUEST_BACKOFF_SECONDS * attempt
            logger.warning(
                "Request to %s failed on attempt %d/%d (%s); retrying in %.1fs",
                url, attempt, REQUEST_MAX_RETRIES, exc, wait,
            )
            if attempt < REQUEST_MAX_RETRIES:
                time.sleep(wait)

    assert last_exc is not None
    raise last_exc
