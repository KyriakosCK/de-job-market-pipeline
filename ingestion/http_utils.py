"""GET with retry/backoff, so one dropped connection doesn't fail a whole run."""
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


def get_json(url: str) -> Any:
    """GET a URL and return parsed JSON. Raises the last error if every attempt fails."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    for attempt in range(1, REQUEST_MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == REQUEST_MAX_RETRIES:
                raise
            wait = REQUEST_BACKOFF_SECONDS * attempt
            logger.warning(
                "Request to %s failed on attempt %d/%d (%s); retrying in %.1fs",
                url, attempt, REQUEST_MAX_RETRIES, exc, wait,
            )
            time.sleep(wait)
