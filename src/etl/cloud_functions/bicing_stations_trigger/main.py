"""HTTP Cloud Function that launches the bicing_stations Dataflow Flex Template job."""
import logging
import os
from datetime import datetime, timezone

import functions_framework
import google.auth
import google.auth.transport.requests
import requests

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
REGION = os.environ.get("GCP_REGION", "southamerica-west1")
BQ_DATASET = os.environ.get("BQ_DATASET", "bicing_analytics")
TEMPLATE_IMAGE = os.environ["STATIONS_TEMPLATE_IMAGE"]
TEMP_GCS_LOCATION = os.environ["DATAFLOW_TEMP_LOCATION"]
DATAFLOW_WORKER_SA = os.environ["DATAFLOW_WORKER_SA"]
GBFS_DISCOVERY_URL = os.environ.get(
    "GBFS_DISCOVERY_URL",
    "https://santiago.publicbikesystem.net/customer/gbfs/v3.0/gbfs.json",
)


def _launch_flex_template(job_name: str) -> str:
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(google.auth.transport.requests.Request())

    url = (
        f"https://dataflow.googleapis.com/v1b3/projects/{PROJECT_ID}"
        f"/locations/{REGION}/flexTemplates:launch"
    )
    body = {
        "launchParameter": {
            "jobName": job_name,
            "containerSpecGcsPath": TEMPLATE_IMAGE,
            "parameters": {
                "project": PROJECT_ID,
                "bq_dataset": BQ_DATASET,
                "discovery_url": GBFS_DISCOVERY_URL,
            },
            "environment": {
                "tempLocation": TEMP_GCS_LOCATION,
                "stagingLocation": TEMP_GCS_LOCATION.rstrip("/") + "/staging",
                "serviceAccountEmail": DATAFLOW_WORKER_SA,
            },
        }
    }
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=body, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["job"]["id"]


@functions_framework.http
def bicing_stations_trigger(request):
    job_name = f"bicing-stations-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    try:
        job_id = _launch_flex_template(job_name)
        logger.info("Launched stations Dataflow job %s", job_id)
        return {"status": "ok", "job_id": job_id}, 200
    except Exception as exc:
        logger.error("Failed to launch Dataflow job: %s", exc)
        return {"error": str(exc)}, 500