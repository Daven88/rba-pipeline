import subprocess
from pathlib import Path
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

def run_days_from(meetings):
    """Run two days before each meeting, to catch every data release the Board
    will see, and fourteen days after, once the minutes publish the decision.
    Pure function of the calendar - kept separate from the fetch so it can be
    tested without BigQuery."""
    pre = {m - timedelta(days=2) for m in meetings}
    post = {m + timedelta(days=14) for m in meetings}
    return pre | post

def fetch_meeting_dates():
    client = bigquery.Client()
    query = "SELECT meeting_date FROM `rba-pipeline-494410.gold.rba_meeting_dates`"
    return {row.meeting_date for row in client.query(query)}

def should_run_today():
    today = datetime.now(ZoneInfo('Australia/Sydney')).date()
    run_days = run_days_from(fetch_meeting_dates())

    future = sorted(d for d in run_days if d > today)
    print(f"Next run day: {future[0]}" if future
          else "WARNING: No future run days - calendar needs updating")

    return today in run_days

def main():
    if not os.getenv('FORCE_RUN') and not should_run_today():
        print("Not a scheduled run day, exiting.")
        return
    extract_rba_main()
    transform_rba_main()
    run_dbt()
    ml_train_main()

if __name__ == "__main__":
    main()