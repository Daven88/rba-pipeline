# Public Streamlit dashboard. Deployed by hand from the streamlit/ directory
# rather than by CI, so Terraform describes its shape and leaves the image
# alone in the same way as the job.
resource "google_cloud_run_v2_service" "dashboard" {
  name                = "rba-dashboard"
  location            = var.region
  deletion_protection = true
  ingress             = "INGRESS_TRAFFIC_ALL"

  # Service-level scaling, distinct from template.scaling below. Google returns
  # this block populated with zeros whether or not you set it, so declaring it
  # explicitly is what stops a perpetual diff.
  scaling {
    min_instance_count = 0
  }

  template {
    service_account                  = google_service_account.dashboard.email
    max_instance_request_concurrency = 80

    # Streamlit keeps per-session state over a websocket, so a viewer has to
    # keep hitting the same instance once more than one is running.
    session_affinity = true

    # A portfolio dashboard does not need twenty instances. Capping this low
    # bounds the Cloud Run bill if the page is ever hammered - each instance
    # can still serve 80 concurrent viewers.
    scaling {
      max_instance_count = 3
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}/rba-dashboard:latest"

      resources {
        limits = {
          cpu    = "1000m"
          memory = "512Mi"
        }
        # CPU is throttled between requests - this is a dashboard that sits idle
        # most of the time, and billing follows CPU allocation.
        cpu_idle          = true
        startup_cpu_boost = true
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version,
      # Written by `gcloud run deploy --source`, which uploads a zip and records
      # the build that produced the image. Terraform cannot reproduce it and
      # should not try to delete it.
      build_config,
    ]
  }
}

# Deliberately public - it is a portfolio piece. Safe because the identity it
# runs as holds only bigquery.dataViewer and bigquery.jobUser, so the worst a
# bug can do is read.
resource "google_cloud_run_v2_service_iam_member" "dashboard_public" {
  name     = google_cloud_run_v2_service.dashboard.name
  location = google_cloud_run_v2_service.dashboard.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
