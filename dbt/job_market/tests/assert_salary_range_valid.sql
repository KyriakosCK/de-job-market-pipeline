-- salary_max must not be below salary_min.
select job_id, salary_min, salary_max
from {{ ref('fact_job_postings') }}
where salary_min is not null
  and salary_max is not null
  and salary_max < salary_min
