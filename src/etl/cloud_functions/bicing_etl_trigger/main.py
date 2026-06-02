"""HTTP Cloud Function that launches the bicing_etl Dataflow Flex Template job."""
import logging
import os
from datetime import datetime, timedelta, timezone

import functions_framework
import google.auth
import google.auth.transport.requests
import requests

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
REGION = os.environ.get("GCP_REGION", "southamerica-west1")
RAW_BUCKET = os.environ.get("RAW_BUCKET", "proyecto-bicing-raw")
BQ_DATASET = os.environ.get("BQ_DATASET", "bicing_analytics")
TEMPLATE_IMAGE = os.environ["ETL_TEMPLATE_IMAGE"]
TEMP_GCS_LOCATION = os.environ["DATAFLOW_TEMP_LOCATION"]
DATAFLOW_WORKER_SA = os.environ["DATAFLOW_WORKER_SA"]


def _launch_flex_template(job_name: str, hour_str: str) -> str:
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
                "bucket": RAW_BUCKET,
                "bq_dataset": BQ_DATASET,
                "hour_utc": hour_str,
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
def bicing_etl_trigger(request):
    now = datetime.now(timezone.utc)
    hour_utc = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    hour_str = hour_utc.strftime("%Y-%m-%dT%H")
    job_name = f"bicing-etl-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    try:
        job_id = _launch_flex_template(job_name, hour_str)
        logger.info("Launched Dataflow job %s for hour %s", job_id, hour_str)
        return {"status": "ok", "job_id": job_id, "hour_utc": hour_str}, 200
    except Exception as exc:
        logger.error("Failed to launch Dataflow job: %s", exc)
        return {"error": str(exc)}, 500