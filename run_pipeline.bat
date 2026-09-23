@echo off
cd /d %~dp0
call .venv\Scripts\activate.bat
python -m ingestion.extract_remoteok
python -m ingestion.extract_remotive
cd dbt\job_market
dbt run --profiles-dir .
dbt test --profiles-dir .
