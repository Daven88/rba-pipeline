# RBA Interest Rate Pipeline

An end-to-end batch data pipeline for Australian interest rate data, built on GCP.

## Architecture

```
World Bank API (JSON)
        │
        ▼
  Bronze Layer (GCS)          ← raw JSON, preserved as-is
        │
        ▼
  Silver Layer (GCS)          ← cleaned & flattened Parquet (Python)
        │
        ▼
  Gold Layer (BigQuery)       ← modelled tables (dbt)
        │
        ▼
  ML Layer (BigQuery)         ← rate direction predictions (scikit-learn)
        │
        ▼
  Orchestration (Airflow)     ← scheduled every ~6 weeks (RBA meeting cadence)
```

## Tech Stack

| Layer          | Tool                    |
|----------------|-------------------------|
| Cloud          | GCP                     |
| Object storage | Google Cloud Storage    |
| Warehouse      | BigQuery                |
| Transformation | dbt Core + Python       |
| Orchestration  | Apache Airflow (Docker) |
| ML             | scikit-learn            |
| Language       | Python 3.11+ / SQL      |

## Project Structure

```
rba-pipeline/
├── src/
│   ├── extract/        # API extraction → Bronze (GCS)
│   ├── transform/      # Python transforms → Silver (GCS)
│   └── ml/             # Prediction models
├── dbt/                # dbt models → Gold (BigQuery)
├── airflow/
│   └── dags/           # Orchestration DAGs
├── config/             # Environment config templates
└── tests/              # Unit and integration tests
```

## Setup

### Prerequisites

- Python 3.11+
- GCP project with billing enabled
- GCS buckets: `rba-pipeline-bronze`, `rba-pipeline-silver`
- GCP service account key with Storage Object Admin role

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment

```bash
cp config/.env.example config/.env
# Edit config/.env with your GCP project and bucket names
```

### Authenticate with GCP

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### Run extraction

```bash
python src/extract/rba_extract.py
```

## Modules

| Module | Description                        | Status      |
|--------|------------------------------------|-------------|
| 1      | Project setup & GCP config         | In progress |
| 2      | API extraction → Bronze layer      | In progress |
| 3      | Python transforms → Silver layer   | Pending     |
| 4      | dbt + BigQuery → Gold layer        | Pending     |
| 5      | ML layer (rate direction model)    | Pending     |
| 6      | Airflow DAG orchestration          | Pending     |
| 7      | PySpark module (separate dataset)  | Pending     |

## Data Source

Interest rate data is sourced from the [World Bank Open Data API](https://data.worldbank.org/indicator/FR.INR.LEND), which publishes Australia's lending interest rate (closely tracking RBA cash rate decisions). No API key is required.
