"""Persist one MQTT reception and its processing outcome atomically."""

import json
from datetime import datetime, timezone
from uuid import uuid4

from processing.measurement_record import measurement_parts
from processing.validate_telemetry import reject_constant, validate_record


TOPIC = "smart-mechatronic/machine_001/telemetry"


def store_message(connection, consumer_run_id, message):
    """Commit one receipt and return its outcome without acknowledging MQTT."""
    if connection.in_transaction:
        raise ValueError("Message storage requires no active transaction.")

    receipt_id = uuid4().hex
    received_at = datetime.now(timezone.utc).isoformat()
    payload = bytes(message.payload)
    record = None
    details = []
    outcome = "invalid"
    measurement_id = None

    try:
        if message.topic != TOPIC or message.qos != 1:
            raise ValueError("Unexpected topic or delivery QoS.")

        record = json.loads(
            payload.decode("utf-8"),
            parse_constant=reject_constant,
        )
        category, issues = validate_record(record)
        details = list(issues)
        outcome = category

        if category != "invalid":
            if record["telemetry"]["device_id"] != "machine_001":
                outcome = "invalid"
                details.append("Device does not match the topic.")

    except (ValueError, UnicodeError) as exc:
        outcome = "invalid"
        details = [str(exc)]

    # Acquire the write lock before comparing and inserting measurements.
    # A concurrent writer cannot insert the same key between these steps.
    with connection:
        connection.execute("BEGIN IMMEDIATE")

        if outcome == "valid":
            key, values = measurement_parts(record)

            existing = connection.execute(
                """
                SELECT measurement_id, received_at_utc, uptime_ms,
                       sensor, status, temperature_c, humidity_pct
                FROM measurements
                WHERE session_id = ? AND device_id = ? AND sequence = ?
                """,
                key,
            ).fetchone()

            if existing is None:
                cursor = connection.execute(
                    """
                    INSERT INTO measurements (
                        import_id, source_line,
                        session_id, device_id, sequence,
                        received_at_utc, uptime_ms, sensor, status,
                        temperature_c, humidity_pct
                    )
                    VALUES (NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (*key, *values),
                )
                measurement_id = cursor.lastrowid
                outcome = "inserted"

            else:
                measurement_id = existing[0]
                if tuple(existing[1:]) == values:
                    outcome = "duplicate"
                else:
                    outcome = "conflict"
                    details = [
                        f"Conflicting measurement for key {key!r}."
                    ]

        connection.execute(
            """
            INSERT INTO mqtt_receipts (
                receipt_id, consumer_run_id, mqtt_received_at_utc,
                topic, qos, mqtt_mid, mqtt_dup, mqtt_retain,
                payload, outcome, details_json, measurement_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt_id,
                consumer_run_id,
                received_at,
                message.topic,
                message.qos,
                message.mid,
                int(message.dup),
                int(message.retain),
                payload,
                outcome,
                json.dumps(details, allow_nan=False),
                measurement_id,
            ),
        )

    # The transaction has committed before this result becomes available.
    return {
        "receipt_id": receipt_id,
        "outcome": outcome,
        "measurement_id": measurement_id,
        "details": details,
    }