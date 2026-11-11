"""Publish sequential QoS 1 messages to the loopback MQTT broker."""

import sys
import time
from uuid import uuid4

import paho.mqtt.client as mqtt

from transport.mqtt_storage import TOPIC


TIMEOUT_SECONDS = 10.0


class LocalPublisher:
    """Keep one local connection and wait for each publication PUBACK."""

    def __init__(self):
        self.connected = False
        self.error = None
        self.closing = False
        self.disconnected_cleanly = False

        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"raw-publisher-{uuid4().hex}",
            clean_session=True,
            protocol=mqtt.MQTTv311,
            reconnect_on_failure=False,
        )
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            self.error = f"Connection rejected: {reason_code}"
        else:
            self.connected = True

    def _on_disconnect(
        self, client, userdata, flags, reason_code, properties
    ):
        self.connected = False
        self.disconnected_cleanly = not reason_code.is_failure

        if reason_code.is_failure or not self.closing:
            self.error = f"Broker disconnected: {reason_code}"

    def _wait(self, condition, description):
        deadline = time.monotonic() + TIMEOUT_SECONDS

        while True:
            if self.error:
                raise RuntimeError(self.error)
            if condition():
                return
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for {description}.")

            result = self.client.loop(timeout=0.2)
            if result != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"MQTT network loop failed: {result}")

    def __enter__(self):
        try:
            result = self.client.connect("127.0.0.1", 1883, keepalive=30)
            if result != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"MQTT connection request failed: {result}")

            self._wait(lambda: self.connected, "broker connection")
            return self

        except BaseException:
            try:
                self.close()
            except Exception as exc:
                print(f"MQTT cleanup failed: {exc}", file=sys.stderr)
            raise

    def publish(self, payload):
        """Return after PUBACK; this does not confirm SQLite storage."""
        if not self.connected or self.closing:
            raise RuntimeError("MQTT publisher is not connected.")

        info = self.client.publish(TOPIC, payload, qos=1, retain=False)

        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Publish request failed: {info.rc}")

        self._wait(info.is_published, "publication PUBACK")

    def poll(self):
        """Maintain the connection while waiting for new RAW lines."""
        if self.error:
            raise RuntimeError(self.error)

        result = self.client.loop(timeout=0.2)
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT network loop failed: {result}")

        if self.error:
            raise RuntimeError(self.error)

    def close(self):
        """Attempt a clean local disconnect with a bounded wait."""
        self.closing = True
        result = self.client.disconnect()

        if result == mqtt.MQTT_ERR_NO_CONN:
            return
        if result != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT disconnect request failed: {result}")

        deadline = time.monotonic() + 5.0

        while not self.disconnected_cleanly:
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for MQTT shutdown.")

            result = self.client.loop(timeout=0.1)
            if self.disconnected_cleanly:
                return
            if result != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"MQTT shutdown loop failed: {result}")
            if self.error:
                raise RuntimeError(self.error)

    def __exit__(self, exc_type, exc, traceback):
        try:
            self.close()
        except Exception as shutdown_error:
            if exc_type is None:
                raise
            print(f"MQTT cleanup failed: {shutdown_error}", file=sys.stderr)

        return False