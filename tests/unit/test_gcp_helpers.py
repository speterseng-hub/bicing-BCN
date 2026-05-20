from datetime import datetime, timezone

from src.utils.gcp_helpers import build_gcs_path


def test_build_gcs_path_with_timestamp():
    ts = datetime(2024, 6, 15, 8, 30, 0, tzinfo=timezone.utc)
    assert build_gcs_path(ts) == "bicing/2024/06/15/08/bicing_20240615_083000.json"


def test_build_gcs_path_without_timestamp():
    path = build_gcs_path()
    assert path.startswith("bicing/")
    assert path.endswith(".json")
