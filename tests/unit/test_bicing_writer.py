from src.ingestion.cloud_functions.bicing_writer.main import _build_gcs_path


class TestBuildGcsPath:
    def test_uses_collected_at_timestamp_in_santiago_time(self):
        # 2024-06-15T08:30:00 UTC = 2024-06-15T04:30:00 America/Santiago (UTC-4, winter)
        path = _build_gcs_path("2024-06-15T08:30:00+00:00")
        assert path == "bicing/2024/06/15/04/bicing_20240615_043000.json"

    def test_falls_back_to_now_on_invalid_timestamp(self):
        path = _build_gcs_path("not-a-date")
        assert path.startswith("bicing/")
        assert path.endswith(".json")

    def test_falls_back_to_now_when_none(self):
        path = _build_gcs_path(None)
        assert path.startswith("bicing/")
        assert path.endswith(".json")

    def test_path_structure(self):
        path = _build_gcs_path("2024-01-01T00:00:00+00:00")
        parts = path.split("/")
        assert parts[0] == "bicing"
        assert len(parts) == 6   # bicing/YYYY/MM/DD/HH/filename
        assert parts[5].startswith("bicing_")
