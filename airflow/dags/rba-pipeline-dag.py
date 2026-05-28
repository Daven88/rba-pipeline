from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime
from src.extract.extract_from_api import main as extract_main
from src.transform.transform import main as load_transform_main
from src.ml.train import main as ml_train_main
from src.project_extension.extract.extract_rba_tables import main as extract_rba_main
from src.project_extension.transform.transform_rba_tables import main as transform_rba_main


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
        bash_command='cd /opt/airflow/dbt/rba_pipeline && dbt clean && dbt run'
    )

    ml_train = PythonOperator(
        task_id='ml_train',
        python_callable=ml_train_main
    )

    extract_rba_task = PythonOperator(
        task_id='extract_rba_csv',
        python_callable=extract_rba_main
    )

    transform_rba_task = PythonOperator(
        task_id='transform_rba',
        python_callable=transform_rba_main
    )

    extract_task >> transform_task 
    extract_rba_task >> transform_rba_task
    [transform_task, transform_rba_task] >> dbt_task >> ml_train