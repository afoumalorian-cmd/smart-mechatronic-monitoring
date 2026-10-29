"""Validate a RAW telemetry file without modifying its contents."""

import argparse
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def is_number(value):
    """Accept finite numbers, excluding booleans."""
    return (
        type(value) in (int, float)
        and math.isfinite(value)
    )


def validate_record(record):
    """Return a classification and a list of validation issues."""
    issues = []

    if not isinstance(record, dict):
        return "invalid", ["Record must be a JSON object."]

    # Check metadata added by the Python collector.
    session_id = record.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        issues.append("Missing or invalid session_id.")

    timestamp = record.get("received_at_utc")
    try:
        if not isinstance(timestamp, str):
            raise ValueError("Timestamp must be a string.")

        parsed_timestamp = datetime.fromisoformat(timestamp)

        # Require an explicitly timezone-aware UTC timestamp.
        if (
            parsed_timestamp.utcoffset() is None
            or parsed_timestamp.utcoffset().total_seconds() != 0
        ):
            raise ValueError("Timestamp must use UTC.")
    except ValueError:
        issues.append("Missing or invalid UTC reception timestamp.")

    telemetry = record.get("telemetry")
    if not isinstance(telemetry, dict):
        issues.append("telemetry must be a JSON object.")
        return "invalid", issues

    # Identify the device and the currently supported sensor.
    device_id = telemetry.get("device_id")
    if not isinstance(device_id, str) or not device_id.strip():
        issues.append("Missing or invalid device_id.")

    if telemetry.get("sensor") != "dht22":
        issues.append("Unsupported sensor: expected dht22.")

    # Reject missing, negative or non-integer counters.
    # Explicit type checks prevent True/False being accepted as integers.
    for field in ("sequence", "uptime_ms"):
        value = telemetry.get(field)
        if type(value) is not int or value < 0:
            issues.append(f"{field} must be a non-negative integer.")

    status = telemetry.get("status")

    if status == "ok":
        # These are project validation bounds, not calibration checks.
        bounds = {
            "temperature_c": (-40, 80),
            "humidity_pct": (0, 100),
        }

        for field, (minimum, maximum) in bounds.items():
            value = telemetry.get(field)

            if not is_number(value):
                issues.append(f"{field} must be a finite number.")
            elif not minimum <= value <= maximum:
                issues.append(
                    f"{field} must be between {minimum} and {maximum}."
                )

    elif status == "error":
        # A correctly reported sensor failure is retained separately.
        # Both measurement fields must exist and contain JSON null.
        for field in ("temperature_c", "humidity_pct"):
            if field not in telemetry or telemetry[field] is not None:
                issues.append(f"{field} must be null for error status.")
    else:
        issues.append("status must be ok or error.")

    if issues:
        return "invalid", issues

    return ("sensor_error" if status == "error" else "valid"), []


def reject_constant(value):
    """Reject nonstandard JSON constants such as NaN and Infinity."""
    raise ValueError(f"Invalid JSON constant: {value}")


def validate_file(input_path):
    """Classify one RAW file and return its output directory and summary."""
    input_path = Path(input_path).resolve()
    project_root = Path(__file__).resolve().parents[1]

    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Each execution gets a new directory, preserving earlier results.
    run_name = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        + "_"
        + uuid4().hex
    )
    output_dir = project_root / "data" / "validated" / run_name

    counts = Counter({
        "total": 0,
        "valid": 0,
        "sensor_error": 0,
        "invalid": 0,
    })

    # Open RAW in read-only mode before creating output files.
    with input_path.open("r", encoding="utf-8") as source:
        output_dir.mkdir(parents=True, exist_ok=False)

        with (
            (output_dir / "valid.jsonl").open(
                "x", encoding="utf-8"
            ) as valid_output,
            (output_dir / "sensor_errors.jsonl").open(
                "x", encoding="utf-8"
            ) as error_output,
            (output_dir / "invalid.jsonl").open(
                "x", encoding="utf-8"
            ) as invalid_output,
        ):
            destinations = {
                "valid": valid_output,
                "sensor_error": error_output,
                "invalid": invalid_output,
            }

            for line_number, line in enumerate(source, start=1):
                counts["total"] += 1

                try:
                    record = json.loads(
                        line, parse_constant=reject_constant
                    )
                    category, issues = validate_record(record)
                except ValueError as exc:
                    record = None
                    category = "invalid"
                    issues = [f"JSON parsing failed: {exc}"]

                counts[category] += 1

                if category == "invalid":
                    # Keep the original line and its location for diagnosis.
                    result = {
                        "source_line": line_number,
                        "issues": issues,
                        "raw_line": line.rstrip("\r\n"),
                    }
                else:
                    # Preserve the original record without changing values.
                    result = record

                destinations[category].write(
                    json.dumps(result, allow_nan=False) + "\n"
                )

    # Persist a small summary next to the classified records.
    summary = {
        "source_file": str(input_path),
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts": dict(counts),
    }

    with (output_dir / "summary.json").open(
        "x", encoding="utf-8"
    ) as output:
        json.dump(summary, output, indent=2, allow_nan=False)

    return output_dir, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        help="RAW JSONL file; defaults to the latest modified RAW file.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]

    if args.input is None:
        candidates = list(
            (project_root / "data" / "raw").glob("telemetry_*.jsonl")
        )
        if not candidates:
            parser.error("No RAW telemetry file found.")

        input_path = max(candidates, key=lambda path: path.stat().st_mtime)
    else:
        input_path = args.input.resolve()

    if not input_path.is_file():
        parser.error(f"Input file not found: {input_path}")

    output_dir, summary = validate_file(input_path)

    print(json.dumps(summary, indent=2))
    print(f"Results: {output_dir}")

    # Sensor failures are separate from invalid record structure.
    return 1 if summary["counts"]["invalid"] else 0


if __name__ == "__main__":
    raise SystemExit(main())