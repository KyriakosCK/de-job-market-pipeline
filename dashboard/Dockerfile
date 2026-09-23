FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir streamlit==1.38.0 pandas==2.2.3 plotly==5.24.1 \
    sqlalchemy==2.0.35 psycopg2-binary==2.9.9

COPY dashboard/app.py .

EXPOSE 8501

# python:slim ships without curl, so probe the health endpoint with Python.
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
