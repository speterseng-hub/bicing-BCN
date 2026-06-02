# Bicing — Data Engineering Pipeline

End-to-end GCP data pipeline for real-time ingestion and analysis of
GBFS-compliant bike-sharing system data. Currently targeting Santiago de Chile.

## Architecture

```
Cloud Scheduler (every 5 min)
     │
     ▼
Cloud Function: bicing_collector   ← fetches GBFS API
     │
     ▼
Pub/Sub: bicing-raw-data           ← decoupled messaging + dead-letter
     │
     ▼
Cloud Function: bicing_writer      ← writes raw JSON to GCS
     │
     ▼
Cloud Storage: proyecto-bicing-raw
     │
     ▼
BigQuery: bicing_analytics         ← queryable warehouse
```

## Project Structure

```
src/ingestion/cloud_functions/   Cloud Functions source code (collector, writer)
src/etl/dataflow/                Dataflow Flex Templates (bicing_etl, bicing_stations)
src/etl/cloud_functions/         ETL trigger Cloud Functions
terraform/                       Infrastructure as Code (GCP resources)
config/                          Environment configuration
tests/                           Unit and integration tests
```

## Setup

### Prerequisites
- GCP project with billing enabled
- `gcloud` CLI authenticated (`gcloud auth application-default login`)
- Terraform >= 1.5
- Python 3.12

### Configure

1. Copy `terraform/terraform.tfvars.example` to `terraform/terraform.tfvars` and fill in your values.
2. Create the Terraform state bucket manually (required before `terraform init`):
   ```bash
   gcloud storage buckets create gs://YOUR_PROJECT_ID-tfstate \
     --location=southamerica-west1 --uniform-bucket-level-access
   ```
3. Update `backend "gcs"` bucket name in `terraform/main.tf`.

### Deploy infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### Deploy Cloud Functions

Cloud Functions are deployed automatically via Terraform from zipped source in GCS.

### Run locally

```bash
pip install -r requirements.txt
cd src/ingestion/cloud_functions/bicing_collector
functions-framework --target=bicing_collector
```

`--debug` enables hot reload on code changes but may cause issues on Windows. Omit it if the server restarts in a loop.

Test the running function:
```bash
curl -X POST http://localhost:8080
```

### Run ETL pipelines locally

Both pipelines use `DirectRunner` for local execution and write directly to BigQuery.

**Station metadata** (run once, or when station data changes):
```bash
python src/etl/dataflow/bicing_stations/main.py \
  --project=YOUR_PROJECT_ID \
  --bucket=proyecto-bicing-raw \
  --bq_dataset=bicing_analytics \
  --runner=DirectRunner \
  --temp_location=gs://proyecto-bicing-raw/tmp
```

**Hourly availability** (processes one UTC hour of GCS files):
```bash
python src/etl/dataflow/bicing_etl/main.py \
  --project=YOUR_PROJECT_ID \
  --bucket=proyecto-bicing-raw \
  --bq_dataset=bicing_analytics \
  --runner=DirectRunner \
  --temp_location=gs://proyecto-bicing-raw/tmp \
  --hour_utc=2026-06-01T03
```

`--hour_utc` defaults to the previous hour if omitted. `--temp_location` is required for the BQ file-load method even with `DirectRunner`.

### Query BigQuery

```bash
# Latest availability rows
bq query --use_legacy_sql=false \
  "SELECT * FROM \`YOUR_PROJECT_ID.bicing_analytics.bicing_raw\` ORDER BY timestamp DESC LIMIT 10"

# Station metadata
bq query --use_legacy_sql=false \
  "SELECT * FROM \`YOUR_PROJECT_ID.bicing_analytics.bicing_stations\` LIMIT 10"
```

## Data Sources

- **Bicing (Santiago)**: `https://santiago.publicbikesystem.net/customer/gbfs/v3.0/gbfs.json`
- Feed: GBFS v3.0 — `station_status` + `station_information`

## Cost Estimate (5-min polling)

| Service | Est. Cost/month |
|---|---|
| Cloud Functions | ~$0 (free tier) |
| Pub/Sub | ~$0.30 |
| Cloud Storage | ~$1 |
| BigQuery | ~$0 (free tier queries) |
| **Total** | **~$1–5/month** |
