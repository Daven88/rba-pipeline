terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # State lives in GCS, versioned, so a corrupted or lost local state is
  # recoverable. The bucket is deliberately NOT managed by this configuration -
  # Terraform cannot create the bucket that holds its own state.
  backend "gcs" {
    bucket = "rba-pipeline-tfstate"
    prefix = "rba-pipeline"
  }
}

# Most resources live in the warehouse/compute project.
provider "google" {
  project = var.project_id
  region  = var.region
}

# The GCS buckets predate that project and live in a second one. Two projects
# both named "rba-pipeline" is a historical accident, not a design.
provider "google" {
  alias   = "storage"
  project = var.storage_project_id
  region  = var.region
}
