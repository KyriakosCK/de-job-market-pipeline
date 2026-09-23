"""
Unit tests for the pure transform functions in ingestion/transform.py.

These run with zero network access and zero database -- exactly the kind
of fast, deterministic test that should run on every commit in CI.
"""
import json
from pathlib import Path

import pytest

from ingestion.transform import (
    arbeitnow_job_id,
    filter_arbeitnow_jobs,
    filter_remoteok_jobs,
    filter_remotive_jobs,
    is_relevant,
    remoteok_job_id,
    remotive_job_id,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def remoteok_sample() -> list[dict]:
    return json.loads((FIXTURES_DIR / "remoteok_sample.json").read_text())


@pytest.fixture
def arbeitnow_sample() -> dict:
    return json.loads((FIXTURES_DIR / "arbeitnow_sample.json").read_text())


@pytest.fixture
def remotive_sample() -> dict:
    return json.loads((FIXTURES_DIR / "remotive_sample.json").read_text())


class TestIsRelevant:
    def test_matches_on_tag(self):
        assert is_relevant("Some Role", "no keywords here", ["python"])

    def test_matches_on_title(self):
        assert is_relevant("Senior Data Engineer", "", [])

    def test_matches_on_description(self):
        assert is_relevant("Generalist", "you will build ETL pipelines daily", [])

    def test_no_match_returns_false(self):
        assert not is_relevant("Sandblaster", "paint and blast metal parts", ["music", "medical"])

    def test_is_case_insensitive(self):
        assert is_relevant("SENIOR DATA ENGINEER", "", [])


class TestRemoteOK:
    def test_job_id_uses_id_field(self):
        assert remoteok_job_id({"id": "123", "slug": "foo"}) == "remoteok_123"

    def test_job_id_falls_back_to_slug(self):
        assert remoteok_job_id({"slug": "foo"}) == "remoteok_foo"

    def test_job_id_raises_without_id_or_slug(self):
        with pytest.raises(ValueError):
            remoteok_job_id({"position": "no ids here"})

    def test_filter_drops_legal_notice_record(self, remoteok_sample):
        filtered = filter_remoteok_jobs(remoteok_sample)
        assert all("id" in job for job in filtered)

    def test_filter_drops_unrelated_jobs(self, remoteok_sample):
        filtered = filter_remoteok_jobs(remoteok_sample)
        titles = {job["position"] for job in filtered}
        assert "Sandblaster" not in titles

    def test_filter_keeps_relevant_jobs(self, remoteok_sample):
        filtered = filter_remoteok_jobs(remoteok_sample)
        titles = {job["position"] for job in filtered}
        assert "Senior Data Engineer" in titles
        assert "Python Backend Engineer" in titles
        assert len(filtered) == 2


class TestArbeitnow:
    def test_job_id_uses_slug(self):
        assert arbeitnow_job_id({"slug": "data-engineer-acme"}) == "arbeitnow_data-engineer-acme"

    def test_job_id_raises_without_slug(self):
        with pytest.raises(ValueError):
            arbeitnow_job_id({"title": "no slug here"})

    def test_filter_drops_unrelated_jobs(self, arbeitnow_sample):
        filtered = filter_arbeitnow_jobs(arbeitnow_sample["data"])
        titles = {job["title"] for job in filtered}
        assert "CNC-Dreher (m/w/d)" not in titles

    def test_filter_keeps_relevant_jobs(self, arbeitnow_sample):
        filtered = filter_arbeitnow_jobs(arbeitnow_sample["data"])
        titles = {job["title"] for job in filtered}
        assert "Data Platform Engineer" in titles
        assert "Junior Analytics Engineer" in titles
        assert len(filtered) == 2


class TestRemotive:
    """Remotive is filtered on the source's own category label rather than
    keyword-matching free text, so these tests pin that behaviour down."""

    def test_job_id_uses_numeric_id(self):
        assert remotive_job_id({"id": 2091097}) == "remotive_2091097"

    def test_job_id_raises_without_id(self):
        with pytest.raises(ValueError):
            remotive_job_id({"title": "no id here"})

    def test_filter_keeps_tech_categories(self, remotive_sample):
        filtered = filter_remotive_jobs(remotive_sample["jobs"])
        titles = {job["title"] for job in filtered}
        assert "Senior Data Engineer" in titles
        assert "Senior Golang Developer" in titles
        assert "Site Reliability Engineer" in titles
        assert len(filtered) == 3

    def test_filter_drops_non_tech_categories(self, remotive_sample):
        filtered = filter_remotive_jobs(remotive_sample["jobs"])
        titles = {job["title"] for job in filtered}
        assert "Head of Marketing & Communications" not in titles
        assert "Freelance Writer" not in titles

    def test_category_beats_keyword_matching(self, remotive_sample):
        """The marketing posting's description mentions "Data-driven
        reporting and ROI" -- exactly the kind of incidental keyword that
        fooled the RemoteOK title/description filter. Category-based
        filtering is immune to it."""
        marketing = next(
            j for j in remotive_sample["jobs"] if j["category"] == "Marketing"
        )
        assert is_relevant(marketing["title"], marketing["description"], marketing["tags"])
        assert filter_remotive_jobs([marketing]) == []
