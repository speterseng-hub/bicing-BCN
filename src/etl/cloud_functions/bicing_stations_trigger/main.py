"""HTTP Cloud Function that launches the bicing_stations Dataflow Flex Template job."""
import logging
import os
from datetime import datetime, timezone

import functions_framework
from google.cloud import dataflow_v1beta3

logger = logging.getLogger(__name__)

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
REGION = os.environ.get("GCP_REGION", "southamerica-west1")
BQ_DATASET = os.environ.get("BQ_DATASET", "bicing_analytics")
TEMPLATE_IMAGE = os.environ["STATIONS_TEMPLATE_IMAGE"]
TEMP_GCS_LOCATION = os.environ["DATAFLOW_TEMP_LOCATION"]
GBFS_DISCOVERY_URL = os.environ.get(
    "GBFS_DISCOVERY_URL",
    "https://santiago.publicbikesystem.net/customer/gbfs/v3.0/gbfs.json",
)


@functions_framework.http
def bicing_stations_trigger(request):
    job_name = f"bicing-stations-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    client = dataflow_v1beta3.FlexTemplatesServiceClient()
    request_body = dataflow_v1beta3.LaunchFlexTemplateRequest(
        project_id=PROJECT_ID,
        location=REGION,
        launch_parameter=dataflow_v1beta3.LaunchFlexTemplateParameter(
            job_name=job_name,
            container_spec_gcs_path=TEMPLATE_IMAGE,
            parameters={
                "project": PROJECT_ID,
                "bq_dataset": BQ_DATASET,
                "discovery_url": GBFS_DISCOVERY_URL,
                "region": REGION,
                "temp_location": TEMP_GCS_LOCATION,
            },
        ),
    )

    try:
        response = client.launch_flex_template(request=request_body)
        job_id = response.job.id
        logger.info("Launched stations Dataflow job %s", job_id)
        return {"status": "ok", "job_id": job_id}, 200
    except Exception as exc:
        logger.error("Failed to launch Dataflow job: %s", exc)
        return {"error": str(exc)}, 500