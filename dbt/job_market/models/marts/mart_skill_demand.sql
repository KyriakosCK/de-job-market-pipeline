-- One row per skill: how many active postings mention it (and what share
-- of active postings that represents), alongside the same counts across
-- all postings ever seen, active or not. Powers the dashboard's
-- "most in-demand skills" chart.
with active_jobs as (

    select job_id from {{ ref('fact_job_postings') }} where is_active

),

all_jobs as (

    select job_id from {{ ref('fact_job_postings') }}

),

bridge as (

    select b.job_id, b.skill_id
    from {{ ref('bridge_job_skill') }} b
    inner join active_jobs a on a.job_id = b.job_id

),

all_bridge as (

    select b.job_id, b.skill_id
    from {{ ref('bridge_job_skill') }} b
    inner join all_jobs a on a.job_id = b.job_id

),

skill_counts as (

    select
        skill_id,
        count(distinct job_id) as postings_count
    from bridge
    group by skill_id

),

all_skill_counts as (

    select
        skill_id,
        count(distinct job_id) as all_time_postings_count
    from all_bridge
    group by skill_id

),

total as (

    select count(*) as total_active_postings from active_jobs

),

all_total as (

    select count(*) as total_all_postings from all_jobs

)

select
    s.skill_id,
    s.skill_name,
    s.category,
    coalesce(sc.postings_count, 0)                                        as postings_count,
    round(
        100.0 * coalesce(sc.postings_count, 0) / nullif(t.total_active_postings, 0), 2
    )                                                                      as pct_of_active_postings,
    coalesce(asc_.all_time_postings_count, 0)                             as all_time_postings_count,
    round(
        100.0 * coalesce(asc_.all_time_postings_count, 0) / nullif(at_.total_all_postings, 0), 2
    )                                                                      as pct_of_all_postings
from {{ ref('dim_skill') }} s
left join skill_counts sc on sc.skill_id = s.skill_id
left join all_skill_counts asc_ on asc_.skill_id = s.skill_id
cross join total t
cross join all_total at_
order by all_time_postings_count desc
