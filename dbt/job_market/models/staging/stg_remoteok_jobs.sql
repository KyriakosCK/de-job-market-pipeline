-- Flatten the raw RemoteOK JSONB payload into typed columns and standardize
-- it onto the common job-posting shape shared with stg_arbeitnow_jobs.
with source as (

    select * from {{ source('raw', 'remoteok_jobs') }}

),

parsed as (

    select
        job_id,
        'remoteok'                                          as source,
        payload ->> 'position'                              as title,
        payload ->> 'company'                                as company_name,
        nullif(trim(payload ->> 'location'), '')             as location,
        (payload ->> 'location') ilike '%remote%'             as is_remote,
        (
            select array_agg(lower(trim(tag)))
            from jsonb_array_elements_text(coalesce(payload -> 'tags', '[]'::jsonb)) as tag
        )                                                    as tags,
        payload ->> 'description'                            as description,
        payload ->> 'url'                                     as posting_url,
        nullif(payload ->> 'salary_min', '0')::numeric        as salary_min,
        nullif(payload ->> 'salary_max', '0')::numeric        as salary_max,
        to_timestamp((payload ->> 'epoch')::bigint)           as posted_at,
        -- RemoteOK publishes no usable job category, so relevance for this
        -- source falls back to title matching in int_jobs_unioned.
        cast(null as text)                                    as source_category,
        first_seen_at,
        last_seen_at
    from source

)

select * from parsed
