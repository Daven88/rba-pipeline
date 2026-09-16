# Three service accounts, each with the narrowest role set that lets it do its
# job. None of them has a key: the pipeline and dashboard use their attached
# identity, and CI federates in from GitHub.

resource "google_service_account" "pipeline_runner" {
  account_id   = "rba-pipeline-runner"
  display_name = "RBA pipeline Cloud Run Job"
}

resource "google_service_account" "dashboard" {
  account_id   = "rba-dashboard"
  display_name = "RBA Dashboard (Streamlit)"
}

resource "google_service_account" "deployer" {
  account_id   = "rba-pipeline-deployer"
  display_name = "GitHub Actions deployer for rba-pipeline"
}

# The pipeline writes: it loads Silver, rebuilds the marts and saves the model.
resource "google_project_iam_member" "runner" {
  for_each = toset([
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/storage.objectAdmin",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.pipeline_runner.email}"
}

# The dashboard is public, so it is read-only by design. A bug in the app
# cannot mutate the warehouse.
resource "google_project_iam_member" "dashboard" {
  for_each = toset([
    "roles/bigquery.dataViewer",
    "roles/bigquery.jobUser",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.dashboard.email}"
}

# CI needs to push an image and update the job - nothing else.
resource "google_project_iam_member" "deployer" {
  for_each = toset([
    "roles/run.developer",
    "roles/artifactregistry.writer",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

# Deploying a job that runs as another identity requires permission to act as
# that identity. Without this the deploy fails with a confusing 403.
resource "google_service_account_iam_member" "deployer_acts_as_runner" {
  service_account_id = google_service_account.pipeline_runner.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

# --- Workload Identity Federation -------------------------------------------
# GitHub presents a short-lived OIDC token; GCP exchanges it for credentials.
# No key is ever created, so none can be leaked or forgotten.

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions-provider"
  display_name                       = "GitHub"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  # Without this condition ANY GitHub repository could exchange a token for
  # these credentials. It is the single most important line in this file.
  attribute_condition = "assertion.repository=='${var.github_repository}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_impersonates_deployer" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${var.project_number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}/attribute.repository/${var.github_repository}"
}
