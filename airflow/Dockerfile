# Extends the official Airflow image with dbt and the ingestion package's
# own dependencies, so DAG tasks can `import ingestion` and shell out to
# `dbt` without any extra plugin machinery.
FROM apache/airflow:2.10.2-python3.11

COPY requirements-airflow.txt /tmp/requirements-airflow.txt
RUN pip install --no-cache-dir -r /tmp/requirements-airflow.txt

USER root
# The dbt project + ingestion package are mounted as volumes at runtime
# (see docker-compose.yml), so nothing needs to be copied into the image
# itself -- editing a model or a DAG on the host is picked up immediately.
USER airflow
