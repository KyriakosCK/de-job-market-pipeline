-- Postings whose text still has mojibake after ingestion's repair. Warn
-- only: int_jobs_unioned nulls them, and this makes that visible. A jump
-- in the count means a source changed its encoding.
{{ config(severity='warn') }}

{% for model in ['stg_remoteok_jobs', 'stg_remotive_jobs'] %}
select job_id, title, company_name, location
from {{ ref(model) }}
where {{ is_mojibake('title') }}
   or {{ is_mojibake('company_name') }}
   or {{ is_mojibake('location') }}
{% if not loop.last %}union all{% endif %}
{% endfor %}
