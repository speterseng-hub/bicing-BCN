"""
Runs the bicing_etl pipeline locally using DirectRunner.

Reads real GCS files and writes to BigQuery — no Dataflow infrastructure needed.
Useful for validating the pipeline logic before deploying as a Flex Template.

Usage:
    python scripts/run_etl_local.py \
        --project elite-coral-496815-s5 \
        --bucket proyecto-bicing-raw \
        --bq_dataset bicing_analytics \
        --hour_utc 2026-05-21T03

To avoid writing to the real BQ table during testing, point to a test dataset:
    --bq_dataset bicing_analytics_test
"""
import sys
import os

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.etl.dataflow.bicing_etl.main import run

if __name__ == "__main__":
    # Inject DirectRunner unless the caller already passed --runner
    args = sys.argv[1:]
    if not any(a.startswith("--runner") for a in args):
        args = ["--runner=DirectRunner"] + args
    if not any(a.startswith("--temp_location") for a in args):
        args += ["--temp_location=gs://elite-coral-496815-s5-dataflow/temp"]

    run(args)