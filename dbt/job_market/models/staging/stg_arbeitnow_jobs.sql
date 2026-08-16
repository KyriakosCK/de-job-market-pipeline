-- Flatten the raw Arbeitnow JSONB payload into typed columns and standardize
-- it onto the common job-posting shape shared with stg_remoteok_jobs.
with source as (

    select * from {{ source('raw', 'arbeitnow_jobs') }}

),

parsed as (

    select
        job_id,
        'arbeitnow'                                         as source,
        payload ->> 'title'                                  as title,
        payload ->> 'company_name'                            as company_name,
        nullif(trim(payload ->> 'location'), '')             as location,
        (payload ->> 'remote')::boolean                      as is_remote,
        (
            select array_agg(lower(trim(tag)))
            from jsonb_array_elements_text(coalesce(payload -> 'tags', '[]'::jsonb)) as tag
        )                                                    as tags,
        payload ->> 'description'                            as description,
        payload ->> 'url'                                     as posting_url,
        -- Arbeitnow doesn't expose salary data.
        cast(null as numeric)                                 as salary_min,
        cast(null as numeric)                                 as salary_max,
        to_timestamp((payload ->> 'created_at')::bigint)      as posted_at,
        first_seen_at,
        last_seen_at
    from source

)

select * from parsed
