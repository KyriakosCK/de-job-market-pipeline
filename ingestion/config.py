"""Ingestion settings. Connection details come from the environment, so the
same code runs locally, in Airflow, and in CI."""
from __future__ import annotations

import os
from dataclasses import dataclass


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
            host=os.environ.get("WAREHOUSE_HOST", "localhost"),
            port=int(os.environ.get("WAREHOUSE_PORT", "5432")),
            database=os.environ.get("WAREHOUSE_DB", "warehouse"),
            user=os.environ.get("WAREHOUSE_USER", "jobmarket"),
            password=os.environ.get("WAREHOUSE_PASSWORD", "jobmarket"),
        )

    @property
    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} dbname={self.database} "
            f"user={self.user} password={self.password}"
        )


REQUEST_TIMEOUT_SECONDS = 30
REQUEST_MAX_RETRIES = 3
REQUEST_BACKOFF_SECONDS = 2.0
USER_AGENT = "SkillScope-DataPipeline/1.0 (+https://github.com/KyriakosCK/de-job-market-pipeline)"

# RemoteOK postings are kept only if their title, tags or description
# mention one of these.
RELEVANT_KEYWORDS = [
    "data", "engineer", "engineering", "analytics", "analyst", "python",
    "sql", "etl", "elt", "warehouse", "pipeline", "airflow", "dbt", "spark",
    "kafka", "cloud", "aws", "gcp", "azure", "machine learning", "ml ",
    "backend", "software", "devops", "platform",
]

# Remotive labels each posting with a category; these are the in-scope ones.
# Kept in sync with the same list in int_jobs_unioned.sql.
REMOTIVE_TECH_CATEGORIES = {
    "Software Development",
    "Data and Analytics",
    "DevOps / Sysadmin",
}
