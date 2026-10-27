"""
SkillScope daily pipeline: land postings from two public APIs, then build
and test the dbt models the dashboard reads.

    extract_remoteok ─┬─▶ dbt_build (seed, run, test)
    extract_remotive ─┘

dbt waits for both extractors, since staging reads every raw table.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# ingestion/ is mounted at /opt/airflow/ingestion (see docker-compose.yml).
sys.path.insert(0, "/opt/airflow")

from ingestion import extract_remoteok, extract_remotive  # noqa: E402

DBT_PROJECT_DIR = "/opt/airflow/dbt/job_market"

with DAG(
    dag_id="job_market_pipeline",
    description="Extract job postings from RemoteOK and Remotive, then dbt build.",
    default_args={"owner": "data-eng", "retries": 2, "retry_delay": timedelta(minutes=5)},
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["skillscope", "elt"],
    doc_md=__doc__,
) as dag:
    extract_remoteok_task = PythonOperator(
        task_id="extract_remoteok",
        python_callable=extract_remoteok.run,
    )
    extract_remotive_task = PythonOperator(
        task_id="extract_remotive",
        python_callable=extract_remotive.run,
    )
    # Tests run before downstream models, so a failing test stops bad data
    # reaching the marts.
    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt build --profiles-dir {DBT_PROJECT_DIR}",
    )

    [extract_remoteok_task, extract_remotive_task] >> dbt_build
