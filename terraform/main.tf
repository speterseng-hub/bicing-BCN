terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # The state bucket must exist before running terraform init.
  # Create it manually once:
  #   gcloud storage buckets create gs://<YOUR_PROJECT_ID>-tfstate \
  #     --location=southamerica-west1 --uniform-bucket-level-access
  # Then replace YOUR_PROJECT_ID below.
  # Replace YOUR_PROJECT_ID with your actual GCP project ID before running terraform init.
  # Create the bucket first: gcloud storage buckets create gs://YOUR_PROJECT_ID-tfstate \
  #   --location=southamerica-west1 --uniform-bucket-level-access
  backend "gcs" {
    bucket = "YOUR_PROJECT_ID-tfstate"
    prefix = "bicing/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
