from google.cloud import pubsub_v1, bigquery
import json
from dotenv import load_dotenv
import os
import threading

load_dotenv('../../config/.env')
PROJECT_ID = os.getenv('GCP_PROJECT_ID')
TABLE_NAME = 'gold.rba_decisions'
lock = threading.Lock()

def read_decisions():
    client = pubsub_v1.SubscriberClient()
    subscription_path = client.subscription_path('rba-pipeline-494410', 'rba-rate-decisions-sub')
    streaming_pull_future = client.subscribe(subscription_path, callback=callback)
    streaming_pull_future.result()

def callback(message):
    data = message.data.decode('utf-8')
    data = json.loads(data)
    with lock:
        push_to_bq(data, TABLE_NAME)
    message.ack()

def push_to_bq(data, table_name):
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f'{PROJECT_ID}.{table_name}'
    errors = client.insert_rows_json(table_id, [data])
    if errors:
        print(f"BQ insert error: {errors}")

if __name__ == '__main__':
    read_decisions()

