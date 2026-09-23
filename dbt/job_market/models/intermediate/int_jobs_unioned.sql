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

),

cleaned as (

    select
        *,
        -- Anything ingestion couldn't repair becomes NULL ("Unspecified" in
        -- the marts) rather than garbage; tests/assert_no_mojibake_in_text.sql
        -- reports how often that happens. RemoteOK also leaves a dangling
        -- separator when a city has no region ("Curitiba, "), so trailing
        -- commas are stripped too.
        {{ clean_text("regexp_replace(" ~ null_if_mojibake('location') ~ ", '[,\\s]+$', '')") }} as source_location
    from unioned

),

-- RemoteOK sends some locations only in the local script ("دبي" for Dubai).
-- Known ones are translated from a hand-maintained seed.
location_translations as (

    select * from {{ ref('location_translations') }}

)

select
    job_id,
    source,
    trim(title)                        as title,
    {{ clean_text(null_if_mojibake('company_name')) }} as company_name,
    -- Untranslated non-Latin locations become NULL ("Unspecified") rather
    -- than an unreadable value on an English dashboard;
    -- tests/assert_locations_translated.sql lists them so the seed can be
    -- extended.
    case
        when t.location_en is not null then t.location_en
        when {{ is_non_latin('c.source_location') }} then null
        else c.source_location
    end                                as location,
    c.source_location,
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
from cleaned c
left join location_translations t
    on t.source_location = c.source_location
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
