"""Publish an existing validated JSONL file to the local MQTT broker."""

import argparse
import json
import time
from pathlib import Path
from uuid import uuid4

import paho.mqtt.client as mqtt

from processing.validate_telemetry import reject_constant, validate_record


TOPIC = "smart-mechatronic/machine_001/telemetry"
TIMEOUT_SECONDS = 10.0


def load_messages(input_path):
    """Validate the entire file before publishing any messages."""
    messages = []

    with input_path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            try:
                record = json.loads(line, parse_constant=reject_constant)
                category, issues = validate_record(record)

                if category != "valid":
                    raise ValueError(
                        f"Expected valid telemetry: {category}; {issues}"
                    )

                if record["telemetry"]["device_id"] != "machine_001":
                    raise ValueError("Device does not match the topic.")

                messages.append(json.dumps(record, allow_nan=False))
            except ValueError as exc:
                raise ValueError(f"Line {line_number}: {exc}") from exc

    if not messages:
        raise ValueError("Input file contains no records.")

    return messages


def publish_file(input_path):
    """Publish sequentially and count broker acknowledgements."""
    counts = {"total": 0, "submitted": 0, "confirmed": 0}
    state = {"connected": False, "error": None, "closing": False}
    client = None
    error = None
    exit_code = 0

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            state["error"] = f"Connection rejected: {reason_code}"
        else:
            state["connected"] = True

    def on_disconnect(client, userdata, flags, reason_code, properties):
        state["connected"] = False
        if not state["closing"]:
            state["error"] = f"Broker disconnected: {reason_code}"

    def pump_until(condition, description):
        """Process network traffic without automatic reconnection."""
        deadline = time.monotonic() + TIMEOUT_SECONDS

        while True:
            if state["error"]:
                raise RuntimeError(state["error"])
            if condition():
                return
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for {description}.")

            result = client.loop(timeout=0.2)
            if result != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"MQTT network loop failed: {result}")

    try:
        # Loading is intentionally in memory for this small-file experiment.
        messages = load_messages(input_path)
        counts["total"] = len(messages)

        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"telemetry-producer-{uuid4().hex}",
            clean_session=True,
            protocol=mqtt.MQTTv311,
            reconnect_on_failure=False,
        )
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.connect("127.0.0.1", 1883, keepalive=30)

        pump_until(lambda: state["connected"], "broker connection")

        for payload in messages:
            info = client.publish(TOPIC, payload, qos=1, retain=False)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"Publish request failed: {info.rc}")

            counts["submitted"] += 1

            # QoS 1 completion confirms the broker's PUBACK.
            # It does not confirm consumer reception or file storage.
            pump_until(info.is_published, "publication PUBACK")
            counts["confirmed"] += 1
            print(json.dumps(counts), flush=True)

    except KeyboardInterrupt:
        error = "Producer interrupted; last delivery may be uncertain."
        exit_code = 130
    except Exception as exc:
        error = str(exc)
        exit_code = 1
    finally:
        state["closing"] = True
        if client is not None:
            client.disconnect()
            client.loop(timeout=0.1)

    print(json.dumps({
        "input_file": str(input_path),
        "topic": TOPIC,
        "counts": counts,
        "error": error,
    }, indent=2))
    return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, required=True,
        help="Existing validated JSONL file to publish.",
    )
    args = parser.parse_args()
    input_path = args.input.resolve()

    if not input_path.is_file():
        parser.error(f"Input file not found: {input_path}")

    return publish_file(input_path)


if __name__ == "__main__":
    raise SystemExit(main())