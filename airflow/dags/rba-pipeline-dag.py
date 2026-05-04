from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
from src.extract.extract_from_api import main as extract_main
from src.transform.transform import main as load_transform_main


with DAG(
    dag_id='rba-pipeline',
    schedule_interval='@weekly',
    start_date=datetime(2026, 5, 4),
    catchup=False
) as dag:
    
    extract_task = PythonOperator(
        task_id='extract_api',
        python_callable=extract_main
    )

    transform_task = PythonOperator(
        task_id='load_transform',
        python_callable=load_transform_main
    )

    dbt_task = BashOperator(
        task_id='dbt_run',
        bash_command='cd /opt/airflow/dbt/rba_pipeline && dbt run'
    )

    extract_task >> transform_task >> dbt_task