-- Singular test: lists locations that bridge_job_region couldn't map to
-- any region, so they're counted as 'Unspecified'. Each row is a keyword
-- to consider adding to seeds/region_keywords.csv. A bare "Remote" (or
-- Spanish "Remoto") says nothing about region, so it's expected here and
-- excluded.
{{ config(severity='warn') }}

select distinct f.location
from {{ ref('bridge_job_region') }} b
inner join {{ ref('fact_job_postings') }} f on f.job_id = b.job_id
where b.region = 'Unspecified'
  and f.location is not null
  and f.location !~* '^remot[eo]$'
