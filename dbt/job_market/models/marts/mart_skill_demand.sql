-- One row per skill: how many active postings mention it, and what share
-- of all active postings that represents. Powers the dashboard's
-- "most in-demand skills" chart.
with active_jobs as (

    select job_id from {{ ref('fact_job_postings') }} where is_active

),

bridge as (

    select b.job_id, b.skill_id
    from {{ ref('bridge_job_skill') }} b
    inner join active_jobs a on a.job_id = b.job_id

),

skill_counts as (

    select
        skill_id,
        count(distinct job_id) as postings_count
    from bridge
    group by skill_id

),

total as (

    select count(*) as total_active_postings from active_jobs

)

select
    s.skill_id,
    s.skill_name,
    s.category,
    coalesce(sc.postings_count, 0)                                        as postings_count,
    round(
        100.0 * coalesce(sc.postings_count, 0) / nullif(t.total_active_postings, 0), 2
    )                                                                      as pct_of_active_postings
from {{ ref('dim_skill') }} s
left join skill_counts sc on sc.skill_id = s.skill_id
cross join total t
order by postings_count desc
