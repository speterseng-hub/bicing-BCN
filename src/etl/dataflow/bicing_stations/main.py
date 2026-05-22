"""Dataflow Flex Template: fetches GBFS station_information and loads into BigQuery bicing_stations."""
import argparse
import json
import logging

import apache_beam as beam
import requests
from apache_beam.io.gcp.bigquery import WriteToBigQuery, BigQueryDisposition
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions

logger = logging.getLogger(__name__)

GBFS_DISCOVERY_URL = "https://santiago.publicbikesystem.net/customer/gbfs/v3.0/gbfs.json"
REQUEST_TIMEOUT = 10

BQ_SCHEMA = {
    "fields": [
        {"name": "station_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "name", "type": "STRING", "mode": "NULLABLE"},
        {"name": "address", "type": "STRING", "mode": "NULLABLE"},
        {"name": "lat", "type": "FLOAT", "mode": "NULLABLE"},
        {"name": "lon", "type": "FLOAT", "mode": "NULLABLE"},
        {"name": "capacity", "type": "INTEGER", "mode": "NULLABLE"},
        {"name": "post_code", "type": "STRING", "mode": "NULLABLE"},
        {"name": "district", "type": "STRING", "mode": "NULLABLE"},
        {"name": "neighborhood", "type": "STRING", "mode": "NULLABLE"},
    ]
}


def _fetch_stations(discovery_url: str) -> list[dict]:
    resp = requests.get(discovery_url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    feeds = resp.json()["data"]["feeds"]
    info_url = next(f["url"] for f in feeds if f["name"] == "station_information")
    resp = requests.get(info_url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()["data"]["stations"]


class FetchStations(beam.DoFn):
    def __init__(self, discovery_url: str):
        self._discovery_url = discovery_url

    def process(self, _):
        try:
            stations = _fetch_stations(self._discovery_url)
        except Exception as exc:
            logger.error("Failed to fetch station_information: %s", exc)
            return

        for s in stations:
            yield {
                "station_id": str(s["station_id"]),
                "name": s.get("name"),
                "address": s.get("address"),
                "lat": s.get("lat"),
                "lon": s.get("lon"),
                "capacity": s.get("capacity"),
                "post_code": s.get("post_code"),
                "district": s.get("district"),
                "neighborhood": s.get("neighborhood"),
            }


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--bq_dataset", required=True)
    parser.add_argument("--discovery_url", default=GBFS_DISCOVERY_URL)
    known_args, pipeline_args = parser.parse_known_args(argv)

    bq_table = f"{known_args.project}:{known_args.bq_dataset}.bicing_stations"

    options = PipelineOptions(pipeline_args)
    options.view_as(StandardOptions).runner = options.view_as(StandardOptions).runner or "DataflowRunner"

    with beam.Pipeline(options=options) as p:
        (
            p
            | "Start" >> beam.Create([None])
            | "FetchStations" >> beam.ParDo(FetchStations(known_args.discovery_url))
            | "WriteToBQ" >> WriteToBigQuery(
                bq_table,
                schema=BQ_SCHEMA,
                write_disposition=BigQueryDisposition.WRITE_TRUNCATE,
                create_disposition=BigQueryDisposition.CREATE_NEVER,
            )
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()