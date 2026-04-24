# RBA Interest Rate Pipeline — Project Context

## About Me
- Aspiring data engineer/scientist, Masters in Data Science
- Advanced SQL & Python, some Airflow & Docker experience
- Learning: dbt, GCP, full pipeline architecture

## Project Goal
End-to-end batch pipeline for Australian interest rate data.
Runs every ~6 weeks aligned to RBA meetings.

## Tech Stack Decisions (and why)
- **Cloud:** GCP (aligns with current employer direction)
- **Storage:** GCS buckets (Bronze/Silver layers as Parquet)
- **Warehouse:** BigQuery (Gold layer)
- **Transformation/Modelling:** dbt Core
- **Orchestration:** Airflow running in Docker
- **ML:** scikit-learn (rate direction prediction)
- **Language:** Python + SQL (PySpark saved for separate module)

## Architecture
Bronze (raw JSON/CSV in GCS)
  → Silver (cleaned Parquet in GCS, Python transforms)
  → Gold (BigQuery tables, modelled by dbt)
  → ML layer (predictions stored back in BigQuery)
  → Orchestrated by Airflow DAG

## Current Module
Module 1 — Project Setup
- OS: Windows
- Tools installed: VS Code, Git, Docker

## Key Decisions Log
- Chose BigQuery over PySpark: data volume too small for Spark
- Chose dbt Core (free/open source) over dbt Cloud
- Skipped Databricks Community Edition: too limited for GCP integration

## Modules Completed
- [ ] Module 1: Project setup & GCP config
- [ ] Module 2: API extraction → Bronze layer
- [ ] Module 3: Python transforms → Silver layer
- [ ] Module 4: dbt + BigQuery → Gold layer
- [ ] Module 5: ML layer
- [ ] Module 6: Airflow DAG
- [ ] Module 7: PySpark (separate dataset)