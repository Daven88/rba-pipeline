FROM python:3.12-slim

WORKDIR /app

COPY airflow/requirements-airflow.txt .

RUN pip install -r requirements-airflow.txt

COPY src/ ./src/
COPY dbt/ ./dbt/
COPY main.py .

ENV DBT_PROFILES_DIR=/app/dbt/rba_pipeline

CMD ["python", "main.py"]