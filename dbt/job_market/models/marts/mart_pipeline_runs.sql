-- Lightweight operational/observability mart over the ingestion run log,
-- so pipeline health can be queried with SQL like everything else instead
-- of grepping Airflow logs.
select
    run_id,
    source,
    records_fetched,
    records_upserted,
    started_at,
    finished_at,
    extract(epoch from (finished_at - started_at)) as duration_seconds,
    status,
    error_message
from {{ source('raw', 'load_runs') }}
order by started_at desc
