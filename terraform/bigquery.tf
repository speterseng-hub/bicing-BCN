resource "google_bigquery_dataset" "analytics" {
  dataset_id = var.bq_dataset
  location   = var.region

  labels = {
    project = "bicing-bcn"
  }
}

resource "google_bigquery_table" "bicing_raw" {
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = "bicing_raw"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "timestamp"
  }

  clustering = ["station_id"]

  schema = jsonencode([
    { name = "station_id", type = "STRING", mode = "REQUIRED" },
    { name = "timestamp", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "num_bikes_available", type = "INTEGER", mode = "NULLABLE" },
    {
      name = "num_bikes_available_types", type = "RECORD", mode = "NULLABLE",
      fields = [
        { name = "mechanical", type = "INTEGER", mode = "NULLABLE" },
        { name = "ebike", type = "INTEGER", mode = "NULLABLE" },
      ]
    },
    { name = "num_docks_available", type = "INTEGER", mode = "NULLABLE" },
    { name = "is_installed", type = "BOOLEAN", mode = "NULLABLE" },
    { name = "is_renting", type = "BOOLEAN", mode = "NULLABLE" },
    { name = "is_returning", type = "BOOLEAN", mode = "NULLABLE" },
    { name = "last_reported", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "ingested_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}

resource "google_bigquery_table" "bicing_stations" {
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = "bicing_stations"
  deletion_protection = false

  schema = jsonencode([
    { name = "station_id", type = "STRING", mode = "REQUIRED" },
    { name = "name", type = "STRING", mode = "NULLABLE" },
    { name = "address", type = "STRING", mode = "NULLABLE" },
    { name = "lat", type = "FLOAT", mode = "NULLABLE" },
    { name = "lon", type = "FLOAT", mode = "NULLABLE" },
    { name = "capacity", type = "INTEGER", mode = "NULLABLE" },
    { name = "post_code", type = "STRING", mode = "NULLABLE" },
    { name = "district", type = "STRING", mode = "NULLABLE" },
    { name = "neighborhood", type = "STRING", mode = "NULLABLE" },
  ])
}
