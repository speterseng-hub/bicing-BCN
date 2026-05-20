variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "southamerica-west1"
}

variable "raw_bucket_name" {
  description = "GCS bucket for raw Bicing data"
  type        = string
  default     = "proyecto-bicing-raw"
}

variable "cf_source_bucket_name" {
  description = "GCS bucket for Cloud Function source zips"
  type        = string
}

variable "pubsub_topic" {
  description = "Pub/Sub topic for raw Bicing data"
  type        = string
  default     = "bicing-raw-data"
}

variable "bq_dataset" {
  description = "BigQuery dataset for analytics"
  type        = string
  default     = "bicing_analytics"
}

variable "scheduler_region" {
  description = "Region for Cloud Scheduler (must be a region where Scheduler is available)"
  type        = string
  default     = "southamerica-east1"
}
