-- Many-to-many bridge between job postings and broad hiring regions.
--
-- A posting's location can be one place ("Redwood City") or a list of
-- regions a remote role hires from ("LATAM, Europe, USA, Canada, APAC").
-- Counting raw strings splits one region across many rows, so each posting
-- is mapped to every region whose keyword appears in its location (seed:
-- region_keywords). A posting open to three regions gets three rows.
--
-- Postings with no location, or one no keyword matches ("Remote"), get a
-- single 'Unspecified' row, so every posting appears here at least once.
-- tests/assert_locations_have_region.sql lists locations that fell through
-- so the seed can be extended.
--
-- Word-boundary matching (\y), as in bridge_job_skill, keeps "us" from
-- matching inside "Russia" or "Belarus".
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
