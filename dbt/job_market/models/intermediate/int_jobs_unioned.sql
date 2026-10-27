-- All sources on one grain (one row per posting), so the marts are
-- source-agnostic. The staging models are combined with `select *`, so
-- their column order must match.
with unioned as (

    select * from {{ ref('stg_remoteok_jobs') }}
    union all
    select * from {{ ref('stg_remotive_jobs') }}

),

cleaned as (

    select
        *,
        -- Unrepairable mojibake becomes NULL ("Unspecified"), reported by
        -- tests/assert_no_mojibake_in_text.sql. Trailing separators
        -- ("Curitiba, ") are stripped.
        {{ clean_text("regexp_replace(" ~ null_if_mojibake('location') ~ ", '[,\\s]+$', '')") }} as source_location
    from unioned

)

select
    job_id,
    source,
    trim(title)                        as title,
    {{ clean_text(null_if_mojibake('company_name')) }} as company_name,
    -- Locations sent only in a non-Latin script ("دبي") are translated from
    -- a seed; untranslated ones become NULL and are listed by
    -- tests/assert_locations_translated.sql.
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
left join {{ ref('location_translations') }} t
    on t.source_location = c.source_location
where title is not null
  -- Remotive: trust its own category. RemoteOK has none, so match role
  -- keywords in the title only; descriptions (boilerplate mentions "data")
  -- and the bare words "engineer"/"analyst" let non-tech roles through.
  and (
       source_category in ('Software Development', 'Data and Analytics', 'DevOps / Sysadmin')
    or title ~* 'data|software|developer|analytics|python|sql|etl|airflow|dbt|spark|devops|machine learning|cloud|backend'
  )
