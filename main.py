import subprocess
from pathlib import Path
from src.extract.extract_from_api import main as extract_main
from src.transform.transform import main as load_transform_main
from src.project_extension.ml.train import main as ml_train_main
from src.project_extension.extract.extract_rba_tables import main as extract_rba_main
from src.project_extension.transform.transform_rba_tables import main as transform_rba_main

DBT_DIR = Path(__file__).parent / "dbt" / "rba_pipeline"

def run_dbt():
    subprocess.run(["dbt", "build"], cwd=DBT_DIR, check=True)

def main():
    extract_main()
    load_transform_main()
    extract_rba_main()
    transform_rba_main()
    run_dbt()
    ml_train_main()

if __name__ == "__main__":
    main()