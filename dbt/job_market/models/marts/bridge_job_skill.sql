-- Many-to-many bridge between job postings and the skill taxonomy.
-- A skill is attached to a posting if its match_keyword appears either in
-- the posting's own tags or in its free-text description.
-- Matching is word-boundary based (regex \y, not substring LIKE) because
-- substring matching produced false positives: "api" inside "rapid",
-- "java" inside "javascript", "elt" inside "svelte". Note match_keyword is
-- interpolated into the regex pattern unescaped, so this would break if a
-- keyword ever contained regex metacharacters (e.g. "c++", ".net") -- not
-- an issue for the current seed list, but worth knowing before adding one.
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
    j.description ~* ('\y' || s.match_keyword || '\y')
    or exists (
        select 1
        from unnest(coalesce(j.tags, array[]::text[])) as tag
        where tag ~* ('\y' || s.match_keyword || '\y')
    )
