resource "google_artifact_registry_repository" "images" {
  repository_id = "cloud-run-source-deploy"
  location      = var.region
  format        = "DOCKER"
  description   = "Container images for the pipeline job and the dashboard."

  # Every CI run pushes a SHA-tagged image and nothing removes the old ones -
  # the repository reached ~15 GB before this policy existed.
  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-old"
    action = "DELETE"
    condition {
      older_than = "2592000s" # 30 days
    }
  }
}

# The pipeline itself. Five stages plus `dbt build` run in sequence inside one
# container; there is no branching to orchestrate, which is why this replaced
# an Airflow DAG.
resource "google_cloud_run_v2_job" "pipeline" {
  name     = "rba-pipeline"
  location = var.region

  template {
    task_count = 1

    template {
      service_account = google_service_account.pipeline_runner.email
      timeout         = "1800s"
      max_retries     = 1

      containers {
        # Placeholder only. CI deploys a SHA-tagged image on every push to
        # master, so the live value is whatever the last green build produced -
        # see the ignore_changes block below.
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}/rba-pipeline:latest"

        resources {
          limits = {
            cpu    = "1"
            memory = "2Gi"
          }
        }

        # config/.env is gitignored and absent from the image, so bucket names
        # have to arrive as real environment variables.
        env {
          name  = "GCS_BRONZE_BUCKET"
          value = google_storage_bucket.bronze.name
        }
        env {
          name  = "GCS_SILVER_BUCKET"
          value = google_storage_bucket.silver.name
        }
        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
      }
    }
  }

  # Terraform owns the shape of this job; GitHub Actions owns which image it
  # runs. Without this, every `terraform apply` would roll the job back to the
  # placeholder tag and undo the last deploy.
  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image,
      client,
      client_version,
    ]
  }
}

# Cron cannot express "two days before an irregular date", so this fires every
# day and main.py decides whether today is a run day.
resource "google_cloud_scheduler_job" "daily" {
  name      = "rba-pipeline-daily"
  region    = var.region
  schedule  = "0 18 * * *"
  time_zone = "Australia/Sydney"

  description = "Fires daily; main.py gates on gold.rba_meeting_dates and exits unless today is T-2 or T+14 of an RBA meeting"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.pipeline.name}:run"

    oauth_token {
      service_account_email = google_service_account.pipeline_runner.email
    }
  }

  retry_config {
    max_backoff_duration = "3600s"
    min_backoff_duration = "5s"
    max_doublings        = 5
  }
}
