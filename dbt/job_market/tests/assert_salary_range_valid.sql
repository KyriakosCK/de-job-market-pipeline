-- Singular test: whenever both salary bounds are present, max should never
-- be less than min. Returning any row here fails the test.
select job_id, salary_min, salary_max
from {{ ref('fact_job_postings') }}
where salary_min is not null
  and salary_max is not null
  and salary_max < salary_min
