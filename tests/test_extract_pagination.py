"""
Tests the Arbeitnow paginator in isolation by monkeypatching get_json, so no
real HTTP call is made.
"""
from unittest.mock import patch

from ingestion.extract_arbeitnow import _fetch_all_pages


def test_fetch_all_pages_follows_next_link_until_null():
    page1 = {
        "data": [{"slug": "job-1"}, {"slug": "job-2"}],
        "links": {"next": "https://example.com/api?page=2"},
    }
    page2 = {
        "data": [{"slug": "job-3"}],
        "links": {"next": None},
    }

    with patch("ingestion.extract_arbeitnow.get_json", side_effect=[page1, page2]) as mocked:
        jobs = _fetch_all_pages("https://example.com/api?page=1")

    assert [job["slug"] for job in jobs] == ["job-1", "job-2", "job-3"]
    assert mocked.call_count == 2


def test_fetch_all_pages_stops_at_max_pages_guard():
    page = {"data": [{"slug": "job"}], "links": {"next": "https://example.com/api?page=next"}}

    with patch("ingestion.extract_arbeitnow.get_json", return_value=page) as mocked:
        jobs = _fetch_all_pages("https://example.com/api?page=1", max_pages=3)

    assert mocked.call_count == 3
    assert len(jobs) == 3
