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
from sqlalchemy.engine import URL, Engine

st.set_page_config(page_title="SkillScope | Data Job Market", page_icon="📊", layout="wide")

MARTS_SCHEMA = "analytics_marts"

# One blue that holds 3:1+ contrast on both Streamlit's light and dark
# backgrounds.
BAR_COLOR = "#3987e5"
# Muted gray for "Unspecified", which isn't a real category.
UNSPECIFIED_COLOR = "#8a8a85"

# Display names for the lowercase category codes in seeds/skill_keywords.csv.
CATEGORY_LABELS = {
    "bi": "BI",
    "ml": "ML",
    "devops": "DevOps",
}


@st.cache_resource
def get_engine() -> Engine:
    # URL.create escapes each part, so a password containing "@" or "/"
    # can't corrupt the connection string the way an f-string would.
    url = URL.create(
        "postgresql+psycopg2",
        username=os.environ.get("WAREHOUSE_USER", "jobmarket"),
        password=os.environ.get("WAREHOUSE_PASSWORD", "jobmarket"),
        host=os.environ.get("WAREHOUSE_HOST", "localhost"),
        port=int(os.environ.get("WAREHOUSE_PORT", "5432")),
        database=os.environ.get("WAREHOUSE_DB", "warehouse"),
    )
    return create_engine(url, pool_pre_ping=True)


def latest_run_status(pipeline_runs: pd.DataFrame) -> tuple[str, str]:
    """Overall status of the most recent pipeline run, and a per-source breakdown.

    Takes each source's latest run, so one source failing can't be hidden by
    another succeeding after it. Sources with no run in the day before the
    newest run are left out, so a source that's no longer scheduled doesn't
    keep reporting its last failure.
    """
    latest = pipeline_runs.sort_values("started_at", ascending=False).drop_duplicates("source")
    latest = latest[latest["started_at"] >= latest["started_at"].max() - pd.Timedelta(days=1)]
    overall = "FAILED" if (latest["status"] != "success").any() else "SUCCESS"
    breakdown = ", ".join(f"{row.source}: {row.status}" for row in latest.itertuples())
    return overall, breakdown


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
            "The `analytics_marts` schema doesn't exist yet. Run the pipeline first: "
            "`run_pipeline.bat` locally, or trigger the `job_market_pipeline` DAG "
            "from http://localhost:8080 when using Docker Compose."
        )
        st.stop()

    fact = load_table("fact_job_postings")
    companies = load_table("dim_company")
    skill_demand = load_table("mart_skill_demand")
    by_region = load_table("mart_postings_by_region")
    daily_trend = load_table("fct_skill_demand_daily")
    pipeline_runs = load_table("mart_pipeline_runs")

except Exception as exc:  # noqa: BLE001
    st.error(f"Couldn't reach the warehouse database: {exc}")
    st.info(
        "Is the warehouse Postgres running (check the WAREHOUSE_* environment "
        "variables), and has the pipeline completed at least once?"
    )
    st.stop()

active_postings = fact[fact["is_active"]] if "is_active" in fact.columns else fact

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total postings tracked", int(len(fact)))
col2.metric("Active postings", int(len(active_postings)))
col3.metric("Companies hiring", int(active_postings["company_id"].nunique()))
col4.metric("Skills tracked", int(skill_demand["skill_id"].nunique()))
if pipeline_runs.empty:
    col5.metric("Last pipeline run", "n/a")
else:
    run_status, run_breakdown = latest_run_status(pipeline_runs)
    col5.metric(
        "Last pipeline run",
        run_status,
        help=f"Latest run of each source in raw.load_runs ({run_breakdown}).",
    )

st.divider()

left, right = st.columns([3, 2])

with left:
    st.subheader("Most in-demand skills")
    matched_skills = skill_demand[skill_demand["all_time_postings_count"] > 0].assign(
        category_label=lambda df: df["category"].map(CATEGORY_LABELS).fillna(df["category"].str.title())
    )
    # The chart ranks skills, so every bar is one color and category is a
    # filter rather than a hue: sorted by count, any two categories can end
    # up side by side, and 8+ hues can't stay distinguishable that way.
    category = st.selectbox(
        "Category",
        ["All categories", *sorted(matched_skills["category_label"].unique())],
        label_visibility="collapsed",
    )
    if category != "All categories":
        matched_skills = matched_skills[matched_skills["category_label"] == category]
    top_skills = matched_skills.nlargest(15, "all_time_postings_count")
    if top_skills.empty:
        st.info("No skill matches yet -- run the pipeline to populate data.")
    else:
        fig = px.bar(
            top_skills.sort_values("all_time_postings_count"),
            x="all_time_postings_count",
            y="skill_name",
            orientation="h",
            custom_data=["category_label"],
            labels={"all_time_postings_count": "Postings (all time)", "skill_name": ""},
        )
        fig.update_traces(
            marker_color=BAR_COLOR,
            hovertemplate="<b>%{y}</b><br>%{customdata[0]}<br>%{x} postings<extra></extra>",
        )
        fig.update_layout(height=500, bargap=0.25, margin={"l": 0, "r": 0, "t": 10, "b": 0})
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Where you can apply from")
    if by_region.empty:
        st.info("No active postings yet -- run the pipeline to populate data.")
    else:
        # Unspecified isn't a region, so it's pinned to the bottom in gray
        # instead of competing in the ranking.
        regions = by_region.assign(
            is_unspecified=by_region["region"] == "Unspecified"
        ).sort_values(["is_unspecified", "postings_count"], ascending=[False, True])
        fig = px.bar(
            regions,
            x="postings_count",
            y="region",
            orientation="h",
            custom_data=["pct_of_active_postings"],
            labels={"postings_count": "Active postings", "region": ""},
        )
        fig.update_traces(
            marker_color=[UNSPECIFIED_COLOR if u else BAR_COLOR for u in regions["is_unspecified"]],
            hovertemplate="<b>%{y}</b><br>%{x} postings (%{customdata[0]}% of active)<extra></extra>",
        )
        fig.update_layout(height=420, bargap=0.25, margin={"l": 0, "r": 0, "t": 10, "b": 0})
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Remote roles often hire from several regions, so a posting counts "
            "once in each region it's open to."
        )

st.divider()

st.subheader("Active postings")
active_listings = active_postings.merge(companies, on="company_id", how="left")[
    ["title", "company_name", "location", "posting_url"]
]
# location/company_name can be NULL (RemoteOK doesn't always publish them);
# label them "Unspecified" as the region chart does, rather
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
        "location": st.column_config.TextColumn(
            "Location", help="Company location, or the regions a remote role hires from"
        ),
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
    # Same ranking as the "Most in-demand skills" chart, so the trend follows
    # the skills shown at the top there.
    top_skill_names = skill_demand.nlargest(8, "all_time_postings_count")["skill_name"]
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
