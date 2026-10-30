"""Prepare validated measurements for consistent SQLite comparisons."""
from datetime import datetime, timezone
def measurement_parts(record):
    """Return the unique key and comparable values of a validated record."""
    telemetry = record["telemetry"]
    key = (
        record["session_id"],
        telemetry["device_id"],
        telemetry["sequence"],
    )
    # Match the timestamp normalization used by the file importer.
    timestamp = datetime.fromisoformat(
        record["received_at_utc"]
    ).astimezone(timezone.utc).isoformat()
    # Keep this order aligned with SQLite queries and insertions.
    values = (
        timestamp,
        telemetry["uptime_ms"],
        telemetry["sensor"],
        telemetry["status"],
        telemetry["temperature_c"],
        telemetry["humidity_pct"],
    )
    return key, values
