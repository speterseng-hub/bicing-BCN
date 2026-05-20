import json
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.cloud_functions.bicing_collector.main import (
    _get_feed_url,
    _fetch_feed,
    _publish,
)


DISCOVERY_RESPONSE = {
    "data": {
        "feeds": [
            {"name": "station_status", "url": "https://example.com/station_status.json"},
            {"name": "station_information", "url": "https://example.com/station_info.json"},
        ]
    }
}

STATION_STATUS_RESPONSE = {
    "last_updated": "2024-01-01T08:00:00Z",
    "data": {
        "stations": [
            {
                "station_id": "1",
                "num_bikes_available": 5,
                "num_docks_available": 10,
                "is_installed": True,
                "is_renting": True,
                "is_returning": True,
            }
        ]
    },
}


class TestGetFeedUrl:
    def test_returns_correct_url(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = DISCOVERY_RESPONSE

        with patch("requests.get", return_value=mock_resp):
            url = _get_feed_url("https://example.com/gbfs.json", "station_status")

        assert url == "https://example.com/station_status.json"

    def test_raises_when_feed_not_found(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = DISCOVERY_RESPONSE

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(ValueError, match="unknown_feed"):
                _get_feed_url("https://example.com/gbfs.json", "unknown_feed")


class TestFetchFeed:
    def test_returns_parsed_json(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = STATION_STATUS_RESPONSE

        with patch("requests.get", return_value=mock_resp):
            result = _fetch_feed("https://example.com/station_status.json")

        assert result == STATION_STATUS_RESPONSE
        mock_resp.raise_for_status.assert_called_once()


class TestPublish:
    def test_publishes_and_returns_message_id(self):
        mock_publisher = MagicMock()
        mock_future = MagicMock()
        mock_future.result.return_value = "msg-123"
        mock_publisher.publish.return_value = mock_future

        payload = {"collected_at": "2024-01-01T08:00:00+00:00", "data": {}}
        result = _publish(mock_publisher, "projects/p/topics/t", payload)

        assert result == "msg-123"
        call_args = mock_publisher.publish.call_args
        assert call_args[0][0] == "projects/p/topics/t"
        sent_data = json.loads(call_args[1]["data"])
        assert sent_data["collected_at"] == payload["collected_at"]
