from google.cloud import pubsub_v1, bigquery
import requests
import pandas as pd
import json
from io import StringIO
from dotenv import load_dotenv
import os

load_dotenv('../../config/.env')
PROJECT_ID = os.getenv('GCP_PROJECT_ID')
TABLE_NAME = 'gold.rba_decisions'
url = 'https://www.rba.gov.au/statistics/cash-rate/'

def scrape_rba_decisions(url):
    response = requests.get(url)
    tables = pd.read_html(StringIO(response.text))
    df = tables[0]
    df = df.drop(columns='Related Documents')
    df.columns = ['date', 'change', 'cash_rate']
    df = df[~df['date'].str.contains('Legend|Cash rate')]
    return df

def get_latest_date():
    try:
        client = bigquery.Client(project=PROJECT_ID)
        bq_query = client.query('SELECT MAX(date) FROM `rba-pipeline-494410.gold.rba_decisions`')
        result = bq_query.result()
        for row in result:
            return row[0]
    except Exception:
        return None
    
def create_table():
    client = bigquery.Client()
    schema = [
        bigquery.SchemaField('date', 'STRING'),
        bigquery.SchemaField('change', 'STRING'),
        bigquery.SchemaField('cash_rate', 'STRING')
    ]
    table = bigquery.Table(f'{PROJECT_ID}.{TABLE_NAME}', schema=schema)
    client.create_table(table, exists_ok=True)

def batch_to_load_bq(df):
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f'{PROJECT_ID}.{TABLE_NAME}'
    job_config = bigquery.LoadJobConfig(write_disposition='WRITE_APPEND')
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()

def publish_decisions(df):
    client = pubsub_v1.PublisherClient()
    topic_path = client.topic_path('rba-pipeline-494410', 'rba-rate-decisions')
    for _, row in df.iterrows():
        try:
            message_bytes = json.dumps(row.to_dict()).encode('utf-8')
            future = client.publish(topic_path, message_bytes)
            future.result()
            print(f"Published: {row['date']}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    df = scrape_rba_decisions(url)
    latest_date = get_latest_date()
    if latest_date is None:
        create_table()
        batch_to_load_bq(df)
        print(f"Batch loaded {len(df)} records")
    else:
        new_rows = df[df['date'] > latest_date]
        publish_decisions(new_rows)
        print(f"Published {len(new_rows)} new records")
    
    

    