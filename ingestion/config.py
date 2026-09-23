"""
Centralized configuration for the ingestion layer.

Everything is read from environment variables so the exact same code runs
unchanged whether it's invoked locally with a .env file, inside an Airflow
task, or inside a CI job -- only the environment differs, never the code.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise EnvironmentError(f"Required environment variable '{name}' is not set")
    return value or ""


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    database: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "DBConfig":
        return cls(
            host=_env("WAREHOUSE_HOST", "localhost"),
            port=int(_env("WAREHOUSE_PORT", "5432")),
            database=_env("WAREHOUSE_DB", "warehouse"),
            user=_env("WAREHOUSE_USER", "jobmarket"),
            password=_env("WAREHOUSE_PASSWORD", "jobmarket"),
        )

    @property
    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.database} "
            f"user={self.user} password={self.password}"
        )


# HTTP settings shared by every extractor.
REQUEST_TIMEOUT_SECONDS = int(_env("REQUEST_TIMEOUT_SECONDS", "30"))
REQUEST_MAX_RETRIES = int(_env("REQUEST_MAX_RETRIES", "3"))
REQUEST_BACKOFF_SECONDS = float(_env("REQUEST_BACKOFF_SECONDS", "2"))
USER_AGENT = _env(
    "SKILLSCOPE_USER_AGENT",
    "SkillScope-DataPipeline/1.0 (+https://github.com/KyriakosCK/de-job-market-pipeline)",
)

# Only postings whose title/description/tags mention at least one of these
# keywords are kept. This keeps the warehouse focused on data/software roles
# instead of the full firehose of every job category the source APIs carry.
RELEVANT_KEYWORDS = [
    "data", "engineer", "engineering", "analytics", "analyst", "python",
    "sql", "etl", "elt", "warehouse", "pipeline", "airflow", "dbt", "spark",
    "kafka", "cloud", "aws", "gcp", "azure", "machine learning", "ml ",
    "backend", "software", "devops", "platform",
]

# Remotive labels every posting with its own category, which is a far more
# reliable relevance signal than keyword-matching free text. These are the
# categories treated as in-scope for a data/software job market analysis.
# Kept in sync with the same list in int_jobs_unioned.sql.
REMOTIVE_TECH_CATEGORIES = {
    "Software Development",
    "Data and Analytics",
    "DevOps / Sysadmin",
}
