# Bicing Barcelona — Data Engineering Pipeline

End-to-end GCP data pipeline for real-time ingestion and analysis of Barcelona's
Bicing bike-sharing system data.

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
src/ingestion/cloud_functions/   Cloud Functions source code
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
   gcloud storage buckets create gs://YOUR_PROJECT_ID-tfstate --location=southamerica-west1
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
functions-framework --target=bicing_collector --debug
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
