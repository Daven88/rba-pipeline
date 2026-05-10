from google.cloud import pubsub_v1
import requests
import pandas as pd
import json
from io import StringIO

url = 'https://www.rba.gov.au/statistics/cash-rate/'

def scrape_rba_decisions(url):
    response = requests.get(url)
    tables = pd.read_html(StringIO(response.text))
    df = tables[0]
    df = df.drop(columns='Related Documents')
    df.columns = ['date', 'change', 'cash_rate']
    df = df[~df['date'].str.contains('Legend|Cash rate')]
    return df

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
    print(df.head())
    publish_decisions(df.head(5))