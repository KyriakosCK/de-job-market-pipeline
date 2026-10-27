-- One row per skill: how many active postings mention it and their share of
-- all active postings, plus the same over every posting ever seen.
with jobs as (

    select job_id, is_active from {{ ref('fact_job_postings') }}

),

skill_counts as (

    select
        b.skill_id,
        count(distinct b.job_id) filter (where j.is_active) as postings_count,
        count(distinct b.job_id)                            as all_time_postings_count
    from {{ ref('bridge_job_skill') }} b
    inner join jobs j on j.job_id = b.job_id
    group by b.skill_id

),

totals as (

    select
        count(*) filter (where is_active) as active_postings,
        count(*)                          as all_postings
    from jobs

)

select
    s.skill_id,
    s.skill_name,
    s.category,
    coalesce(sc.postings_count, 0)                                                    as postings_count,
    round(100.0 * coalesce(sc.postings_count, 0) / nullif(t.active_postings, 0), 2)  as pct_of_active_postings,
    coalesce(sc.all_time_postings_count, 0)                                           as all_time_postings_count,
    round(100.0 * coalesce(sc.all_time_postings_count, 0) / nullif(t.all_postings, 0), 2) as pct_of_all_postings
from {{ ref('dim_skill') }} s
left join skill_counts sc on sc.skill_id = s.skill_id
cross join totals t
order by all_time_postings_count desc
