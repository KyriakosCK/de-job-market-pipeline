-- Flatten the raw Remotive JSONB payload into typed columns and standardize
-- it onto the common job-posting shape shared with the other staging models.
--
-- Two things are different about this source:
--   * Remotive is a remote-only board, so is_remote is always true rather
--     than inferred from the location text.
--   * Remotive classifies every posting itself, and that label is carried
--     through as source_category so int_jobs_unioned can trust it instead
--     of keyword-matching the title.
--
-- Column order must stay identical to the other stg_* models: they're
-- combined with `union all` on `select *` in int_jobs_unioned.
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
        -- Remotive publishes salary as free text ("$120 - $170 /hour",
        -- "175k - 190k", "Pay per task", ""). There's no reliable way to
        -- parse that into numeric columns without inventing precision we
        -- don't have, so it's left null rather than guessed at.
        cast(null as numeric)                                          as salary_min,
        cast(null as numeric)                                          as salary_max,
        (payload ->> 'publication_date')::timestamptz                  as posted_at,
        nullif(payload ->> 'category', '')                             as source_category,
        first_seen_at,
        last_seen_at
    from source

)

select * from parsed
