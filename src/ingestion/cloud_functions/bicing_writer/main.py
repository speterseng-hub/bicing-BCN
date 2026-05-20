import base64
import json
import logging
import os
from datetime import datetime, timezone

import functions_framework
from google.cloud import storage

logger = logging.getLogger(__name__)

RAW_BUCKET = os.environ.get("RAW_BUCKET", "proyecto-bicing-raw")


def _build_gcs_path(collected_at: str | None = None) -> str:
    if collected_at:
        try:
            ts = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
        except ValueError:
            ts = datetime.now(timezone.utc)
    else:
        ts = datetime.now(timezone.utc)

    return (
        f"bicing/{ts.strftime('%Y/%m/%d/%H')}/"
        f"bicing_{ts.strftime('%Y%m%d_%H%M%S')}.json"
    )


def _write_to_gcs(bucket_name: str, blob_path: str, payload: dict) -> None:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.upload_from_string(
        json.dumps(payload, ensure_ascii=False),
        content_type="application/json",
    )


@functions_framework.http
def bicing_writer(request):
    """HTTP-triggered Cloud Function acting as Pub/Sub push subscriber.
    Decodes the Pub/Sub envelope, extracts the payload, and writes it to GCS."""
    envelope = request.get_json(silent=True)
    if not envelope or "message" not in envelope:
        logger.error("Invalid Pub/Sub envelope: %s", envelope)
        return {"error": "invalid envelope"}, 400

    message = envelope["message"]
    try:
        raw_bytes = base64.b64decode(message.get("data", ""))
        payload = json.loads(raw_bytes)
    except Exception as exc:
        logger.error("Failed to decode Pub/Sub message: %s", exc)
        return {"error": str(exc)}, 400

    collected_at = payload.get("collected_at")
    gcs_path = _build_gcs_path(collected_at)

    try:
        _write_to_gcs(RAW_BUCKET, gcs_path, payload)
        logger.info("Written to gs://%s/%s", RAW_BUCKET, gcs_path)
    except Exception as exc:
        logger.error("GCS write failed: %s", exc)
        # Return 500 so Pub/Sub retries delivery
        return {"error": str(exc)}, 500

    return {"status": "ok", "path": gcs_path}, 200
