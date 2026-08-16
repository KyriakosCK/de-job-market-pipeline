# Architecture notes

## Layers

**1. Extract (`ingestion/`).** Two independent, side-effect-free extractors
fetch JSON from RemoteOK and Arbeitnow, filter out postings unrelated to
data/software roles (`ingestion/transform.py`), and upsert the full raw
payload as JSONB into `raw.remoteok_jobs` / `raw.arbeitnow_jobs`. Every run
is logged to `raw.load_runs` — success or failure — so pipeline health is
queryable with SQL instead of grepping logs.

**2. Load.** There isn't a separate load step: the extractors upsert
directly (`ingestion/db.py::upsert_raw_jobs`) keyed on a source-prefixed
`job_id`, so re-running ingestion is always safe (idempotent) and a posting
that disappears from a source just stops getting its `last_seen_at`
refreshed rather than being deleted.

**3. Transform (`dbt/job_market/`).**

```
staging (1:1 with raw, typed + cleaned)
  stg_remoteok_jobs, stg_arbeitnow_jobs
        │
        ▼
intermediate (source-agnostic)
  int_jobs_unioned
        │
        ▼
marts (star schema)
  dim_company, dim_skill ──┐
  fact_job_postings         ├──▶ bridge_job_skill (many-to-many)
  mart_skill_demand ────────┘
  mart_postings_by_location
  fct_skill_demand_daily (incremental, one partition per day)
  mart_pipeline_runs (observability, sourced from raw.load_runs)
```

Why a bridge table for skills instead of an array column on the fact table:
a job posting can require many skills and a skill applies to many postings
— genuine many-to-many — and a bridge table lets `mart_skill_demand`
aggregate with a plain `count(distinct job_id) group by skill_id` instead
of unnesting arrays on every query.

**4. Orchestrate (`airflow/dags/job_market_pipeline_dag.py`).** A single
`@daily` DAG: both extractors run in parallel, then `dbt seed → dbt run →
dbt test` runs once both have finished (staging models read from both raw
tables, so dbt can't start early). `dbt test` runs last and on purpose —
if data quality regresses, the DAG run is marked failed even though every
individual load succeeded, which is the signal that should actually page
someone.

**5. Serve (`dashboard/app.py`).** Reads exclusively from
`analytics_marts.*` — never from `raw` — which keeps "the dashboard is
wrong" bugs confined to a dbt model instead of spreading across the whole
stack.

## Table grains

| Table | Grain |
|---|---|
| `raw.remoteok_jobs` / `raw.arbeitnow_jobs` | one row per posting ever seen from that source |
| `int_jobs_unioned` | one row per posting, across both sources |
| `dim_company` | one row per distinct company name |
| `dim_skill` | one row per tracked skill (from the `skill_keywords` seed) |
| `fact_job_postings` | one row per posting (same grain as `int_jobs_unioned`, enriched with `company_id` + `is_active`) |
| `bridge_job_skill` | one row per (posting, skill) match |
| `mart_skill_demand` | one row per skill, current point-in-time counts |
| `fct_skill_demand_daily` | one row per (day, skill) — this is the only table with history |
| `mart_pipeline_runs` | one row per ingestion run |

## Extending it

* **New source:** add `ingestion/extract_<source>.py` (copy the Arbeitnow
  one if it paginates, RemoteOK's if it doesn't), a `raw.<source>_jobs`
  table in `sql/ddl_raw_tables.sql`, a `stg_<source>_jobs.sql` model, and
  one more `union all` branch in `int_jobs_unioned.sql`. No mart changes.
* **New skill:** add a row to `dbt/job_market/seeds/skill_keywords.csv`
  and `dbt seed`. No model changes.
* **New dimension (e.g. seniority level parsed from title):** add it to
  `int_jobs_unioned.sql`, then either a new `dim_*` model or a column
  directly on `fact_job_postings`, depending on whether it's genuinely
  reusable across facts or specific to postings.
