"""
SkillScope daily pipeline: pull tech job postings from three public APIs,
model them with dbt, and leave a fresh star schema for the dashboard to
read.

    extract_remoteok  ─┐
    extract_arbeitnow ─┼─▶ dbt_seed ─▶ dbt_run ─▶ dbt_test
    extract_remotive  ─┘

All three extractors write to Postgres independently and can run in
parallel; dbt only starts once they've all finished, since the staging
models read from every raw table.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# The ingestion/ package is mounted at /opt/airflow/ingestion (see
# docker-compose.yml); add its parent to sys.path so `import ingestion` works
# the same way it does when running `python -m ingestion.extract_remoteok`
# locally, with no code changes between the two environments.
sys.path.insert(0, "/opt/airflow")

from ingestion import extract_arbeitnow, extract_remoteok, extract_remotive  # noqa: E402

DBT_PROJECT_DIR = "/opt/airflow/dbt/job_market"
DBT_PROFILES_DIR = "/opt/airflow/dbt/job_market"

default_args = {
    "owner": "data-eng",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "depends_on_past": False,
}

with DAG(
    dag_id="job_market_pipeline",
    description="Extract job postings from RemoteOK + Arbeitnow, model with dbt, test, done.",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["skillscope", "elt", "portfolio"],
    doc_md=__doc__,
) as dag:

    extract_remoteok_task = PythonOperator(
        task_id="extract_remoteok",
        python_callable=extract_remoteok.run,
        doc_md="Fetch postings from https://remoteok.com/api and upsert into raw.remoteok_jobs.",
    )

    extract_arbeitnow_task = PythonOperator(
        task_id="extract_arbeitnow",
        python_callable=extract_arbeitnow.run,
        doc_md="Fetch postings (paginated) from the Arbeitnow API and upsert into raw.arbeitnow_jobs.",
    )

    extract_remotive_task = PythonOperator(
        task_id="extract_remotive",
        python_callable=extract_remotive.run,
        doc_md=(
            "Fetch postings from https://remotive.com/api/remote-jobs and upsert the "
            "tech-category ones into raw.remotive_jobs. Remotive asks for no more than "
            "~4 calls/day, which this @daily schedule stays well inside."
        ),
    )

    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"dbt seed --profiles-dir {DBT_PROFILES_DIR}"
        ),
        doc_md="Load/refresh the skill_keywords reference seed.",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"dbt run --profiles-dir {DBT_PROFILES_DIR}"
        ),
        doc_md="Build staging -> intermediate -> mart models (star schema + incremental daily snapshot).",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"dbt test --profiles-dir {DBT_PROFILES_DIR}"
        ),
        doc_md="Run schema + singular tests; fails the DAG run if data quality regresses.",
    )

    [
        extract_remoteok_task,
        extract_arbeitnow_task,
        extract_remotive_task,
    ] >> dbt_seed >> dbt_run >> dbt_test
