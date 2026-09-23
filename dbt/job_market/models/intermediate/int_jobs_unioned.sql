-- Union every source onto one common grain (one row per posting) so every
-- downstream mart is source-agnostic. Adding a fourth source later only
-- means adding one more `union all` branch here.
--
-- NOTE: the staging models are combined with `select *`, so their column
-- order has to stay identical. Adding a column to one means adding it in
-- the same position in all of them.
with remoteok as (

    select * from {{ ref('stg_remoteok_jobs') }}

),

arbeitnow as (

    select * from {{ ref('stg_arbeitnow_jobs') }}

),

remotive as (

    select * from {{ ref('stg_remotive_jobs') }}

),

unioned as (

    select * from remoteok
    union all
    select * from arbeitnow
    union all
    select * from remotive

)

select
    job_id,
    source,
    trim(title)                        as title,
    {{ clean_text('company_name') }}   as company_name,
    {{ clean_text('location') }}       as location,
    coalesce(is_remote, false)         as is_remote,
    tags,
    description,
    posting_url,
    salary_min,
    salary_max,
    posted_at,
    source_category,
    first_seen_at,
    last_seen_at
from unioned
where title is not null
  -- Relevance is decided two different ways, depending on what the source
  -- actually gives us:
  --
  --   * Remotive labels every posting with its own category, so we trust
  --     that structured label directly.
  --   * RemoteOK and Arbeitnow publish no usable category, so we fall back
  --     to matching role keywords against the TITLE only. Matching the
  --     description instead is what originally let "Fire Fighter" and
  --     "Accounts Receivable Clerk" through -- almost every posting's
  --     boilerplate mentions "data" or "software" somewhere.
  --
  --   The bare words "engineer" and "analyst" are deliberately absent: they
  --   matched drilling, maritime, construction and compliance roles. Real
  --   tech titles still qualify via "data", "software", or "developer".
  and (
       source_category in ('Software Development', 'Data and Analytics', 'DevOps / Sysadmin')
    or title ilike '%data%'
    or title ilike '%software%'
    or title ilike '%developer%'
    or title ilike '%analytics%'
    or title ilike '%python%'
    or title ilike '%sql%'
    or title ilike '%etl%'
    or title ilike '%airflow%'
    or title ilike '%dbt%'
    or title ilike '%spark%'
    or title ilike '%devops%'
    or title ilike '%machine learning%'
    or title ilike '%cloud%'
    or title ilike '%backend%'
  )
