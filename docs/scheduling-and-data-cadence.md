# Scheduling & Data Cadence

Notes for migrating the pipeline off local Airflow onto Cloud Run Jobs + Cloud
Scheduler. Verified against live sources on 2026-09-06.

## Why not Cloud Composer

Composer is managed Airflow, but it runs a permanently-on GKE cluster —
roughly $300+/month. For a job that fires eight times a year, Cloud Run Jobs
bill per execution and land inside the free tier. The Airflow DAG stays in the
repo as a record of the orchestration design; it just stops being the thing
that runs.

## Source update cadences

Read from the RBA CSV headers and the World Bank API on 2026-09-06.

| Source | Table | Freq | Last published | Latest obs |
|---|---|---|---|---|
| Commodity prices | I2 | Monthly (1st business day) | 01-Sep-2026 | Aug 2026 |
| Labour force | H5 | Monthly (~3rd Thursday) | 21-Aug-2026 | Jul 2026 |
| CPI trimmed mean | G1 | Quarterly (late Jan/Apr/Jul/Oct) | 30-Jul-2026 | Q2 2026 |
| Wage growth / productivity | H4 | Quarterly | 20-Aug / 03-Sep-2026 | Q2 2026 |
| GDP / terms of trade | H1 | Quarterly (early Mar/Jun/Sep/Dec) | 03-Sep-2026 | Q2 2026 |
| Household consumption / public demand | H2 | Quarterly | 03-Sep-2026 | Q2 2026 |
| World Bank indicators | — | Annual | 13-Jul-2026 | 2025 |

Three different clocks. The quarterly national accounts (H1/H2/H4) are the
binding constraint — they land in the first week of Mar/Jun/Sep/Dec.

**Running two days before a meeting is the right window.** The RBA schedules
its meetings *after* the ABS releases it wants to see, so T-2 captures every
release the Board itself is looking at:

- Sep 29 meeting → Sep 3 national accounts already published
- Nov 3 meeting → late-Oct Q3 CPI already published
- Dec 8 meeting → Dec 3 national accounts already published

## Two run types

| Run | Trigger | Purpose |
|---|---|---|
| Pre-meeting | T-2 days | Refresh features, regenerate prediction |
| Post-minutes | T+14 days | Capture actual decision + sentiment, retrain |

The RBA publishes minutes two weeks after each meeting. Without the second run
the training set never gains the most recent decision — the model would never
learn from the meeting it just predicted.

## Scheduling approach

Cron cannot express "two days before an irregular date". Rather than maintain
eight cron entries a year, fire **one daily Cloud Scheduler job** and gate
inside the container: `main.py` reads the meeting calendar and exits 0
immediately unless today is T-2 or T+14. A job that exits in two seconds, 365
times a year, costs effectively nothing, and the cron expression never needs
editing.

### Meeting calendar needs a single source of truth

`RBA_MEETING_DATES_2026` is currently hardcoded in `streamlit/app.py`. Once the
scheduler gate needs the same dates, that list exists in two places and will
drift.

Move it to a **dbt seed** → `gold.rba_meeting_dates`, read by both the gate and
the dashboard. Adding the 2027 calendar then means editing one CSV. It also
retires the dashboard's "calendar needs updating" fallback.

Remaining 2026 meetings: **Sep 29, Nov 3, Dec 8**. The list runs dry after that.

## Known issues to fix during the migration

### 1. Stale World Bank indicators

`FR.INR.LEND` (lending interest rate) has **no data after 2019** — seven years
stale. `FR.INR.RINR` is likely the same vintage. Both are extracted, stored and
potentially fed to the model as constants. Check whether they contribute
anything before carrying them forward.

### 2. Model artifact written to an ephemeral path

`src/project_extension/ml/train.py:127` does
`joblib.dump(best_model, 'src/project_extension/ml/models/best_model.pkl')` —
a relative path into a directory that is gitignored, so it will not exist in
the image (`FileNotFoundError`). Line 130 then reads it back. The Cloud Run
filesystem is in-memory and dies with the job, so the model must go to GCS.

### 3. Config comes from a gitignored .env

`config/.env` is not in the image, so `os.getenv('GCS_BRONZE_BUCKET')` returns
`None` and `client.bucket(None)` fails. Bucket names must be passed as Cloud
Run environment variables.

### 4. GOOGLE_APPLICATION_CREDENTIALS must be unset

Locally, docker-compose mounts personal ADC from `AppData/Roaming/gcloud`. On
Cloud Run this variable must be left unset so the SDK picks up the runtime
service account automatically.

### 5. profiles.yml exists only on the dev machine

`C:\Users\User\.dbt\profiles.yml` is mounted by docker-compose and is not in
git. The image needs its own copy. Contents are already correct —
`method: oauth` resolves to ADC, so it works unchanged under a runtime service
account.

### 6. Positional usecols are fragile

`transform_rba_tables.py` selects columns by index (e.g. `usecols=[0, 2, 8]`).
All six mappings were verified correct on 2026-09-06, but if the RBA adds or
reorders a column the meaning shifts silently with no error. Worth pinning to
the Series ID row instead.

## Identity

Use a dedicated `rba-pipeline-runner` service account — not the dashboard's.
`rba-dashboard` is deliberately read-only (`bigquery.dataViewer`,
`bigquery.jobUser`) so a bug in the public app can never mutate the warehouse.
The pipeline runner needs `bigquery.dataEditor`, `bigquery.jobUser` and
`storage.objectAdmin`.

## Cleanup candidate

`config/rba-streamlit-deploy-*.json` is a service account key created for the
old Streamlit Community Cloud deployment. Cloud Run uses keyless ADC, so this
key is no longer needed. It is gitignored, but it is still a live credential
sitting on disk — consider deleting the key and the `rba-streamlit-deploy`
project.
