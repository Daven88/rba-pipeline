# RBA Interest Rate Pipeline

With inflation surging and petrol prices at record highs, many Australians are asking: will interest rates go up or down? For property investors, this question is critical — higher rates directly reduce borrowing capacity, limiting what you can afford to buy. This pipeline extracts macro-economic indicators from the World Bank API, transforms and models them across a Bronze→Silver→Gold architecture on GCP, and applies machine learning to predict the direction of Australia's interest rates ahead of RBA meetings — helping answer the question: is now a good time to borrow?

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

## Dashboard

![ML Analysis Dashboard](docs/dashboard.png)

[View live dashboard](https://datastudio.google.com/reporting/96bc22f1-2266-41d8-a4d5-4362da1fc059)

![Airflow DAG](docs/airflow.png)

## Modules

| Module | Description                        | Status      |
|--------|------------------------------------|-------------|
| 1      | Project setup & GCP config         | Complete    |
| 2      | API extraction → Bronze layer      | Complete    |
| 3      | Python transforms → Silver layer   | Complete    |
| 4      | dbt + BigQuery → Gold layer        | Complete    |
| 5      | ML layer (rate direction model)    | Complete    |
| 6      | Airflow DAG orchestration          | Complete    |
| 7      | PySpark module (separate dataset)  | Pending     |

## Data Source

Interest rate data is sourced from the [World Bank Open Data API](https://data.worldbank.org/indicator/FR.INR.LEND), which publishes Australia's lending interest rate (closely tracking RBA cash rate decisions). No API key is required.
