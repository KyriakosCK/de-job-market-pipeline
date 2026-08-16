-- Many-to-many bridge between job postings and the skill taxonomy.
-- A skill is attached to a posting if its match_keyword appears either in
-- the posting's own tags or in its free-text description.
with jobs as (

    select job_id, tags, description from {{ ref('int_jobs_unioned') }}

),

skills as (

    select skill_id, match_keyword from {{ ref('dim_skill') }}

)

select
    j.job_id,
    s.skill_id
from jobs j
cross join skills s
where
    lower(coalesce(j.description, '')) like '%' || s.match_keyword || '%'
    or exists (
        select 1
        from unnest(coalesce(j.tags, array[]::text[])) as tag
        where tag like '%' || s.match_keyword || '%'
    )
