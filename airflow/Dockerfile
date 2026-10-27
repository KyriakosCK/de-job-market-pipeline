# Official Airflow image plus dbt and the ingestion dependencies. The DAGs,
# ingestion package and dbt project are mounted at runtime (docker-compose.yml).
FROM apache/airflow:2.10.2-python3.11

COPY requirements-airflow.txt /tmp/requirements-airflow.txt
RUN pip install --no-cache-dir -r /tmp/requirements-airflow.txt
