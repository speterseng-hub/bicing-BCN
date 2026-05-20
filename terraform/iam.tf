resource "google_service_account" "collector" {
  account_id   = "bicing-collector-sa"
  display_name = "Bicing Collector — Cloud Function SA"
}

resource "google_service_account" "writer" {
  account_id   = "bicing-writer-sa"
  display_name = "Bicing Writer — Cloud Function SA"
}

# collector: publish to Pub/Sub
resource "google_pubsub_topic_iam_member" "collector_publisher" {
  topic  = google_pubsub_topic.raw.id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.collector.email}"
}

# writer: write objects to raw GCS bucket
resource "google_storage_bucket_iam_member" "writer_storage" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.writer.email}"
}

# writer: insert rows into BigQuery
resource "google_bigquery_dataset_iam_member" "writer_bq" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.writer.email}"
}

# Cloud Scheduler needs to invoke bicing_collector (OIDC)
resource "google_service_account" "scheduler" {
  account_id   = "bicing-scheduler-sa"
  display_name = "Bicing Scheduler — invokes bicing_collector"
}

resource "google_cloudfunctions2_function_iam_member" "scheduler_invoker" {
  location       = var.region
  cloud_function = google_cloudfunctions2_function.collector.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_run_service_iam_member" "scheduler_run_invoker" {
  location = var.region
  service  = google_cloudfunctions2_function.collector.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

# writer SA needs to invoke its own CF (Pub/Sub push OIDC token)
resource "google_cloudfunctions2_function_iam_member" "pubsub_invoker" {
  location       = var.region
  cloud_function = google_cloudfunctions2_function.writer.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.writer.email}"
}

# Cloud Functions v2 runs on Cloud Run — Pub/Sub push also needs run.invoker
resource "google_cloud_run_service_iam_member" "pubsub_run_invoker" {
  location = var.region
  service  = google_cloudfunctions2_function.writer.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.writer.email}"
}
