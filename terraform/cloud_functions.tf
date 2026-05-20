# ── Zip and upload Cloud Function source code ─────────────────────────────────

data "archive_file" "collector_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../src/ingestion/cloud_functions/bicing_collector"
  output_path = "${path.root}/.build/bicing_collector.zip"
}

data "archive_file" "writer_zip" {
  type        = "zip"
  source_dir  = "${path.root}/../src/ingestion/cloud_functions/bicing_writer"
  output_path = "${path.root}/.build/bicing_writer.zip"
}

resource "google_storage_bucket_object" "collector_source" {
  name   = "bicing_collector_${data.archive_file.collector_zip.output_md5}.zip"
  bucket = google_storage_bucket.cf_source.name
  source = data.archive_file.collector_zip.output_path
}

resource "google_storage_bucket_object" "writer_source" {
  name   = "bicing_writer_${data.archive_file.writer_zip.output_md5}.zip"
  bucket = google_storage_bucket.cf_source.name
  source = data.archive_file.writer_zip.output_path
}

# ── bicing_collector ──────────────────────────────────────────────────────────

resource "google_cloudfunctions2_function" "collector" {
  name        = "bicing-collector"
  location    = var.region
  depends_on  = [google_project_service.apis]
  description = "Fetches Bicing GBFS station_status and publishes to Pub/Sub"

  build_config {
    runtime     = "python312"
    entry_point = "bicing_collector"

    source {
      storage_source {
        bucket = google_storage_bucket.cf_source.name
        object = google_storage_bucket_object.collector_source.name
      }
    }
  }

  service_config {
    min_instance_count    = 0
    max_instance_count    = 3
    timeout_seconds       = 60
    available_memory      = "256M"
    service_account_email = google_service_account.collector.email

    environment_variables = {
      GCP_PROJECT_ID      = var.project_id
      PUBSUB_TOPIC        = var.pubsub_topic
      GBFS_DISCOVERY_URL  = "https://santiago.publicbikesystem.net/customer/gbfs/v3.0/gbfs.json"
    }
  }
}

# ── bicing_writer ─────────────────────────────────────────────────────────────

resource "google_cloudfunctions2_function" "writer" {
  name        = "bicing-writer"
  location    = var.region
  depends_on  = [google_project_service.apis]
  description = "Receives Pub/Sub messages and writes raw JSON to GCS"

  build_config {
    runtime     = "python312"
    entry_point = "bicing_writer"

    source {
      storage_source {
        bucket = google_storage_bucket.cf_source.name
        object = google_storage_bucket_object.writer_source.name
      }
    }
  }

  service_config {
    min_instance_count    = 0
    max_instance_count    = 10
    timeout_seconds       = 60
    available_memory      = "256M"
    service_account_email = google_service_account.writer.email

    environment_variables = {
      RAW_BUCKET = var.raw_bucket_name
    }
  }
}

# ── Cloud Scheduler ───────────────────────────────────────────────────────────

resource "google_cloud_scheduler_job" "collector_trigger" {
  name             = "bicing-collector-trigger"
  description      = "Triggers bicing_collector every 5 minutes"
  region           = var.scheduler_region
  schedule         = "*/5 * * * *"
  time_zone        = "Europe/Madrid"
  attempt_deadline = "30s"

  retry_config {
    retry_count = 3
  }

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.collector.service_config[0].uri

    oidc_token {
      service_account_email = google_service_account.scheduler.email
    }
  }
}
