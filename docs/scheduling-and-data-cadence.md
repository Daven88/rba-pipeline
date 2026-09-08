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

## Migration checklist

| # | Step | Status |
|---|---|---|
| 1 | Dockerfile at repo root | done |
| 2 | Root `.gcloudignore` (56 files, down from 56,138) | done |
| 3 | `profiles.yml` committed to `dbt/rba_pipeline/` | done |
| 4 | `main.py` entrypoint | done |
| 5 | Fix the three runtime blockers (model to GCS, buckets from env, `GOOGLE_APPLICATION_CREDENTIALS` unset) | done |
| 6 | `rba-pipeline-runner` service account + IAM | done |
| 7 | `gcloud run jobs deploy`, then `execute` to test manually | done - green 2026-09-07 |
| 8 | Meeting calendar as a dbt seed -> `gold.rba_meeting_dates`, gate in `main.py` | |
| 9 | Cloud Scheduler daily trigger with OIDC | |
| 10 | GitHub Actions CI | |
| 11 | Fix Silver snapshot duplication (see below) | done - 2026-09-08 |
| 12 | Add model-level dbt tests (`unique`, ranges, accepted values) | |

Steps 1-7 get the pipeline running. 8-9 put it on a schedule. 10 is independent
and can happen whenever.

### Run dbt tests, not just models

`schema.yml` declares **27 tests** that have never run in the pipeline. Both the
Airflow DAG and `main.py` call `dbt run`, which builds models and ignores tests.

Switch the subprocess call to `dbt build` — it runs models and their tests
together in DAG order, and stops a failed model propagating downstream. With
`check=True` a failing data test then fails the Cloud Run Job, which is the
alerting you would otherwise have to build by hand.

Highest value per unit of effort in this whole list: the tests already exist.

### What the first cloud run exposed (2026-09-07)

Three things broke that had worked locally for months. All the same root cause:
running as a service account removes the permissions your personal ADC was
silently supplying.

**Two GCP projects, both named "rba-pipeline".**

    rba-pipeline          369194321133   <- owns the GCS buckets
    rba-pipeline-494410   213888644789   <- owns BigQuery, Cloud Run

`storage.objectAdmin` was granted on 494410, which contains no buckets. Fixed
with bucket-level bindings on `rba-pipeline-bronze` and `rba-pipeline-silver`,
which is tighter than a second project-wide grant.

**Four `schema.yml` column names did not exist.** `unemployed_%`, `GDP_%`,
`overall_AU$`, `bulk_AU$` - the real BigQuery names are `unemployed__`,
`GDP__`, `overall_AU_`, `bulk_AU_` (pandas mangled the CSV headers). dbt writes
the yml name straight into `where GDP_% is null`, so BigQuery threw a syntax
error. These four tests could never have passed; `dbt run` never executed them.

**The service account could not read `finance-lakehouse:rba_minutes.sentiment`.**
The cross-project sentiment join only ever worked because the developer's ADC
had access to both projects. Fixed with `bigquery.dataViewer` on that table.

Also noted: the buckets are in `US` while BigQuery and Cloud Run are in
`australia-southeast1`, so every `dbt build` pulls Parquet across the Pacific.
Works, but costs latency and egress. Moving a bucket means recreating it and
repointing the external tables, so it is not a quick fix.

### Silver snapshot duplication (step 11) - FIXED 2026-09-08

Resolved by writing one file per table and overwriting it, rather than a dated
snapshot per run. Bronze already keeps every dated raw CSV and JSON, so the
audit trail did not need duplicating in Silver.

    rba_tables/{table}/{today}.parquet      ->  rba_tables/{table}/{table}.parquet
    interest_rates/{date}_{ind}.parquet     ->  interest_rates/{ind}.parquet

The folder must be kept - the external tables glob a specific directory
(`gs://.../rba_tables/cpi/*.parquet`), so flattening the path leaves them
matching nothing. That failure is silent: an empty external table passes
`not_null` vacuously, `dbt build` stays green, and the marts quietly empty.

Result: 89 Silver files -> 12. `ext_cpi` 1213 rows -> 174, with rows now equal
to distinct dates on every RBA table. `mart_rba_decisions` stayed at 299 rows,
confirming the marts had always been deduplicated by the `ROW_NUMBER()` pattern
and the model's training data is unchanged.

Note `stg_interest_rates_raw` is 396 rows over 66 dates and is correct: its
grain is (date, indicator_id), 66 years x 6 indicators.

#### Original problem


Each run writes a new dated Parquet file holding the **full history**, and the
external tables read the whole folder with a wildcard:

    gs://rba-pipeline-silver/rba_tables/cpi/*.parquet

So every run adds another complete copy. Measured 2026-09-06:

| Table | Rows | Distinct dates |
|---|---|---|
| `ext_cpi` | 865 | 173 |
| `ext_labour_force` | 2,898 | 581 |
| `mart_rba_decisions` | 299 | 299 |

Five runs, five copies. The marts are clean only by accident: the
`ROW_NUMBER() ... rn = 1` pattern in `int_rba_features` was written to replace
an unsupported `ASOF JOIN`, and collapsing duplicates is a side effect. Change
that logic and duplicates reach the marts.

Costs today: 5x scan on every `dbt build`, growing by one full copy per run.
This matters more once Cloud Scheduler runs it unattended.

Two fixes to choose between:
- Overwrite a single file per table instead of writing dated snapshots (simple,
  loses history)
- Keep snapshots, select the latest by the `_FILE_NAME` pseudo-column (keeps an
  audit trail, more SQL)

### Model-level dbt tests (step 12)

All 27 existing tests are on **sources**. No `stg_`, `int_` or `mart_` model has
a single test, so `dbt build` validates the inputs and trusts every
transformation.

| Test | Where | Catches |
|---|---|---|
| `unique` | `date` on every `stg_` model | The duplication above — would have caught it on run two |
| `accepted_values` | `rba_decisions.change`, `sentiment.sentiment`, `ml_future_prediction.predicted_direction` | Junk categories, unexpected labels breaking the dashboard |
| `accepted_range` | `unemployment_rate` 0-20, `trimmed_mean_yoy` -5-20, `cash_rate` 0-20 | The positional `usecols` column shift. `not_null` passes on non-null nonsense; a range test does not |
| `relationships` | mart date -> `stg_rba_decisions` date | Mart rows with no decision behind them |
| row count > 0 | each mart | A model that silently returns nothing |

`accepted_range` needs `dbt_utils` — add a `packages.yml` and run `dbt deps`.

Sequencing note: step 11 is now fixed, so these can go straight in at the
default `error` severity - the data is genuinely clean.

### GitHub Actions (step 10)

There is currently no CI. Every deploy has been a manual `gcloud` command, and
`tests/` holds only a `.gitkeep`.

Not a blocker for the migration — sequence it after the Job runs. Proportionate
first workflow, on push:

- `docker build` — catches a broken Dockerfile before deploy rather than during
- `python -m py_compile` or `ruff` over `src/` and `main.py`
- `pytest` for the pure functions only: `clean()`, `package_data()`,
  `calculate_taylor_rule()` — input in, output out, no cloud calls

For a data pipeline, dbt tests catch more real problems than unit tests: the
risk is bad *data*, not bad *functions*. No pytest would catch the RBA
reordering a CSV column, but a dbt range test would.

Worth having for the portfolio regardless - CI/CD appears in most data
engineering job ads.

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
