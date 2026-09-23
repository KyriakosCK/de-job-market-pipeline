# job_market dbt project

Transforms raw job-posting JSON (landed by the Python ingestion scripts in
`../../ingestion`) into an analytics-ready star schema.

```
raw.remoteok_jobs  ─┐
                     ├─▶ stg_remoteok_jobs  ─┐
raw.arbeitnow_jobs ─┘   stg_arbeitnow_jobs ─┴─▶ int_jobs_unioned ─▶ dim_company
                                                                  ─▶ fact_job_postings
                                                                  ─▶ bridge_job_skill ◀─ dim_skill (seed)
                                                                  ─▶ mart_skill_demand ─▶ fct_skill_demand_daily (incremental)
                                                                  ─▶ bridge_job_region ◀─ region_keywords (seed) ─▶ mart_postings_by_region
raw.load_runs ──────────────────────────────────────────────────▶ mart_pipeline_runs
```

## Common commands

```bash
dbt seed        # load seeds/skill_keywords.csv
dbt run         # build staging -> intermediate -> marts
dbt test        # schema + singular tests
dbt docs generate && dbt docs serve   # browsable lineage graph
```

See the root `README.md` for how these fit into the full pipeline and how
to run everything via Docker Compose / Airflow.
