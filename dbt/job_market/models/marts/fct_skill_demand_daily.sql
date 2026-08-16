-- Incremental fact table: one row per (day, skill), appended each time the
-- Airflow DAG runs `dbt run`. This is what turns a single point-in-time
-- snapshot (mart_skill_demand) into an actual trend line over time.
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

{% if is_incremental() %}
    where current_date not in (select distinct snapshot_date from {{ this }})
{% endif %}
