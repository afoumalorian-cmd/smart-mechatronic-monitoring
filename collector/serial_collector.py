"""Collect Arduino JSON telemetry and add UTC reception timestamps.

Read newline-delimited JSON objects from a serial port.
Wrap each object with a reception timestamp and a session identifier,
then save one record per line in a local JSONL file.

Example:
    python collector/serial_collector.py --port COM5 --baud 9600
"""

import argparse  # Read command-line options such as --port and --baud.
import json  # Convert JSON text to Python objects and back.
import sys  # Send error messages to the standard error stream.
import uuid  # Generate a unique identifier for each collection session.
from datetime import datetime, timezone  # Create timezone-aware UTC timestamps.
from pathlib import Path  # Build filesystem paths independently of the OS.

import serial  # Provided by the pyserial package; communicates with Arduino.


def main():
    # Build the command-line interface.
    # __doc__ contains the module docstring displayed above.
    parser = argparse.ArgumentParser(description=__doc__)

    # Use COM5 unless the caller supplies another port.
    parser.add_argument("--port", default="COM5")

    # The baud rate must match Serial.begin(9600) in the Arduino sketch.
    # type=int converts the command-line text to an integer.
    parser.add_argument("--baud", type=int, default=9600)

    args = parser.parse_args()

    # Identify this execution of the collector.
    # All records collected during this execution share the same session ID.
    session_id = uuid.uuid4().hex

    # Record the session start time in UTC.
    # This timestamp is used in the output filename.
    started_at = datetime.now(timezone.utc)

    # Locate the project root using this script's location:
    # project_root/collector/serial_collector.py
    #
    # resolve() returns an absolute path.
    # parents[0] is the collector directory.
    # parents[1] is the project root.
    #
    # This avoids depending on the terminal's current directory.
    project_root = Path(__file__).resolve().parents[1]

    # Store received telemetry in the project's local data/raw directory.
    output_dir = project_root / "data" / "raw"

    # Create missing parent directories.
    # exist_ok=True allows the directory to exist already.
    output_dir.mkdir(parents=True, exist_ok=True)

    # Give each session its own file.
    # Example date component: 20261029T142908.
    #
    # JSONL means "JSON Lines": each line is a separate JSON object.
    # The UUID helps prevent filename collisions between sessions.
    output_path = output_dir / (
        f"telemetry_{started_at:%Y%m%dT%H%M%S}_{session_id}.jsonl"
    )

    # Count records successfully written and flushed during this session.
    saved_count = 0

    try:
        # Open the serial port.
        #
        # timeout=1 limits how long a read waits for incoming data.
        # It does not set the sensor's measurement interval.
        #
        # The context manager closes the port when this block exits,
        # including when an exception or Ctrl+C interrupts collection.
        #
        # Opening the port may reset an Arduino Uno.
        with serial.Serial(args.port, args.baud, timeout=1) as connection:

            # Open a new UTF-8 text file.
            #
            # Mode "x" creates a file exclusively and fails if it exists,
            # preventing accidental replacement of an earlier recording.
            #
            # This context manager also closes the file automatically.
            with output_path.open("x", encoding="utf-8") as output:
                print(f"Reading {args.port} at {args.baud} baud.")
                print(f"Saving to {output_path}")
                print("Press Ctrl+C to stop.")

                # Serial communication delivers bytes.
                # A timeout can occur before a complete line arrives.
                # Keep incomplete data here until its newline is received.
                pending = bytearray()

                # Keep collecting until Ctrl+C or a collection error.
                while True:

                    # Read bytes until a newline arrives or the read times out.
                    # b"\n" is a newline represented as bytes, not text.
                    chunk = connection.read_until(b"\n")

                    # An empty result means no bytes arrived before timeout.
                    # Wait for data by starting the next iteration.
                    if not chunk:
                        continue

                    # Append new bytes to any previously received fragment.
                    pending.extend(chunk)

                    # Discard an accumulated fragment larger than 4096 bytes.
                    # Our expected Arduino JSON messages are much shorter.
                    #
                    # This check runs after read_until() returns; it is not
                    # a strict size limit on that individual read operation.
                    if len(pending) > 4096:
                        pending.clear()
                        print("Skipped oversized line.", file=sys.stderr)
                        continue

                    # If the line is incomplete, retain it for the next read.
                    if not pending.endswith(b"\n"):
                        continue

                    # Copy the completed line, then clear the buffer so that
                    # it can receive the next Arduino message.
                    raw_line = bytes(pending)
                    pending.clear()

                    try:
                        # Decode bytes as UTF-8, then parse the JSON text.
                        # A JSON object becomes a Python dictionary.
                        event = json.loads(raw_line.decode("utf-8"))

                        # Accept JSON objects only.
                        # Other valid JSON values, such as lists or numbers,
                        # do not match the expected telemetry structure.
                        if not isinstance(event, dict):
                            raise ValueError("Expected a JSON object.")

                    except (UnicodeDecodeError, ValueError) as exc:
                        # Report malformed input and continue collecting.
                        # This can also skip a partial startup message.
                        print(f"Skipped invalid line: {exc}", file=sys.stderr)
                        continue

                    # Add collector metadata without changing the Arduino
                    # fields, which remain nested under "telemetry".
                    #
                    # received_at_utc is the PC's reception-processing time,
                    # not the exact time the sensor performed its reading.
                    #
                    # Sensor events with status="error" are retained too.
                    record = {
                        "received_at_utc": datetime.now(
                            timezone.utc
                        ).isoformat(),
                        "session_id": session_id,
                        "telemetry": event,
                    }

                    # Serialize the record and append a newline.
                    # allow_nan=False rejects nonstandard JSON numbers
                    # such as NaN and Infinity.
                    output.write(
                        json.dumps(record, allow_nan=False) + "\n"
                    )

                    # Flush Python's file buffer after every record.
                    # This makes data available to other readers promptly.
                    # It does not guarantee persistence through power loss.
                    output.flush()

                    saved_count += 1

                    # Display the Arduino event and the saved-record count.
                    # The file additionally contains the collector metadata.
                    print(
                        f"[{saved_count}] "
                        f"{json.dumps(event, allow_nan=False)}"
                    )

    except KeyboardInterrupt:
        # Ctrl+C stops collection normally.
        # The context managers close the file and serial port first.
        print(f"\nStopped. Saved {saved_count} records.")

    except (serial.SerialException, OSError, ValueError) as exc:
        # Examples:
        # - COM5 is already open in Arduino Serial Monitor.
        # - The serial device disconnects.
        # - The file cannot be created or written.
        # - Serialization encounters a nonstandard numeric value.
        #
        # These errors stop collection and return a failure exit code.
        print(f"Collection failed: {exc}", file=sys.stderr)
        return 1

    # Return a success exit code after a normal Ctrl+C stop.
    return 0


# Run main() only when this file is executed directly.
# Importing it from another Python module does not start collection.
#
# SystemExit passes main()'s return value to the operating system:
# 0 = success, 1 = failure.
if __name__ == "__main__":
    raise SystemExit(main())