"""Receive validated telemetry over local MQTT and save it as JSONL."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import paho.mqtt.client as mqtt

from processing.validate_telemetry import reject_constant, validate_record


TOPIC = "smart-mechatronic/machine_001/telemetry"


def consume(output_path, limit):
    """Save messages before acknowledging them; stop on any failure."""
    counts = {"received": 0, "saved": 0}
    state = {"error": None, "done": False}

    def fail(message):
        state["error"] = message
        state["done"] = True

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            fail(f"Connection rejected: {reason_code}")
            return

        result, _ = client.subscribe(TOPIC, qos=1)
        if result != mqtt.MQTT_ERR_SUCCESS:
            fail(f"Subscribe request failed: {result}")

    def on_subscribe(client, userdata, mid, reason_codes, properties):
        if len(reason_codes) != 1 or reason_codes[0].value != 1:
            fail(f"Expected a QoS 1 subscription: {reason_codes}")
            return
        print(f"Ready: subscribed to {TOPIC} at QoS 1", flush=True)

    def on_disconnect(client, userdata, flags, reason_code, properties):
        if not state["done"]:
            fail(f"Broker disconnected: {reason_code}")

    # Exclusive creation prevents overwriting an earlier reception file.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as output:

        def on_message(client, userdata, message):
            counts["received"] += 1

            try:
                if message.topic != TOPIC or message.qos != 1:
                    raise ValueError("Unexpected topic or delivery QoS.")

                record = json.loads(
                    message.payload.decode("utf-8"),
                    parse_constant=reject_constant,
                )
                category, issues = validate_record(record)
                if category != "valid":
                    raise ValueError(
                        f"Rejected record: {category}; issues={issues}"
                    )

                if record["telemetry"]["device_id"] != "machine_001":
                    raise ValueError("Device does not match the topic.")

                # Preserve record values, including the collection timestamp.
                output.write(json.dumps(record, allow_nan=False) + "\n")
                output.flush()
                os.fsync(output.fileno())
                counts["saved"] += 1

                # This acknowledges delivery to this consumer, not to the
                # original publisher. Duplicates remain possible.
                result = client.ack(message.mid, message.qos)
                if result != mqtt.MQTT_ERR_SUCCESS:
                    raise RuntimeError(f"MQTT acknowledgement failed: {result}")

                print(json.dumps(counts), flush=True)
                if limit and counts["saved"] >= limit:
                    state["done"] = True

            except Exception as exc:
                # Leave the failed message unacknowledged and stop.
                fail(f"Message processing failed: {exc}")

        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"telemetry-consumer-{uuid4().hex}",
            clean_session=True,
            protocol=mqtt.MQTTv311,
            manual_ack=True,
            reconnect_on_failure=False,
        )
        client.on_connect = on_connect
        client.on_subscribe = on_subscribe
        client.on_disconnect = on_disconnect
        client.on_message = on_message

        try:
            client.connect("127.0.0.1", 1883, keepalive=30)
            while not state["done"]:
                result = client.loop(timeout=1.0)
                if result != mqtt.MQTT_ERR_SUCCESS:
                    fail(f"MQTT network loop failed: {result}")
        except KeyboardInterrupt:
            print("Interrupted by user.", flush=True)
            fail("Consumer interrupted.")
        except Exception as exc:
            fail(f"Consumer failed: {exc}")
        finally:
            state["done"] = True
            client.disconnect()
            client.loop(timeout=0.1)

    print(json.dumps({
        "output_file": str(output_path),
        "counts": counts,
        "error": state["error"],
    }, indent=2))
    return 1 if state["error"] else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Stop after this many saved messages; 0 waits until Ctrl+C.",
    )
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit must be non-negative.")

    project_root = Path(__file__).resolve().parents[1]
    run_name = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        + "_" + uuid4().hex
    )
    output_path = (
        project_root / "data" / "mqtt" / run_name / "received.jsonl"
    )
    return consume(output_path, args.limit)


if __name__ == "__main__":
    raise SystemExit(main())