-- Incremental fact table: one row per (day, skill), appended each time the
-- Airflow DAG runs `dbt run`. This is what turns a single point-in-time
-- snapshot (mart_skill_demand) into an actual trend line over time.
--
-- A second run on the same day replaces that day's rows through unique_key
-- rather than being skipped, so rerunning after a failed extract corrects
-- the day's numbers instead of keeping the partial ones.
{{
    config(
        materialized='incremental',
        unique_key=['snapshot_date', 'skill_id']
    )
}}

select
    current_date as snapshot_date,
    skill_id,
    skill_name,
    category,
    postings_count,
    pct_of_active_postings
from {{ ref('mart_skill_demand') }}
