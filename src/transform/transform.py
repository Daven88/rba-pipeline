import pandas as pd
from google.cloud import storage
import pyarrow
import io
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, date

INDICATOR_CODES = ['FR.INR.LEND', 'FR.INR.RINR']

def read_from_bronze(bucket_name, blob):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob_loc = bucket.blob(blob)
    json_data = blob_loc.download_as_bytes()
    data = json.loads(json_data)
    return data

def clean_data(payload):
    records = payload['records']
    df = pd.DataFrame(records)
    df['indicator_id'] = df['indicator'].apply(lambda x:x['id']) 
    df['indicator_name'] = df['indicator'].apply(lambda x:x['value'])                                                                                                             
    df['country_id'] = df['country'].apply(lambda x:x['id']) 
    df['country_name'] = df['country'].apply(lambda x:x['value'])  
    df = df.drop(columns=['indicator', 'country', 'unit', 'obs_status', 'decimal'])
    df['date'] = df['date'].astype(int)
    return df

def load_to_silver(df, silver_bucket, indicator):
    buffer = io.BytesIO()                                                                                                                                                     
    df.to_parquet(buffer)
    buffer.seek(0)                                                                                                                                                            
    client = storage.Client()                                                                                                                                                 
    bucket_obj = client.bucket(silver_bucket)
    blob_name = f'interest_rates/{date.today()}_{indicator}.parquet' 
    blob_loc = bucket_obj.blob(blob_name) 
    blob_loc.upload_from_string(buffer.getvalue(),content_type='application/octet-stream')
    
def main():
    dot_env_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', '.env')
    load_dotenv(dot_env_path)
    bucket_name = os.getenv('GCS_BRONZE_BUCKET')
    silver_bucket = os.getenv('GCS_SILVER_BUCKET')

    for indicator in INDICATOR_CODES:
        blob_loc = f'interest_rates/{date.today()}_{indicator}.json'
        extracted_data = read_from_bronze(bucket_name, blob_loc)
        df = clean_data(extracted_data)
        load_to_silver(df, silver_bucket, indicator)

if __name__ == "__main__":
    main()
