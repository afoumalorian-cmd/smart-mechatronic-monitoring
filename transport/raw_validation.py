"""Classify RAW records and stop on ambiguous sequence continuity."""

import json

from processing.validate_telemetry import reject_constant, validate_record


class SequenceDiscontinuityError(ValueError):
    """Signal a repeated or decreasing counter within one device session."""


def classify_raw_line(raw_line, last_sequences):
    """Classify a complete RAW line and update usable sequence counters.

    last_sequences maps (session_id, device_id) to the last counter.
    A discontinuity raises before updating that counter.
    Invalid records still participate when their identity and counter
    are usable, matching the collector's sequence policy.
    """
    try:
        record = json.loads(raw_line, parse_constant=reject_constant)
    except (ValueError, UnicodeError) as exc:
        return None, "invalid", [f"JSON parsing failed: {exc}"]

    if isinstance(record, dict):
        session_id = record.get("session_id")
        telemetry = record.get("telemetry")

        if isinstance(telemetry, dict):
            device_id = telemetry.get("device_id")
            sequence = telemetry.get("sequence")

            if (
                isinstance(session_id, str)
                and session_id.strip()
                and isinstance(device_id, str)
                and device_id.strip()
                and type(sequence) is int
                and sequence >= 0
            ):
                key = (session_id, device_id)
                previous = last_sequences.get(key)

                if previous is not None and sequence <= previous:
                    raise SequenceDiscontinuityError(
                        f"Sequence discontinuity for {key!r}: "
                        f"previous={previous}, current={sequence}."
                    )

                last_sequences[key] = sequence

    category, issues = validate_record(record)

    if category != "invalid":
        if record["telemetry"]["device_id"] != "machine_001":
            return record, "invalid", ["Device does not match the topic."]

    return record, category, issues