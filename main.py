import subprocess
from pathlib import Path
from src.extract.extract_from_api import main as extract_main
from src.transform.transform import main as load_transform_main
from src.project_extension.ml.train import main as ml_train_main
from src.project_extension.extract.extract_rba_tables import main as extract_rba_main
from src.project_extension.transform.transform_rba_tables import main as transform_rba_main
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from google.cloud import bigquery

DBT_DIR = Path(__file__).parent / "dbt" / "rba_pipeline"

def run_dbt():
    subprocess.run(["dbt", "build"], cwd=DBT_DIR, check=True)

def should_run_today():
    client = bigquery.Client()
    query = "SELECT meeting_date FROM `rba-pipeline-494410.gold.rba_meeting_dates`"
    today = datetime.now(ZoneInfo('Australia/Sydney')).date()
    meetings = {row.meeting_date for row in client.query(query)}
    pre = {m - timedelta(days=2) for m in meetings}
    post = {m + timedelta(days=14) for m in meetings}
    run_days = pre | post

    future = sorted(d for d in run_days if d > today)
    print(f"Next run day: {future[0]}" if future
          else "WARNING: No future run days - calendar needs updating")
    
    return today in run_days

def main():
    if not os.getenv('FORCE_RUN') and not should_run_today():
        print("Not a scheduled run day, exiting.")
        return
    extract_main()
    load_transform_main()
    extract_rba_main()
    transform_rba_main()
    run_dbt()
    ml_train_main()

if __name__ == "__main__":
    main()