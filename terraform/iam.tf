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

# ── ETL trigger SA — launches Dataflow jobs and reads GCS ─────────────────────

resource "google_service_account" "etl_trigger" {
  account_id   = "bicing-etl-trigger-sa"
  display_name = "Bicing ETL Trigger — launches Dataflow Flex Template jobs"
}

# launch Dataflow jobs
resource "google_project_iam_member" "etl_trigger_dataflow_developer" {
  project = var.project_id
  role    = "roles/dataflow.developer"
  member  = "serviceAccount:${google_service_account.etl_trigger.email}"
}

# Dataflow worker SA needs to be impersonated by the trigger SA
resource "google_service_account_iam_member" "etl_trigger_act_as_worker" {
  service_account_id = google_service_account.dataflow_worker.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.etl_trigger.email}"
}

# ── Dataflow worker SA — runs the actual pipeline ─────────────────────────────

resource "google_service_account" "dataflow_worker" {
  account_id   = "bicing-dataflow-worker-sa"
  display_name = "Bicing Dataflow Worker — executes ETL pipelines"
}

# read raw GCS files
resource "google_storage_bucket_iam_member" "dataflow_worker_raw_reader" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.dataflow_worker.email}"
}

# read/write Dataflow staging and temp bucket
resource "google_storage_bucket_iam_member" "dataflow_worker_staging" {
  bucket = google_storage_bucket.dataflow.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.dataflow_worker.email}"
}

# write to BigQuery
resource "google_bigquery_dataset_iam_member" "dataflow_worker_bq" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.dataflow_worker.email}"
}

# Dataflow worker needs Dataflow worker role
resource "google_project_iam_member" "dataflow_worker_role" {
  project = var.project_id
  role    = "roles/dataflow.worker"
  member  = "serviceAccount:${google_service_account.dataflow_worker.email}"
}

# ── ETL Scheduler SA — invokes the trigger Cloud Functions ────────────────────

resource "google_service_account" "etl_scheduler" {
  account_id   = "bicing-etl-scheduler-sa"
  display_name = "Bicing ETL Scheduler — invokes ETL trigger CFs"
}

resource "google_cloudfunctions2_function_iam_member" "etl_scheduler_invoker" {
  location       = var.region
  cloud_function = google_cloudfunctions2_function.etl_trigger.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.etl_scheduler.email}"
}

resource "google_cloud_run_service_iam_member" "etl_scheduler_run_invoker" {
  location = var.region
  service  = google_cloudfunctions2_function.etl_trigger.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.etl_scheduler.email}"
}
