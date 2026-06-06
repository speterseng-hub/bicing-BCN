#!/usr/bin/env bash
set -euo pipefail

PROJECT="${GCP_PROJECT_ID:?GCP_PROJECT_ID env var is required}"
REGION="${GCP_REGION:-southamerica-west1}"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT}/bicing-dataflow"
BUCKET="gs://${PROJECT}-dataflow"

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

docker build -t "${REGISTRY}/bicing-etl:latest" src/etl/dataflow/bicing_etl
docker push "${REGISTRY}/bicing-etl:latest"

docker build -t "${REGISTRY}/bicing-stations:latest" src/etl/dataflow/bicing_stations
docker push "${REGISTRY}/bicing-stations:latest"

gcloud dataflow flex-template build \
    "${BUCKET}/templates/bicing_etl.json" \
    --image="${REGISTRY}/bicing-etl:latest" \
    --sdk-language=PYTHON \
    --metadata-file=src/etl/dataflow/bicing_etl/template_metadata.json \
    --project="${PROJECT}"

gcloud dataflow flex-template build \
    "${BUCKET}/templates/bicing_stations.json" \
    --image="${REGISTRY}/bicing-stations:latest" \
    --sdk-language=PYTHON \
    --metadata-file=src/etl/dataflow/bicing_stations/template_metadata.json \
    --project="${PROJECT}"

echo "Done — both templates uploaded to ${BUCKET}/templates/"
