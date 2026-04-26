import json
import requests
from datetime import datetime, timezone
from google.cloud import storage
from dotenv import load_dotenv
import os

BASE_URL = 'https://api.worldbank.org/v2'
INDICATOR_CODE = 'FR.INR.LEND'
COUNTRY_CODE = 'AU'

def extract_from_api(indicator, country):
    url = f'{BASE_URL}/country/{country}/indicator/{indicator}'
    response = requests.get(url, params={'format': 'json', 'per_page': 100})
    response.raise_for_status()
    data = response.json()
    metadata = data[0]
    records = data[1]
    return metadata, records

def package_data(records, indicator):
    payload = {
        'source': 'world_bank_api',
        'indicator': indicator,
        'extracted_at': datetime.now(timezone.utc).isoformat(),
        'record_count': len(records),
        'records': records
    }
    return payload

def upload_to_gcs(bucket, blob, payload):
    client = storage.Client()
    bucket_obj = client.bucket(bucket)
    blob_loc = bucket_obj.blob(blob)
    json_format = json.dumps(payload)
    blob_loc.upload_from_string(json_format, content_type='application/json')

def main():

    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', '.env')
    load_dotenv(dotenv_path)
    bucket_name = os.getenv('GCS_BRONZE_BUCKET')

    indicator = INDICATOR_CODE
    country = COUNTRY_CODE

    metadata, records = extract_from_api(indicator, country)

    payload = package_data(records, indicator)

    blob_path = f"interest_rates/{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"

    upload_to_gcs(bucket_name, blob_path, payload)

if __name__ == '__main__':
    main()


    

