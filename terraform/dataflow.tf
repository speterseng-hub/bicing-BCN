# ── Artifact Registry — Docker images for Dataflow Flex Templates ─────────────

resource "google_artifact_registry_repository" "dataflow" {
  repository_id = "bicing-dataflow"
  location      = var.region
  format        = "DOCKER"
  description   = "Dataflow Flex Template images for Bicing ETL pipelines"
  depends_on    = [google_project_service.apis]
}

# ── GCS — Flex Template spec files and Dataflow temp/staging ──────────────────

resource "google_storage_bucket" "dataflow" {
  name                        = "${var.project_id}-dataflow"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
}

# ── Cloud Function zips ────────────────────────────────────────────────────────

data "archive_file" "etl_trigger_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../src/etl/cloud_functions/bicing_etl_trigger"
  output_path = "${path.root}/.build/bicing_etl_trigger.zip"
}

data "archive_file" "stations_trigger_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../src/etl/cloud_functions/bicing_stations_trigger"
  output_path = "${path.root}/.build/bicing_stations_trigger.zip"
}

resource "google_storage_bucket_object" "etl_trigger_source" {
  name   = "bicing_etl_trigger_${data.archive_file.etl_trigger_zip.output_md5}.zip"
  bucket = google_storage_bucket.cf_source.name
  source = data.archive_file.etl_trigger_zip.output_path
}

resource "google_storage_bucket_object" "stations_trigger_source" {
  name   = "bicing_stations_trigger_${data.archive_file.stations_trigger_zip.output_md5}.zip"
  bucket = google_storage_bucket.cf_source.name
  source = data.archive_file.stations_trigger_zip.output_path
}

# ── bicing_etl_trigger Cloud Function ─────────────────────────────────────────

resource "google_cloudfunctions2_function" "etl_trigger" {
  name        = "bicing-etl-trigger"
  location    = var.region
  depends_on  = [google_project_service.apis]
  description = "Launches bicing_etl Dataflow Flex Template for the previous hour"

  build_config {
    runtime     = "python312"
    entry_point = "bicing_etl_trigger"

    source {
      storage_source {
        bucket = google_storage_bucket.cf_source.name
        object = google_storage_bucket_object.etl_trigger_source.name
      }
    }
  }

  service_config {
    min_instance_count    = 0
    max_instance_count    = 1
    timeout_seconds       = 120
    available_memory      = "256M"
    service_account_email = google_service_account.etl_trigger.email

    environment_variables = {
      GCP_PROJECT_ID        = var.project_id
      GCP_REGION            = var.region
      RAW_BUCKET            = var.raw_bucket_name
      BQ_DATASET            = var.bq_dataset
      ETL_TEMPLATE_IMAGE    = "gs://${google_storage_bucket.dataflow.name}/templates/bicing_etl.json"
      DATAFLOW_TEMP_LOCATION = "gs://${google_storage_bucket.dataflow.name}/temp"
    }
  }
}

# ── bicing_stations_trigger Cloud Function ────────────────────────────────────

resource "google_cloudfunctions2_function" "stations_trigger" {
  name        = "bicing-stations-trigger"
  location    = var.region
  depends_on  = [google_project_service.apis]
  description = "Launches bicing_stations Dataflow Flex Template"

  build_config {
    runtime     = "python312"
    entry_point = "bicing_stations_trigger"

    source {
      storage_source {
        bucket = google_storage_bucket.cf_source.name
        object = google_storage_bucket_object.stations_trigger_source.name
      }
    }
  }

  service_config {
    min_instance_count    = 0
    max_instance_count    = 1
    timeout_seconds       = 120
    available_memory      = "256M"
    service_account_email = google_service_account.etl_trigger.email

    environment_variables = {
      GCP_PROJECT_ID           = var.project_id
      GCP_REGION               = var.region
      BQ_DATASET               = var.bq_dataset
      STATIONS_TEMPLATE_IMAGE  = "gs://${google_storage_bucket.dataflow.name}/templates/bicing_stations.json"
      DATAFLOW_TEMP_LOCATION   = "gs://${google_storage_bucket.dataflow.name}/temp"
      GBFS_DISCOVERY_URL       = "https://santiago.publicbikesystem.net/customer/gbfs/v3.0/gbfs.json"
    }
  }
}

# ── Cloud Scheduler — hourly ETL trigger ──────────────────────────────────────

resource "google_cloud_scheduler_job" "etl_trigger" {
  name             = "bicing-etl-trigger"
  description      = "Triggers bicing_etl Dataflow job every hour"
  region           = var.scheduler_region
  schedule         = "5 * * * *"
  time_zone        = "UTC"
  attempt_deadline = "30s"

  retry_config {
    retry_count = 2
  }

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.etl_trigger.service_config[0].uri

    oidc_token {
      service_account_email = google_service_account.etl_scheduler.email
    }
  }
}
