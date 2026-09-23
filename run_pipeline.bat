@echo off
rem Daily SkillScope run for Windows Task Scheduler (the no-Docker
rem alternative to the Airflow DAG). Each run appends to its own dated log
rem in logs\, and the script exits non-zero if any step fails so Task
rem Scheduler's "Last Run Result" shows the failure.
setlocal
cd /d %~dp0
if not exist logs mkdir logs
for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set RUN_DATE=%%d
set LOG=logs\pipeline_%RUN_DATE%.log
set PYTHONIOENCODING=utf-8
set FAILED=0

call .venv\Scripts\activate.bat
echo ===== SkillScope run started %DATE% %TIME% ===== >> %LOG%

rem Extractors are independent: one source being down shouldn't stop the
rem other from landing, or dbt from rebuilding on whatever data we have.
python -m ingestion.extract_remoteok >> %LOG% 2>&1 || set FAILED=1
python -m ingestion.extract_remotive >> %LOG% 2>&1 || set FAILED=1

rem `dbt build` = seed + run + test in dependency order.
pushd dbt\job_market
dbt build --profiles-dir . >> ..\..\%LOG% 2>&1 || set FAILED=1
popd

echo ===== SkillScope run finished %DATE% %TIME% (failed=%FAILED%) ===== >> %LOG%
exit /b %FAILED%
