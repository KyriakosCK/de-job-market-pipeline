-- One row per (day, skill), appended each run: the history behind the
-- trend chart. A same-day rerun replaces that day's rows via unique_key.
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
