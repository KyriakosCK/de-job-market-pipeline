-- Postings to hiring regions. A location can be one place or a list of
-- regions a remote role hires from ("LATAM, Europe, USA"), so each posting
-- gets a row per region whose keyword (seed: region_keywords) appears in
-- it, or one 'Unspecified' row if none does. Word boundaries (\y) keep "us"
-- from matching inside "Russia".
with jobs as (

    select job_id, location from {{ ref('fact_job_postings') }}

),

keywords as (

    select match_keyword, region from {{ ref('region_keywords') }}

),

matched as (

    select distinct
        j.job_id,
        k.region
    from jobs j
    inner join keywords k
        on j.location ~* ('\y' || k.match_keyword || '\y')

)

select job_id, region from matched

union all

select j.job_id, 'Unspecified' as region
from jobs j
where not exists (select 1 from matched m where m.job_id = j.job_id)
