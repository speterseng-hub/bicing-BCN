import os

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
REGION = os.environ.get("GCP_REGION", "southamerica-west1")

PUBSUB_TOPIC = os.environ.get("PUBSUB_TOPIC", "bicing-raw-data")
RAW_BUCKET = os.environ.get("RAW_BUCKET", "proyecto-bicing-raw")

GBFS_DISCOVERY_URL = "https://santiago.publicbikesystem.net/customer/gbfs/v3.0/gbfs.json"
GBFS_TIMEOUT = 10

GCS_PATH_PREFIX = "bicing"
