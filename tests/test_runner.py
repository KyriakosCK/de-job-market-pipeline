"""
Tests the shared extractor runner with the database layer mocked out, so
no Postgres is needed.
"""
from unittest.mock import MagicMock, patch

import pytest

from ingestion.config import DBConfig
from ingestion.runner import run_extractor

CONFIG = DBConfig("host", 5432, "db", "user", "password")


def _run(fetch, **overrides):
    kwargs = dict(
        source="test",
        table="test_jobs",
        fetch=fetch,
        filter_jobs=lambda jobs: [job for job in jobs if job["keep"]],
        job_id=lambda job: f"test_{job['id']}",
        config=CONFIG,
    )
    kwargs.update(overrides)
    return run_extractor(**kwargs)


@patch("ingestion.runner.db")
def test_success_upserts_filtered_jobs_and_logs_fetched_count(mock_db):
    mock_db.upsert_raw_jobs.side_effect = lambda conn, table, records: len(records)
    jobs = [{"id": 1, "keep": True}, {"id": 2, "keep": False}, {"id": 3, "keep": True}]

    upserted = _run(lambda: jobs, clean=lambda job: {**job, "cleaned": True})

    assert upserted == 2
    records = mock_db.upsert_raw_jobs.call_args.args[2]
    assert [job_id for job_id, _ in records] == ["test_1", "test_3"]
    assert all(payload["cleaned"] for _, payload in records)
    log_args = mock_db.log_run.call_args
    assert log_args.args[1:4] == ("test", 3, 2)
    assert log_args.kwargs["status"] == "success"


@patch("ingestion.runner.db")
def test_failure_after_fetch_logs_fetched_count_and_reraises(mock_db):
    mock_db.get_connection.return_value.__enter__.return_value = MagicMock()
    mock_db.upsert_raw_jobs.side_effect = RuntimeError("db down")

    with pytest.raises(RuntimeError, match="db down"):
        _run(lambda: [{"id": 1, "keep": True}, {"id": 2, "keep": True}])

    log_args = mock_db.log_run.call_args
    assert log_args.args[1:4] == ("test", 2, 0)
    assert log_args.kwargs["status"] == "failed"
    assert log_args.kwargs["error_message"] == "db down"


@patch("ingestion.runner.db")
def test_failure_during_fetch_logs_zero_fetched(mock_db):
    def failing_fetch():
        raise ConnectionError("api down")

    with pytest.raises(ConnectionError):
        _run(failing_fetch)

    assert mock_db.log_run.call_args.args[2] == 0
    assert mock_db.log_run.call_args.kwargs["status"] == "failed"
