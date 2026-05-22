from datetime import datetime, timezone


def build_gcs_path(timestamp: datetime | None = None) -> str:
    """Return GCS object path for a given UTC timestamp."""
    ts = timestamp or datetime.now(timezone.utc)
    return (
        f"bicing/{ts.strftime('%Y/%m/%d/%H')}/"
        f"bicing_{ts.strftime('%Y%m%d_%H%M%S')}.json"
    )
