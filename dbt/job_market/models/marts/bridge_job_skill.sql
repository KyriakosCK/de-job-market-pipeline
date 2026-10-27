-- Postings to skills: a skill matches if its keyword appears in the tags or
-- description. Word boundaries (\y) stop "java" matching "javascript".
-- Keywords go into the regex unescaped, so none may contain metacharacters
-- ("c++", ".net").
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
