"""
SkillScope dashboard: a thin read-only view over the marts the dbt project
builds. It never talks to the raw schema or the source APIs directly -- if
a number looks wrong here, the bug is in a dbt model, not in this file,
which is exactly the separation of concerns an ELT pipeline should give you.

Run standalone (outside Docker) with:
    streamlit run dashboard/app.py
"""
from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

st.set_page_config(page_title="SkillScope | Data Job Market", page_icon="📊", layout="wide")

MARTS_SCHEMA = "analytics_marts"


@st.cache_resource
def get_engine() -> Engine:
    host = os.environ.get("WAREHOUSE_HOST", "localhost")
    port = os.environ.get("WAREHOUSE_PORT", "5432")
    db = os.environ.get("WAREHOUSE_DB", "warehouse")
    user = os.environ.get("WAREHOUSE_USER", "jobmarket")
    password = os.environ.get("WAREHOUSE_PASSWORD", "jobmarket")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=300)
def load_table(table_name: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(f"select * from {MARTS_SCHEMA}.{table_name}"), conn)


def marts_exist() -> bool:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "select 1 from information_schema.schemata where schema_name = :schema"
            ),
            {"schema": MARTS_SCHEMA},
        )
        return result.first() is not None


st.title("📊 SkillScope — Data & Software Job Market")
st.caption(
    "Live view over remote job postings from RemoteOK and Remotive, "
    "modelled with dbt on Postgres and refreshed daily. "
    "Job data courtesy of [Remotive](https://remotive.com) and "
    "[RemoteOK](https://remoteok.com). "
    "Source: github.com/KyriakosCK/de-job-market-pipeline"
)

try:
    if not marts_exist():
        st.warning(
            "The `analytics_marts` schema doesn't exist yet. Run the pipeline first:\n\n"
            "```bash\ndocker compose up airflow-init\n"
            "# then trigger the `job_market_pipeline` DAG from http://localhost:8080\n```"
        )
        st.stop()

    fact = load_table("fact_job_postings")
    companies = load_table("dim_company")
    skill_demand = load_table("mart_skill_demand")
    by_location = load_table("mart_postings_by_location")
    daily_trend = load_table("fct_skill_demand_daily")
    pipeline_runs = load_table("mart_pipeline_runs")

except Exception as exc:  # noqa: BLE001
    st.error(f"Couldn't reach the warehouse database: {exc}")
    st.info("Is `docker compose up` running, and has the DAG completed at least once?")
    st.stop()

active_postings = fact[fact["is_active"]] if "is_active" in fact.columns else fact

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total postings tracked", int(len(fact)))
col2.metric("Active postings", int(len(active_postings)))
col3.metric("Companies hiring", int(active_postings["company_id"].nunique()))
col4.metric("Skills tracked", int(skill_demand["skill_id"].nunique()))
last_run = pipeline_runs.iloc[0] if not pipeline_runs.empty else None
col5.metric(
    "Last pipeline run",
    last_run["status"].upper() if last_run is not None else "n/a",
    help="Most recent row in raw.load_runs, surfaced via mart_pipeline_runs.",
)

st.divider()

left, right = st.columns([3, 2])

with left:
    st.subheader("Most in-demand skills")
    top_skills = skill_demand[skill_demand["all_time_postings_count"] > 0].head(15)
    if top_skills.empty:
        st.info("No skill matches yet -- run the pipeline to populate data.")
    else:
        fig = px.bar(
            top_skills.sort_values("all_time_postings_count"),
            x="all_time_postings_count",
            y="skill_name",
            color="category",
            orientation="h",
            labels={"all_time_postings_count": "Postings (all time)", "skill_name": "Skill"},
        )
        fig.update_layout(height=500, legend_title_text="Category")
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Postings by location")
    top_locations = by_location.sort_values("postings_count", ascending=False).head(10)
    st.dataframe(
        top_locations[["location", "postings_count", "remote_postings_count"]],
        hide_index=True,
        use_container_width=True,
    )

st.divider()

st.subheader("Active postings")
active_listings = active_postings.merge(companies, on="company_id", how="left")[
    ["title", "company_name", "location", "posting_url"]
]
# location/company_name can be NULL (RemoteOK doesn't always publish them);
# label them the same way mart_postings_by_location already does, rather
# than let st.dataframe render the literal string "None". posting_url is
# left blank instead, since a link column showing "Unspecified" would look
# like a broken link rather than a missing one.
active_listings = active_listings.fillna(
    {"company_name": "Unspecified", "location": "Unspecified", "posting_url": ""}
)
st.dataframe(
    active_listings,
    hide_index=True,
    use_container_width=True,
    column_config={
        "title": "Title",
        "company_name": "Company",
        "location": "Location",
        "posting_url": st.column_config.LinkColumn("Posting URL"),
    },
)

st.divider()

st.subheader("Skill demand trend")
if daily_trend.empty or daily_trend["snapshot_date"].nunique() < 2:
    st.info(
        "Trend needs at least two days of pipeline runs -- "
        "`fct_skill_demand_daily` appends one row per skill every time the DAG runs."
    )
else:
    top_skill_names = skill_demand.sort_values("postings_count", ascending=False).head(8)["skill_name"]
    trend_subset = daily_trend[daily_trend["skill_name"].isin(top_skill_names)]
    fig = px.line(
        trend_subset.sort_values("snapshot_date"),
        x="snapshot_date",
        y="postings_count",
        color="skill_name",
        markers=True,
        labels={"snapshot_date": "Date", "postings_count": "Active postings", "skill_name": "Skill"},
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

with st.expander("Pipeline run history (raw.load_runs via mart_pipeline_runs)"):
    st.dataframe(pipeline_runs, hide_index=True, use_container_width=True)
