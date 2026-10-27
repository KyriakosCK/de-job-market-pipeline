-- Flatten raw Remotive payloads onto the common posting shape. Column order
-- must match stg_remoteok_jobs (int_jobs_unioned uses `select *`).
with source as (

    select * from {{ source('raw', 'remotive_jobs') }}

),

parsed as (

    select
        job_id,
        'remotive'                                                    as source,
        payload ->> 'title'                                           as title,
        payload ->> 'company_name'                                    as company_name,
        nullif(trim(payload ->> 'candidate_required_location'), '')   as location,
        true                                                          as is_remote,
        (
            select array_agg(lower(trim(tag)))
            from jsonb_array_elements_text(coalesce(payload -> 'tags', '[]'::jsonb)) as tag
        )                                                             as tags,
        payload ->> 'description'                                     as description,
        payload ->> 'url'                                              as posting_url,
        -- Salary is free text ("$120 - $170 /hour", "Pay per task"), too
        -- inconsistent to parse reliably.
        cast(null as numeric)                                          as salary_min,
        cast(null as numeric)                                          as salary_max,
        (payload ->> 'publication_date')::timestamptz                  as posted_at,
        nullif(payload ->> 'category', '')                             as source_category,
        first_seen_at,
        last_seen_at
    from source

)

select * from parsed
