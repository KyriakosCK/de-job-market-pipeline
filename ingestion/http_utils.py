"""
Small HTTP helper with retry/backoff so a flaky public API doesn't fail an
entire Airflow run over a single dropped connection.
"""
from __future__ import annotations

import logging
import re
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

# A source that passes credentials as query params can have them echoed
# back by `requests` into exception messages (e.g. "... for url: https://...
# ?app_key=xxxx"). Redact known-sensitive param values before anything
# touches the logs.
_SENSITIVE_PARAM_RE = re.compile(
    r"(?i)(app_id|app_key|api_key|apikey|token|secret|password)=[^&\s]+"
)


def _redact(text: str) -> str:
    return _SENSITIVE_PARAM_RE.sub(r"\1=REDACTED", text)


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
                url, attempt, REQUEST_MAX_RETRIES, _redact(str(exc)), wait,
            )
            if attempt < REQUEST_MAX_RETRIES:
                time.sleep(wait)

    assert last_exc is not None
    # Re-raise with a redacted message (rather than the raw exception) so a
    # caller's own logging/error-message handling -- e.g. an extractor's
    # logger.exception() and raw.load_runs.error_message -- can't leak
    # credentials embedded in the request URL either.
    try:
        raise type(last_exc)(_redact(str(last_exc))) from None
    except TypeError:
        raise last_exc from None
