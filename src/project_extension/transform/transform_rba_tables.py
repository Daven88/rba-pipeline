import io
import pandas as pd
from google.cloud import storage
from dotenv import load_dotenv
from datetime import datetime
import os
from google.api_core import exceptions


def read_from_bronze(bucket_name, blob):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob_loc = bucket.blob(blob)
    csv_data = blob_loc.download_as_bytes()
    return csv_data

config_dict = {
    "cpi": {
        "skiprows": 10,
        "usecols": [0, 10, 20],
        "columns": ['date', 'trimmed_mean_yoy', 'trimmed_mean_quarterly']
    },
    "labour_force": {
        "skiprows": 10,
        "usecols": [0, 10, 11],
        "columns": ['date','unemployed_%', 'unemployed_trend']
    },
    "commodity_prices": {
        "skiprows": 10,
        "usecols": [0, 1, 13],
        "columns": ['date','overall_AU$', 'bulk_AU$']
    },
    "government_expenditure": {
        "skiprows": 10,
        "usecols": [0, 2, 8],
        "columns": ['date', 'household_consump', 'government_spending']
    },
    "gdp": {
        "skiprows": 10,
        "usecols": [0, 2, 11],
        "columns": ['date', 'GDP_%', 'ratio_exp_to_imp']
    },
    "productivity": {
        "skiprows": 10,
        "usecols": [0, 1, 9],
        "columns": ['date', 'year_ended_wage_growth', 'year_ended_productivity_growth']
    }
}

def clean(csv_data, config):
    data = pd.read_csv(io.StringIO(csv_data.decode('utf-8')), 
                       skiprows=config['skiprows'],
                       usecols=config['usecols'],
                       header=None,
                       names=config['columns'])
    data = data.iloc[1:]
    data['date'] = pd.to_datetime(data['date'], dayfirst=True)
    numeric_cols = [col for col in data.columns if col != 'date']
    data[numeric_cols] = data[numeric_cols].apply(pd.to_numeric, errors='coerce')
    data = data.dropna()
    return data


def load_to_silver(data, silver_bucket, blob):
    buffer = io.BytesIO()
    data.to_parquet(buffer)
    buffer.seek(0)
    client = storage.Client()
    bucket_obj = client.bucket(silver_bucket)
    blob_loc = bucket_obj.blob(blob) 
    blob_loc.upload_from_string(buffer.getvalue(),content_type='application/octet-stream')

def main():
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', '.env')
    load_dotenv(dotenv_path)
    bronze_bucket = os.getenv('GCS_BRONZE_BUCKET')
    silver_bucket = os.getenv('GCS_SILVER_BUCKET')
    today = datetime.now().strftime('%Y-%m-%d')

    for table, config in config_dict.items():
        try:
            bronze_blob = f'rba_tables/{table}/{today}.csv'
            csv_data = read_from_bronze(bronze_bucket, bronze_blob)
            df = clean(csv_data, config)
            silver_blob = f'rba_tables/{table}/{today}.parquet'
            load_to_silver(df, silver_bucket, silver_blob)
        except exceptions.NotFound:
            print(f'{table} not found, does the extract script need to be run today?')
    
if __name__ == '__main__':
    main() 
   

