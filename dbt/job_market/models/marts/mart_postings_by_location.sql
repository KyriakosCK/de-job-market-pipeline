select
    coalesce(location, 'Unspecified') as location,
    count(*)                          as postings_count,
    count(*) filter (where is_remote) as remote_postings_count,
    round(avg(salary_min), 0)         as avg_salary_min,
    round(avg(salary_max), 0)         as avg_salary_max
from {{ ref('fact_job_postings') }}
where is_active
group by 1
order by postings_count desc
