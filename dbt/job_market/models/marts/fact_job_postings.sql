with jobs as (

    select * from {{ ref('int_jobs_unioned') }}

),

companies as (

    select * from {{ ref('dim_company') }}

)

select
    j.job_id,
    c.company_id,
    j.source,
    j.title,
    j.location,
    j.is_remote,
    j.salary_min,
    j.salary_max,
    j.posted_at,
    j.posting_url,
    j.first_seen_at,
    j.last_seen_at,
    -- "still active" = the last ingestion run still saw this posting live,
    -- within the freshness window configured in dbt_project.yml vars.
    j.last_seen_at >= (current_timestamp - (
        {{ var('active_posting_window_days') }} || ' days'
    )::interval) as is_active
from jobs j
left join companies c on c.company_name = j.company_name
