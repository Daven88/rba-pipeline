import requests
from google.cloud import storage
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

url_dict = {
    "cpi": "https://www.rba.gov.au/statistics/tables/csv/g1-data.csv",
    "labour_force": "https://www.rba.gov.au/statistics/tables/csv/h5-data.csv",
    "commodity_prices": "https://www.rba.gov.au/statistics/tables/csv/i2-data.csv",
    "government_expenditure": "https://www.rba.gov.au/statistics/tables/csv/h2-data.csv",
    "gdp": "https://www.rba.gov.au/statistics/tables/csv/h1-data.csv",
    "productivity": "https://www.rba.gov.au/statistics/tables/csv/h4-data.csv"
}

def extract_from_csv(url_dict):
    data = {}
    for table, url in url_dict.items():
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        data[table] = response.content
    return data
    
def upload_to_gcs(bucket, blob, data):
    client = storage.Client()
    bucket_obj = client.bucket(bucket)
    blob_loc = bucket_obj.blob(blob)
    blob_loc.upload_from_string(data, content_type='text/csv')

def main():
    dotenv_path = os.path.join(os.path.dirname(__file__),'..', '..', '..', 'config', '.env')
    load_dotenv(dotenv_path)
    bucket = os.getenv('GCS_BRONZE_BUCKET')
    data = extract_from_csv(url_dict)
    for table, content in data.items():
        blob = f"rba_tables/{table}/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.csv"
        upload_to_gcs(bucket, blob, content)

if __name__ == '__main__':
    main()