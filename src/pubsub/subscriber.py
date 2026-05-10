from google.cloud import pubsub_v1, bigquery
import json
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv('../../config/.env')
PROJECT_ID = os.getenv('GCP_PROJECT_ID')

TABLE_NAME = 'gold.rba_decisions'

def read_decisions():
    client = pubsub_v1.SubscriberClient()
    subscription_path = client.subscription_path('rba-pipeline-494410', 'rba-rate-decisions-sub')
    streaming_pull_future = client.subscribe(subscription_path, callback=callback)
    streaming_pull_future.result()

def callback(message):
    data = message.data.decode('utf-8')
    data = json.loads(data)
    push_to_bq(data, TABLE_NAME)
    message.ack()

def push_to_bq(data, table_name):
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f'{PROJECT_ID}.{table_name}'
    job_config = bigquery.LoadJobConfig(write_disposition='WRITE_APPEND')
    df = pd.DataFrame([data])
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()

def create_table():
    client = bigquery.Client()
    schema = [
        bigquery.SchemaField('date', 'STRING'),
        bigquery.SchemaField('change', 'STRING'),
        bigquery.SchemaField('cash_rate', 'STRING')
    ]
    table = bigquery.Table(f'{PROJECT_ID}.{TABLE_NAME}', schema=schema)
    client.create_table(table, exists_ok=True)

if __name__ == '__main__':
    read_decisions()
