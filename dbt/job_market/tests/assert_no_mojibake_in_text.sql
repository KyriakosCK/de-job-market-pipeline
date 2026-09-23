-- Singular test: flags postings whose short text fields still contain
-- mojibake after ingestion's repair step (see macros/mojibake.sql).
--
-- Severity is warn, not error: int_jobs_unioned already nulls garbled
-- locations and company names, so nothing broken reaches the dashboard.
-- This test exists so that fallback firing is visible in `dbt test` output
-- instead of silently eating data. A sudden jump in its row count means a
-- source changed its encoding.
{{ config(severity='warn') }}

{% for model in ['stg_remoteok_jobs', 'stg_arbeitnow_jobs', 'stg_remotive_jobs'] %}
select job_id, title, company_name, location
from {{ ref(model) }}
where {{ is_mojibake('title') }}
   or {{ is_mojibake('company_name') }}
   or {{ is_mojibake('location') }}
{% if not loop.last %}union all{% endif %}
{% endfor %}
