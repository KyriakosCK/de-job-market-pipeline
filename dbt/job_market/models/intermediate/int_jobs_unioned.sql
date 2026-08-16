-- Union both sources onto one common grain (one row per posting) so every
-- downstream mart is source-agnostic. Adding a third source later only
-- means adding one more `union all` branch here.
with remoteok as (

    select * from {{ ref('stg_remoteok_jobs') }}

),

arbeitnow as (

    select * from {{ ref('stg_arbeitnow_jobs') }}

),

unioned as (

    select * from remoteok
    union all
    select * from arbeitnow

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
    first_seen_at,
    last_seen_at
from unioned
where title is not null
