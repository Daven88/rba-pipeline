variable "project_id" {
  description = "Project holding BigQuery, Cloud Run, Scheduler and the service accounts."
  type        = string
  default     = "rba-pipeline-494410"
}

variable "project_number" {
  description = "Numeric id of project_id, needed to build the workload identity principalSet."
  type        = string
  default     = "213888644789"
}

variable "storage_project_id" {
  description = "Separate project that owns the Bronze and Silver buckets."
  type        = string
  default     = "rba-pipeline"
}

variable "region" {
  description = "Region for Cloud Run, Scheduler, Artifact Registry and BigQuery."
  type        = string
  default     = "australia-southeast1"
}

variable "github_repository" {
  description = "owner/name of the repo allowed to impersonate the deployer service account."
  type        = string
  default     = "Daven88/rba-pipeline"
}
