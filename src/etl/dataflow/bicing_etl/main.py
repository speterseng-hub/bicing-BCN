"""Dataflow Flex Template: reads daily GCS files and loads into BigQuery bicing_raw."""
import argparse
import json
import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import apache_beam as beam
from apache_beam.io.gcp.bigquery import BigQueryDisposition, WriteToBigQuery
from apache_beam.options.pipeline_options import GoogleCloudOptions, PipelineOptions, StandardOptions

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


def gcs_prefixes_for_date(bucket: str, local_date: date) -> list[str]:
    """Return the 24 GCS prefixes for a given America/Santiago local date."""
    base = local_date.strftime("%Y/%m/%d")
    return [f"gs://{bucket}/bicing/{base}/{h:02d}/" for h in range(24)]


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
        import logging
        from apache_beam.io.gcp import gcsio
        _logger = logging.getLogger(__name__)
        gcs = gcsio.GcsIO()
        try:
            files = list(gcs.list_prefix(prefix).keys())
        except Exception:
            files = []
        if not files:
            _logger.warning("No files found at %s", prefix)
        yield from files


class ParseGCSFile(beam.DoFn):
    """Reads one GCS JSON file and emits one BQ row per station."""

    def process(self, gcs_path):
        import json
        import logging
        import sys
        from apache_beam.io.gcp import gcsio
        _logger = logging.getLogger(__name__)

        if "/template" not in sys.path:
            sys.path.insert(0, "/template")
        from main import parse_payload as _parse_payload

        gcs = gcsio.GcsIO()
        try:
            with gcs.open(gcs_path) as f:
                payload = json.load(f)
        except Exception as exc:
            _logger.error("Failed to read %s: %s", gcs_path, exc)
            return
        yield from _parse_payload(payload)


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True, help="Raw GCS bucket name (no gs:// prefix)")
    parser.add_argument("--bq_dataset", required=True)
    parser.add_argument(
        "--date",
        required=False,
        help="Date to process in America/Santiago local time e.g. 2026-05-21. Defaults to yesterday.",
    )
    known_args, pipeline_args = parser.parse_known_args(argv)

    if known_args.date:
        local_date = date.fromisoformat(known_args.date)
    else:
        local_date = (datetime.now(LOCAL_TZ) - timedelta(days=1)).date()

    prefixes = gcs_prefixes_for_date(known_args.bucket, local_date)

    options = PipelineOptions(pipeline_args)
    options.view_as(StandardOptions).runner = (
        options.view_as(StandardOptions).runner or "DataflowRunner"
    )
    project = options.view_as(GoogleCloudOptions).project
    bq_table = f"{project}:{known_args.bq_dataset}.bicing_raw"

    with beam.Pipeline(options=options) as p:
        (
            p
            | "CreatePrefixes" >> beam.Create(prefixes)
            | "ListFiles"      >> beam.ParDo(ListGCSFiles())
            | "ParseFiles"     >> beam.ParDo(ParseGCSFile())
            | "WriteToBQ"      >> WriteToBigQuery(
                bq_table,
                schema=BQ_SCHEMA,
                write_disposition=BigQueryDisposition.WRITE_APPEND,
                create_disposition=BigQueryDisposition.CREATE_NEVER,
            )
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
