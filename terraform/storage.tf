# Bronze holds raw CSV exactly as the RBA published it. Silver holds one
# cleaned Parquet per table, overwritten each run - dated snapshots were
# removed once external tables started globbing five copies of the history.
resource "google_storage_bucket" "bronze" {
  provider = google.storage

  name                        = "rba-pipeline-bronze"
  location                    = "US"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = false
  force_destroy               = false
}

resource "google_storage_bucket" "silver" {
  provider = google.storage

  name                        = "rba-pipeline-silver"
  location                    = "US"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = false
  force_destroy               = false
}

# Gold. Every dbt model and the ML outputs land here. Note this is in
# australia-southeast1 while the buckets above are in US - a cross-region read
# on every external table scan, inherited rather than chosen.
resource "google_bigquery_dataset" "gold" {
  dataset_id  = "gold"
  location    = var.region
  description = "Modelled tables and ML outputs, built by dbt."
}
