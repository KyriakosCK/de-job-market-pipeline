-- Active postings per hiring region. A posting open to several regions
-- counts once in each, so postings_count does not sum to the number of
-- active postings; pct_of_active_postings answers "what share of open
-- roles can someone in this region apply to?".
with active as (

    select job_id from {{ ref('fact_job_postings') }} where is_active

),

total as (

    select count(*) as active_postings from active

)

select
    b.region,
    count(*)                                                     as postings_count,
    round(100.0 * count(*) / nullif(max(t.active_postings), 0), 1) as pct_of_active_postings
from {{ ref('bridge_job_region') }} b
inner join active a on a.job_id = b.job_id
cross join total t
group by b.region
order by postings_count desc
