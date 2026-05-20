import json
import logging
import os
from datetime import datetime, timezone

import functions_framework
import requests
from google.cloud import pubsub_v1

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
logger = logging.getLogger(__name__)

PUBSUB_TOPIC = os.environ.get("PUBSUB_TOPIC", "bicing-raw-data")
GBFS_DISCOVERY_URL = os.environ.get(
    "GBFS_DISCOVERY_URL",
    "https://santiago.publicbikesystem.net/customer/gbfs/v3.0/gbfs.json",
)
REQUEST_TIMEOUT = 10


def _get_feed_url(discovery_url: str, feed_name: str) -> str:
    resp = requests.get(discovery_url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    feeds = resp.json()["data"]["feeds"]
    for feed in feeds:
        if feed["name"] == feed_name:
            return feed["url"]
    raise ValueError(f"Feed '{feed_name}' not found in GBFS discovery document")


def _fetch_feed(url: str) -> dict:
    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _publish(publisher: pubsub_v1.PublisherClient, topic_path: str, payload: dict) -> str:
    data = json.dumps(payload).encode("utf-8")
    future = publisher.publish(topic_path, data=data)
    return future.result()


@functions_framework.http
def bicing_collector(request):
    """HTTP-triggered Cloud Function. Fetches Bicing GBFS station_status and
    publishes the raw payload to Pub/Sub."""
    collected_at = datetime.now(timezone.utc).isoformat()

    try:
        status_url = _get_feed_url(GBFS_DISCOVERY_URL, "station_status")
        raw_data = _fetch_feed(status_url)
    except requests.RequestException as exc:
        logger.error("Failed to fetch Bicing API: %s", exc)
        return {"error": str(exc)}, 502
    except ValueError as exc:
        logger.error("GBFS discovery error: %s", exc)
        return {"error": str(exc)}, 500

    payload = {
        "collected_at": collected_at,
        "feed": "station_status",
        "source_url": GBFS_DISCOVERY_URL,
        "data": raw_data,
    }

    project_id = os.environ["GCP_PROJECT_ID"]
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, PUBSUB_TOPIC)

    try:
        message_id = _publish(publisher, topic_path, payload)
        logger.info("Published message %s at %s", message_id, collected_at)
    except Exception as exc:
        logger.error("Failed to publish to Pub/Sub: %s", exc)
        return {"error": str(exc)}, 500

    return {"status": "ok", "message_id": message_id, "collected_at": collected_at}, 200
