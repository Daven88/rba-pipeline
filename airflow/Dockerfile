FROM apache/airflow:2.10.5
USER root
COPY requirements-airflow.txt .
RUN pip install -r requirements-airflow.txt
USER airflow