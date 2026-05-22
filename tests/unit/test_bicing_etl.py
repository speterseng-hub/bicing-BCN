from datetime import datetime, timezone, timedelta

import pytest

from src.etl.dataflow.bicing_etl.main import gcs_prefix_for_hour, parse_payload


# ── fixtures ──────────────────────────────────────────────────────────────────

def make_payload(stations: list[dict], collected_at: str = "2026-05-21T03:00:00+00:00") -> dict:
    return {
        "collected_at": collected_at,
        "feed": "station_status",
        "data": {"data": {"stations": stations}},
    }


def make_station(**overrides) -> dict:
    base = {
        "station_id": "42",
        "num_bikes_available": 5,
        "num_bikes_available_types": {"mechanical": 3, "ebike": 2},
        "num_docks_available": 10,
        "is_installed": True,
        "is_renting": True,
        "is_returning": True,
        "last_reported": 1779332400,  # 2026-05-21T03:00:00 UTC
    }
    return {**base, **overrides}


# ── gcs_prefix_for_hour ───────────────────────────────────────────────────────

class TestGcsPrefixForHour:
    def test_converts_utc_to_santiago(self):
        # 03:00 UTC = 23:00 Santiago (UTC-4 in May)
        hour_utc = datetime(2026, 5, 21, 3, 0, tzinfo=timezone.utc)
        prefix = gcs_prefix_for_hour("my-bucket", hour_utc)
        assert prefix == "gs://my-bucket/bicing/2026/05/20/23/"

    def test_midnight_utc_stays_same_day_in_santiago(self):
        # 04:00 UTC = 00:00 Santiago (UTC-4 in May)
        hour_utc = datetime(2026, 5, 21, 4, 0, tzinfo=timezone.utc)
        prefix = gcs_prefix_for_hour("my-bucket", hour_utc)
        assert prefix == "gs://my-bucket/bicing/2026/05/21/00/"

    def test_bucket_name_in_prefix(self):
        hour_utc = datetime(2026, 5, 21, 12, 0, tzinfo=timezone.utc)
        prefix = gcs_prefix_for_hour("proyecto-bicing-raw", hour_utc)
        assert prefix.startswith("gs://proyecto-bicing-raw/")


# ── parse_payload ─────────────────────────────────────────────────────────────

class TestParsePayload:
    def test_returns_one_row_per_station(self):
        payload = make_payload([make_station(station_id="1"), make_station(station_id="2")])
        rows = parse_payload(payload)
        assert len(rows) == 2

    def test_station_id_is_string(self):
        payload = make_payload([make_station(station_id=99)])
        rows = parse_payload(payload)
        assert rows[0]["station_id"] == "99"
        assert isinstance(rows[0]["station_id"], str)

    def test_collected_at_becomes_timestamp_and_ingested_at(self):
        collected_at = "2026-05-21T03:00:00+00:00"
        payload = make_payload([make_station()], collected_at=collected_at)
        rows = parse_payload(payload)
        assert rows[0]["timestamp"] == collected_at
        assert rows[0]["ingested_at"] == collected_at

    def test_last_reported_unix_converted_to_iso(self):
        payload = make_payload([make_station(last_reported=1779332400)])
        rows = parse_payload(payload)
        assert rows[0]["last_reported"] == "2026-05-21T03:00:00+00:00"

    def test_last_reported_iso_string_converted(self):
        payload = make_payload([make_station(last_reported="2026-05-21T10:26:04.209Z")])
        rows = parse_payload(payload)
        assert rows[0]["last_reported"] == "2026-05-21T10:26:04.209000+00:00"

    def test_last_reported_none_stays_none(self):
        payload = make_payload([make_station(last_reported=None)])
        rows = parse_payload(payload)
        assert rows[0]["last_reported"] is None

    def test_bike_types_dict_mapped_correctly(self):
        station = make_station(num_bikes_available_types={"mechanical": 3, "ebike": 2})
        rows = parse_payload(make_payload([station]))
        assert rows[0]["num_bikes_available_types"] == {"mechanical": 3, "ebike": 2}

    def test_bike_types_none_becomes_none(self):
        station = make_station(num_bikes_available_types=None)
        rows = parse_payload(make_payload([station]))
        assert rows[0]["num_bikes_available_types"] is None

    def test_empty_stations_list_returns_empty(self):
        payload = make_payload([])
        assert parse_payload(payload) == []

    def test_missing_collected_at_uses_fallback(self):
        payload = {"data": {"data": {"stations": [make_station()]}}}
        rows = parse_payload(payload)
        assert rows[0]["ingested_at"] is not None

    def test_boolean_fields_cast_correctly(self):
        station = make_station(is_installed=1, is_renting=0, is_returning=True)
        rows = parse_payload(make_payload([station]))
        assert rows[0]["is_installed"] is True
        assert rows[0]["is_renting"] is False
        assert rows[0]["is_returning"] is True

    def test_all_required_bq_fields_present(self):
        rows = parse_payload(make_payload([make_station()]))
        required = {
            "station_id", "timestamp", "num_bikes_available",
            "num_bikes_available_types", "num_docks_available",
            "is_installed", "is_renting", "is_returning",
            "last_reported", "ingested_at",
        }
        assert required == set(rows[0].keys())