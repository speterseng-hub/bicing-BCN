"""Dataflow Flex Template: reads hourly GCS files and loads into BigQuery bicing_raw."""
import argparse
import json
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import apache_beam as beam
from apache_beam.io.gcp.bigquery import BigQueryDisposition, WriteToBigQuery
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions

logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo("America/Santiago")
BQ_SCHEMA = {
    "fields": [
        {"name": "station_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "num_bikes_available", "type": "INTEGER", "mode": "NULLABLE"},
        {
            "name": "num_bikes_available_types",
            "type": "RECORD",
            "mode": "NULLABLE",
            "fields": [
                {"name": "mechanical", "type": "INTEGER", "mode": "NULLABLE"},
                {"name": "ebike", "type": "INTEGER", "mode": "NULLABLE"},
            ],
        },
        {"name": "num_docks_available", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "is_installed", "type": "BOOLEAN", "mode": "NULLABLE"},
        {"name": "is_renting", "type": "BOOLEAN", "mode": "NULLABLE"},
        {"name": "is_returning", "type": "BOOLEAN", "mode": "NULLABLE"},
        {"name": "last_reported", "type": "TIMESTAMP", "mode": "NULLABLE"},
        {"name": "ingested_at", "type": "TIMESTAMP", "mode": "REQUIRED"},
    ]
}


def gcs_prefix_for_hour(bucket: str, hour_utc: datetime) -> str:
    """Return the GCS prefix for a given UTC hour using America/Santiago local time."""
    local = hour_utc.astimezone(LOCAL_TZ)
    return f"gs://{bucket}/bicing/{local.strftime('%Y/%m/%d/%H')}/"


def parse_payload(payload: dict) -> list[dict]:
    """Transform a raw collector payload dict into a list of BQ-ready station rows.

    Pure function — no I/O. Safe to unit test without GCS or credentials.
    """
    collected_at = payload.get("collected_at", "")
    try:
        ingested_at = datetime.fromisoformat(collected_at.replace("Z", "+00:00")).isoformat()
    except (ValueError, AttributeError):
        ingested_at = datetime.now(timezone.utc).isoformat()

    stations = payload.get("data", {}).get("data", {}).get("stations", [])
    rows = []
    for station in stations:
        last_reported_raw = station.get("last_reported")
        if last_reported_raw is None:
            last_reported = None
        elif isinstance(last_reported_raw, (int, float)):
            last_reported = datetime.fromtimestamp(last_reported_raw, tz=timezone.utc).isoformat()
        else:
            last_reported = datetime.fromisoformat(
                str(last_reported_raw).replace("Z", "+00:00")
            ).isoformat()

        bike_types_raw = station.get("num_bikes_available_types")
        bike_types = (
            {
                "mechanical": bike_types_raw.get("mechanical"),
                "ebike": bike_types_raw.get("ebike"),
            }
            if isinstance(bike_types_raw, dict)
            else None
        )

        rows.append({
            "station_id": str(station["station_id"]),
            "timestamp": ingested_at,
            "num_bikes_available": station.get("num_bikes_available"),
            "num_bikes_available_types": bike_types,
            "num_docks_available": station.get("num_docks_available"),
            "is_installed": bool(station.get("is_installed")),
            "is_renting": bool(station.get("is_renting")),
            "is_returning": bool(station.get("is_returning")),
            "last_reported": last_reported,
            "ingested_at": ingested_at,
        })
    return rows


class ListGCSFiles(beam.DoFn):
    """Receives a GCS prefix and emits one path per matching object."""

    def process(self, prefix):
        from apache_beam.io.gcp import gcsio
        gcs = gcsio.GcsIO()
        try:
            files = list(gcs.list_prefix(prefix).keys())
        except Exception:
            files = []
        if not files:
            logger.warning("No files found at %s", prefix)
        yield from files


class ParseGCSFile(beam.DoFn):
    """Reads one GCS JSON file and emits one BQ row per station."""

    def process(self, gcs_path):
        from apache_beam.io.gcp import gcsio
        gcs = gcsio.GcsIO()
        try:
            with gcs.open(gcs_path) as f:
                payload = json.load(f)
        except Exception as exc:
            logger.error("Failed to read %s: %s", gcs_path, exc)
            return
        yield from parse_payload(payload)


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--bucket", required=True, help="Raw GCS bucket name (no gs:// prefix)")
    parser.add_argument("--bq_dataset", required=True)
    parser.add_argument(
        "--hour_utc",
        required=False,
        help="ISO hour to process e.g. 2026-05-21T03 (UTC). Defaults to previous hour.",
    )
    known_args, pipeline_args = parser.parse_known_args(argv)

    if known_args.hour_utc:
        hour_utc = datetime.fromisoformat(known_args.hour_utc).replace(tzinfo=timezone.utc)
    else:
        now = datetime.now(timezone.utc)
        hour_utc = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)

    prefix = gcs_prefix_for_hour(known_args.bucket, hour_utc)
    bq_table = f"{known_args.project}:{known_args.bq_dataset}.bicing_raw"

    options = PipelineOptions(pipeline_args)
    options.view_as(StandardOptions).runner = (
        options.view_as(StandardOptions).runner or "DataflowRunner"
    )

    with beam.Pipeline(options=options) as p:
        (
            p
            | "CreatePrefix" >> beam.Create([prefix])
            | "ListFiles"    >> beam.ParDo(ListGCSFiles())
            | "ParseFiles"   >> beam.ParDo(ParseGCSFile())
            | "WriteToBQ"    >> WriteToBigQuery(
                bq_table,
                schema=BQ_SCHEMA,
                write_disposition=BigQueryDisposition.WRITE_APPEND,
                create_disposition=BigQueryDisposition.CREATE_NEVER,
            )
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
