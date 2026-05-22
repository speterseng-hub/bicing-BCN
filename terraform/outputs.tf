output "raw_bucket_url" {
  description = "GCS URL of the raw data bucket"
  value       = "gs://${google_storage_bucket.raw.name}"
}

output "pubsub_topic_id" {
  description = "Pub/Sub topic ID"
  value       = google_pubsub_topic.raw.id
}

output "bq_dataset_id" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.analytics.dataset_id
}

output "collector_sa_email" {
  description = "Service account email for bicing_collector"
  value       = google_service_account.collector.email
}

output "writer_sa_email" {
  description = "Service account email for bicing_writer"
  value       = google_service_account.writer.email
}

output "dataflow_bucket_url" {
  description = "GCS URL of the Dataflow staging/temp/template bucket"
  value       = "gs://${google_storage_bucket.dataflow.name}"
}

output "artifact_registry_repo" {
  description = "Artifact Registry repository for Dataflow Flex Template images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/bicing-dataflow"
}

output "dataflow_worker_sa_email" {
  description = "Service account email for Dataflow worker"
  value       = google_service_account.dataflow_worker.email
}
