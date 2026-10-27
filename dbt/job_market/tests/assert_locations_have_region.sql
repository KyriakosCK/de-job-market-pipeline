-- Locations no region keyword matched, i.e. candidates for
-- seeds/region_keywords.csv. A bare "Remote"/"Remoto" is expected and skipped.
{{ config(severity='warn') }}

select distinct f.location
from {{ ref('bridge_job_region') }} b
inner join {{ ref('fact_job_postings') }} f on f.job_id = b.job_id
where b.region = 'Unspecified'
  and f.location is not null
  and f.location !~* '^remot[eo]$'
