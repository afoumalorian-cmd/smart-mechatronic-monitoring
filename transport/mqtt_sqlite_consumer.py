"""Receive local MQTT telemetry and persist it in SQLite."""

import argparse
import json
import sqlite3
from pathlib import Path
from uuid import uuid4

import paho.mqtt.client as mqtt

from processing.sqlite_schema import initialize_database
from transport.mqtt_storage import TOPIC, store_message


def consume(database_path, limit):
    """Commit each message before requesting its MQTT acknowledgement."""
    run_id = uuid4().hex
    counts = {
        "received": 0,
        "inserted": 0,
        "duplicate": 0,
        "conflict": 0,
        "sensor_error": 0,
        "invalid": 0,
        "ack_requested": 0,
    }
    state = {"error": None, "done": False}
    connection = None
    client = None

    def fail(message):
        if state["error"] is None:
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

    def on_message(client, userdata, message):
        # A network loop iteration may dispatch multiple queued messages.
        if state["done"]:
            return

        counts["received"] += 1

        try:
            result = store_message(connection, run_id, message)
            outcome = result["outcome"]
            counts[outcome] += 1
            print(json.dumps(result), flush=True)

            if outcome not in ("inserted", "duplicate"):
                fail(f"Message stored as {outcome}; stopping without ACK.")
                return

            # Storage has committed. ACK failure cannot undo that commit.
            ack_result = client.ack(message.mid, message.qos)
            if ack_result != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(
                    f"MQTT acknowledgement request failed: {ack_result}"
                )
            counts["ack_requested"] += 1

            print(json.dumps(counts), flush=True)
            processed = counts["inserted"] + counts["duplicate"]
            if limit and processed >= limit:
                state["done"] = True

        except Exception as exc:
            fail(f"Message processing failed: {exc}")

    try:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database_path)

        # Request SQLite's full synchronization policy.
        # Power-loss durability still depends on the storage and OS.
        connection.execute("PRAGMA synchronous = FULL")
        initialize_database(connection)

        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"telemetry-sqlite-{run_id}",
            clean_session=True,
            protocol=mqtt.MQTTv311,
            manual_ack=True,
            reconnect_on_failure=False,
        )
        client.on_connect = on_connect
        client.on_subscribe = on_subscribe
        client.on_disconnect = on_disconnect
        client.on_message = on_message

        client.connect("127.0.0.1", 1883, keepalive=30)

        while not state["done"]:
            result = client.loop(timeout=1.0)
            if result != mqtt.MQTT_ERR_SUCCESS:
                fail(f"MQTT network loop failed: {result}")

    except KeyboardInterrupt:
        fail("Consumer interrupted.")
    except Exception as exc:
        fail(f"Consumer failed: {exc}")
    finally:
        state["done"] = True

        # Attempt to flush pending ACKs and disconnect cleanly.
        # This does not prove that the broker received the ACKs.
        try:
            if client is not None:
                client.disconnect()
                result = client.loop(timeout=0.1)
                if result not in (
                    mqtt.MQTT_ERR_SUCCESS,
                    mqtt.MQTT_ERR_NO_CONN,
                ):
                    fail(f"MQTT shutdown loop failed: {result}")
        except Exception as exc:
            fail(f"MQTT shutdown failed: {exc}")
        finally:
            if connection is not None:
                connection.close()

    print(json.dumps({
        "database": str(database_path),
        "consumer_run_id": run_id,
        "counts": counts,
        "error": state["error"],
    }, indent=2))

    return 1 if state["error"] else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        required=True,
        help="SQLite database used for MQTT reception.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Stop after this many insertions or duplicates; 0 waits.",
    )
    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit must be non-negative.")

    return consume(args.database.resolve(), args.limit)


if __name__ == "__main__":
    raise SystemExit(main())