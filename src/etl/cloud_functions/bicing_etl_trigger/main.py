"""HTTP Cloud Function that launches the bicing_etl Dataflow Flex Template job."""
import logging
import os
from datetime import datetime, timedelta, timezone

import functions_framework
from google.cloud import dataflow_v1beta3

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
REGION = os.environ.get("GCP_REGION", "southamerica-west1")
RAW_BUCKET = os.environ.get("RAW_BUCKET", "proyecto-bicing-raw")
BQ_DATASET = os.environ.get("BQ_DATASET", "bicing_analytics")
TEMPLATE_IMAGE = os.environ["ETL_TEMPLATE_IMAGE"]
TEMP_GCS_LOCATION = os.environ["DATAFLOW_TEMP_LOCATION"]


@functions_framework.http
def bicing_etl_trigger(request):
    now = datetime.now(timezone.utc)
    hour_utc = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    hour_str = hour_utc.strftime("%Y-%m-%dT%H")
    job_name = f"bicing-etl-{hour_utc.strftime('%Y%m%d-%H%M%S')}"

    client = dataflow_v1beta3.FlexTemplatesServiceClient()
    request_body = dataflow_v1beta3.LaunchFlexTemplateRequest(
        project_id=PROJECT_ID,
        location=REGION,
        launch_parameter=dataflow_v1beta3.LaunchFlexTemplateParameter(
            job_name=job_name,
            container_spec_gcs_path=TEMPLATE_IMAGE,
            parameters={
                "project": PROJECT_ID,
                "bucket": RAW_BUCKET,
                "bq_dataset": BQ_DATASET,
                "hour_utc": hour_str,
                "region": REGION,
                "temp_location": TEMP_GCS_LOCATION,
            },
        ),
    )

    try:
        response = client.launch_flex_template(request=request_body)
        job_id = response.job.id
        logger.info("Launched Dataflow job %s for hour %s", job_id, hour_str)
        return {"status": "ok", "job_id": job_id, "hour_utc": hour_str}, 200
    except Exception as exc:
        logger.error("Failed to launch Dataflow job: %s", exc)
        return {"error": str(exc)}, 500