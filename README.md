# Smart Mechatronic Asset Monitoring & Edge Data Platform

An incremental mechatronics, IoT and data engineering project built
primarily with existing hardware.

## Objectives

- Control a DC geared motor through an Arduino and a motor driver.
- Collect environmental measurements and generate local alerts.
- Use a Raspberry Pi 4 as an edge gateway.
- Progressively build telemetry storage, data pipelines and dashboards.

## Current Status

Phase 6 - Local MQTT transport: an existing validated telemetry file
was published through Mosquitto on Raspberry Pi and saved by a Python
consumer.

The 55-record test confirmed matching source and received JSON content
and order, with no duplicate measurement keys in that execution.
Consumer disconnection detection was verified by stopping the broker.

The Phase 5 validation and SQLite pipeline remains available separately.
Collection and MQTT publication remain manual, separate operations.
Automatic startup and serial reconnection are not implemented.

Motor control and DHT22 acquisition results from previous phases are preserved.

USB power and board detection verified: ON LED lit, Arduino UNO
detected and selected on COM5.

Blink sketch compiled and uploaded successfully. The built-in LED
was observed blinking continuously with a programmed interval of
one second on and one second off.

Serial communication verified at 9600 baud:
- Arduino-to-PC periodic counter received in Serial Monitor.
- PC-to-Arduino commands: 1 turns the built-in LED on;
  0 turns it off, with LED ON / LED OFF acknowledgements.

### L298N Control Preparation

Connections assembled:
- Arduino 5V to L298N +5V logic supply.
- Arduino GND to L298N GND.
- Arduino D8 to L298N IN1.
- Arduino D9 to L298N IN2.
- Onboard 5V regulator jumper removed; ENA and ENB jumpers retained.

Arduino and driver power LEDs were observed lit with USB connected.
The l298n_control_test sketch was uploaded, and serial commands
F, R and S returned the expected FORWARD, REVERSE and STOP messages
at 9600 baud.

These responses verify command handling in the Arduino program.
Control-pin voltages and driver outputs have not been measured.
A motor was connected to OUT1 and OUT2 while power was disconnected,
but no powered motor test was completed with this separate module.

### KEYES L298P V1 Shield Motor Test

The separate L298N module was replaced for testing by the
KEYES L298P V1 shield stacked on the Arduino Uno.

Test configuration:
- One yellow geared motor connected to motor socket A1.
- Six 1.5 V AA alkaline cells connected to BAT: 9 V nominal.
- Channel A: D6 for PWM and D2 for direction.
- Channel B disabled.
- Serial Monitor configured at 9600 baud.
- F or T starts a forward timed test; R starts a reverse timed test.
- S requests a stop.
- Motion commands received during an active test are ignored.
- Initial PWM: 150; timed test duration: 5000 ms.
- Commands 1, 2 and 3 select PWM 100, 125 and 150 respectively.
- PWM can be changed during rotation without restarting the timeout.
- A one-second restart delay is enforced after stopping.

Motor rotation was observed during the five-second test at PWM 150.
A higher speed was observed during an additional test at PWM 250.
The previous D9 PWM assignment did not produce motor rotation;
rotation was obtained after correcting the assignment to D6.

These observations confirm basic motor actuation with this setup.
Motor voltage, current, RPM and prolonged operation remain unverified.
PWM does not regulate the motor supply to 5 V.
Sending S during motor rotation stopped the motor before the
five-second timeout.

Forward and reverse motor rotation were observed using F and R.
The stop command and five-second automatic stop were also verified
with this updated sketch. The motor was allowed to stop completely
before changing direction.

### Additional Experimental Sketches

- servo_test: SG90 position commands on D9; movement not validated.
- button_led_buzzer_test: button on A2, LED on A1 and buzzer on A3;
  integrated operation not yet confirmed.
- l298n_control_test: updated with a three-second automatic stop
  and support for lowercase commands; this revision remains untested.

Each sketch must be uploaded separately with its matching wiring.
The servo and L298N sketches both use D9 and require different wiring.

## DHT22 Telemetry Acquisition

### Wiring and Firmware

- Three-pin DHT22 module: + to 5V, OUT to D7, - to GND.
- Motor and BAT disconnected during sensor acquisition.
- Arduino powered through USB.
- Sketch: firmware/dht22_telemetry/dht22_telemetry.ino.
- Arduino libraries: DHT sensor library by Adafruit and
  Adafruit Unified Sensor.
- One JSON object emitted every three seconds at 9600 baud.
- Fields: device_id, sequence, uptime_ms, sensor, status,
  temperature_c and humidity_pct.
- Failed sensor readings emit status="error" and null measurements.

Temperature and humidity readings were received successfully.
A response to warmer, humid air was observed; sensor accuracy
has not been independently verified.

### Python Collector

Requires Python 3.12.6 and pyserial 3.5.

Create the environment and install dependencies from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Close Arduino Serial Monitor before starting collection:

```powershell
.\.venv\Scripts\python.exe .\collector\serial_collector.py --port COM5
```

Press Ctrl+C to stop collection and close the serial port.

Each session creates a JSONL file under data/raw/.
Every record contains:
- received_at_utc: PC reception-processing time in UTC.
- session_id: identifier shared by records from this collector run.
- telemetry: the original parsed Arduino JSON object.

A completed collection produced a file containing 177 records.
The first three persisted records were inspected and contained
UTC reception timestamps, a common session ID and sensor readings.

The collector skips malformed JSON and retains sensor error events.
Telemetry field validation is performed separately after collection.
Automatic serial reconnection is not implemented yet.
Local environments and collected data are excluded from Git.

### Telemetry Validation

Run validation on the latest modified RAW telemetry file:

```powershell
.\.venv\Scripts\python.exe .\processing\validate_telemetry.py
```

The validator checks record structure, UTC reception timestamps,
required telemetry fields, status and measurement ranges.

Each run creates a directory under data/validated/ containing:

- valid.jsonl: valid measurements.
- sensor_errors.jsonl: correctly structured sensor error events.
- invalid.jsonl: rejected records with source lines and reasons.
- summary.json: validation counts and source file information.

RAW files remain unchanged.

Validation of the recorded session classified all 177 records as
valid, with no sensor error events or invalid records.
A synthetic humidity value of 120% was correctly rejected.
Sensor accuracy has not been independently verified.

## Local SQLite Storage

Validated telemetry is imported using Python's built-in sqlite3 module.
SQLite version observed in the project environment: 3.45.3.
No additional Python dependency is required.

### Import Command

Run from the project root:

```powershell
.\.venv\Scripts\python.exe .\processing\import_sqlite.py --input .\data\validated\20261029T152121_8908f98ecfdf41fc822910703e19e905\valid.jsonl
```

The default database is data/local/telemetry.sqlite3.
Use --database to select a different database path.
Local databases remain excluded from Git through the data/ rule.

### Schema and Traceability

- import_runs stores successful import execution IDs, UTC import
  timestamps, source file paths and record counts.
- measurements stores collection metadata and DHT22 measurements.
- Each measurement references the import that first inserted it
  and retains its line number in the validated source file.
- The unique key is (session_id, device_id, sequence).
- An index on (device_id, received_at_utc) supports device/time queries.

The importer reuses validate_record() from validate_telemetry.py.
Only records classified as valid are accepted.
RAW and validated source files remain unchanged.

Identical existing measurements are skipped.
An existing key with different measurement content causes a conflict.
Each file import uses one transaction: a rejected record or conflict
rolls back all measurements and the history row from that import.

The unique-key design assumes that sequence numbers do not restart
within the same collection session. Arduino restarts within an active
collector session are not automatically handled.

### Observed Results

- Syntax check completed successfully.
- First import: 177 records read, 177 inserted, 0 duplicates.
- Repeated import: 177 records read, 0 inserted, 177 duplicates.
- Read-only SQL queries confirmed 177 measurements and two import runs.
- Device: machine_001.
- Reception period: 2026-10-29T14:29:13.598852+00:00 to
  2026-10-29T14:38:02.540166+00:00.

| Measurement | Minimum | Average | Maximum |
|---|---:|---:|---:|
| Temperature (°C) | 24.4 | 24.66 | 25.0 |
| Relative humidity (%) | 43.8 | 44.46 | 47.5 |

A synthetic conflict test used a separate temporary database.
A new measurement followed by a conflicting existing key was rejected.
Counts remained unchanged at 177 measurements and one import run,
confirming rollback of the entire attempted import.
The corrected test explicitly closed its SQLite connections,
and temporary file cleanup completed successfully.

These statistics describe recorded readings.
Sensor accuracy has not been independently verified.

## Development Environment

- Windows and PowerShell
- VS Code: main code and documentation editor
- Arduino IDE 2.3.10: sketch compilation, upload and Serial Monitor verified
- Git 2.54.0.windows.1: available
- GitHub: https://github.com/afoumalorian-cmd/smart-mechatronic-monitoring
- Phase 4 branch: feature/phase-4-raspberry-pi-gateway
- Python 3.12.6 with a project-local .venv
- pyserial 3.5

## Hardware Inventory

| Component | Status |
|---|---|
| KEYES Uno-compatible board / ATmega328P | USB detection, Blink upload and execution verified |
| L298N HW-095 motor driver | Logic power LED observed; motor outputs untested |
| Yellow DC geared motors | 6 available; 5 V maximum reported by owner |
| ROBITON AGM VRLA battery | Label: 12 V, 1.3 Ah; condition unverified |
| DELTA DTM 12008 AGM VRLA battery | Label: 12 V, 0.8 Ah; condition unverified |
| Two-cell 18650 holder | Available; no cells |
| Multimeter | Not available |
| Raspberry Pi 4 and sensors | Reported available; detailed inventory pending |
| KEYES L298P V1 shield | Motor rotation observed on A1 using D6 PWM and D2 direction |
| Six-cell AA battery holder with alkaline cells | Connected to shield BAT; 9 V nominal, voltage not measured |
| DHT22 three-pin module | Temperature and humidity acquisition verified on D7 |

## Open Hardware Questions

- Validate motor voltage and current with the six-cell battery supply.
- Motor reference and current requirements remain unknown.
- The L298N does not automatically regulate motor output to 5 V.
- The 12 V batteries must not power the 5 V motors through the
  driver without an appropriate, validated power arrangement.

## Working Method

- Develop each major step on a dedicated Git branch.
- Update this README with each meaningful change.
- Record actual test results separately from planned features.
- Review git status and git diff before each commit.
- Push and merge only with the owner's explicit authorization.
- Use English for code, comments, docstrings and filenames.

## Progress

- [x] Review project scope and architecture.
- [x] Visually identify the Arduino-compatible board and motor driver.
- [x] Record available batteries and motor information.
- [x] Install and open Arduino IDE.
- [x] Verify Git availability.
- [x] Complete initial repository documentation.
- [x] Configure the GitHub remote.
- [x] Push initial documentation to GitHub.
- [x] Verify Arduino USB power and board detection (COM5).
- [x] Validate firmware upload and built-in LED blinking.
- [x] Validate serial data exchange.
- [x] Assemble L298N logic power and channel A control connections.
- [x] Verify F/R/S command handling through serial acknowledgements.
- [ ] Measure control signals and validate separate L298N module outputs.
- [x] Observe motor rotation using the KEYES L298P V1 shield.
- [x] Observe increased motor speed when PWM changes from 150 to 250.
- [ ] Measure motor supply voltage and current.
- [ ] Confirm motor ratings and validate prolonged operation.
- [x] Verify the S command stops the motor during a timed test.
- [x] Verify forward and reverse motor rotation through serial commands.
- [x] Verify serial PWM selection using presets 100, 125 and 150.
- [x] Acquire DHT22 temperature and humidity as serial JSON.
- [x] Collect telemetry with Python and add UTC reception timestamps.
- [x] Persist a collection session containing 177 JSONL records.
- [x] Validate telemetry fields and measurement ranges.
- [x] Import validated telemetry into local SQLite storage.
- [x] Preserve source-file and source-line traceability.
- [x] Verify repeated imports skip identical measurements.
- [x] Query stored measurements and calculate summary statistics.
- [x] Verify conflicting records roll back the entire import.


## Phase 4 - Raspberry Pi Edge Gateway

### Verified Environment

- Raspberry Pi 4 Model B with a 32 GB microSD.
- Raspberry Pi OS Full (64-bit), based on Debian 13 Trixie.
- System upgrade, reboot and SSH reconnection verified.
- SSH access tested from the VS Code terminal and PuTTY.
- Python 3.13.5, SQLite 3.46.1 and pyserial 3.5.
- Arduino connected through USB on /dev/ttyACM0 at 9600 baud.
- Motor and BAT disconnected during acquisition.


### Observed Results

- Collection stopped cleanly with Ctrl+C after saving 55 records.
- Two non-JSON lines were skipped at startup; their origin is unknown.
- Validation: 55 valid records, 0 sensor errors and 0 invalid records.
- SQLite import: 55 records read, 55 inserted and 0 duplicates.
- Read-only queries confirmed 55 measurements and one import run.
- Existing scripts ran on the Pi without source-code changes.

Collection, validation and import remain separate manual operations.
Graphical desktop access has not yet been verified.


### Linux Setup and Collection

Run from the project root:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m serial.tools.list_ports -v
./.venv/bin/python collector/serial_collector.py --port /dev/ttyACM0 --baud 9600
```

Press Ctrl+C to stop collection. The serial port path may change;
identify it before starting a new session.


### Linux Validation and SQLite Import

Commands used for the verified Raspberry Pi session:

```bash
./.venv/bin/python processing/validate_telemetry.py --input data/raw/telemetry_20261029T203118_b1f4f900c42e49f29a57d457ff7856b4.jsonl
./.venv/bin/python processing/import_sqlite.py --input data/validated/20261029T203752_9478d0853fdf4cbf868f8c9ce488a351/valid.jsonl
```

For subsequent sessions, replace these paths with the new RAW file
and its corresponding validated file. Source files remain unchanged.
The local database is data/local/telemetry.sqlite3.

## Phase 5 - Local Pipeline and Explicit Recovery

### Processing Flow

Stop collection before running the pipeline on a completed RAW file.

processing/run_pipeline.py orchestrates validation and SQLite import.
It reuses validate_file() and import_file() from the existing modules.
Collection remains a separate operation.

Only valid measurements are imported. Sensor errors and invalid
records remain in their separate validation outputs.
When no valid measurements exist, SQLite import is skipped.

### Execution Journals

Each attempt creates a JSON journal under data/pipeline/ containing:

- Execution ID, source path, database path and UTC timestamps.
- RAW SHA-256 fingerprint.
- Validation directory and classification counts when available.
- Import summary on success, or error details on failure.
- Previous execution reference when using --resume.

States include started, validated, completed,
completed_with_rejections, failed and interrupted.

Journal updates use a temporary file followed by atomic replacement.
Full durability through power loss has not been verified.

### Explicit Recovery

Use --input to process a RAW file or --resume to retry an unfinished
or failed execution from its journal. These options are mutually exclusive.
Use --database to override the target database, including during recovery.

Recovery verifies the RAW fingerprint and starts a new attempt.
It repeats validation and import rather than continuing at a saved line.
The previous journal remains unchanged.
Identical measurements are skipped by the SQLite importer.

Journals without a source fingerprint cannot be resumed.
Completed executions cannot be resumed through --resume.
A fresh --input execution remains possible.

### Observed Results

Windows:

- Existing RAW: 177 valid measurements imported.
- Repeated execution: 0 inserted, 177 duplicates skipped.
- Invalid database target: failure recorded with validation results.
- Recovery with corrected database: completed, 177 duplicates skipped.
- Synthetic journal fingerprint mismatch: rejected before validation.
- Mixed input: 1 valid, 1 sensor error, 1 invalid; 1 inserted;
  journal status completed_with_rejections.
- Input without valid measurements: import skipped.

Raspberry Pi:

- Existing RAW: 55 valid, 0 sensor errors, 0 invalid.
- Dedicated test database: 55 inserted, 0 duplicates.
- Journal inspected: completed, fingerprint and import summary present.
- Recovery scenarios have not been separately tested on the Pi.

### Current Limits

- No automatic discovery or skipping of previously processed RAW files.
- No automatic collection-to-processing trigger.
- No automatic startup or serial reconnection.
- MQTT transport is implemented separately in Phase 6; it is not
  integrated into the local pipeline.
- No automatic handling of Arduino sequence resets within a session.
- Ctrl+C handling exists; interruption and power-loss recovery have
  not been experimentally verified in Phase 5.
- Fingerprint checks do not lock the RAW file; collection must be stopped.
- Journals contain local absolute paths and are not portable between
  Windows and Raspberry Pi without adaptation.
- Data, databases and execution journals remain excluded from Git.

### Command Examples

Run from the project root, after stopping collection.
These examples use existing local files and dedicated test databases.

Windows / PowerShell:

```powershell
.\.venv\Scripts\python.exe processing/run_pipeline.py --input data/raw/telemetry_20261029T142908_41ea517fb95941d8a66366e44b4c5942.jsonl --database data/local/phase5_pipeline_test.sqlite3
```

Recovery example verified on Windows, using the failed execution journal
and a corrected database target:

```powershell
.\.venv\Scripts\python.exe processing/run_pipeline.py --resume data/pipeline/1b4b256ce84949c6b34e0e524cb829fd.json --database data/local/phase5_pipeline_test.sqlite3
```

Raspberry Pi / Linux:

```bash
./.venv/bin/python processing/run_pipeline.py --input data/raw/telemetry_20261029T203118_b1f4f900c42e49f29a57d457ff7856b4.jsonl --database data/local/phase5_pipeline_test.sqlite3
```

Replace RAW and journal paths with those from the intended execution.
Without --database, the target defaults to data/local/telemetry.sqlite3
for --input, or to the previous journal's database for --resume.

### Exit Codes

- 0: processing completed with no invalid records; sensor errors alone
  do not cause a nonzero exit code.
- 1: processing completed with invalid records, or a processing
  failure occurred; inspect the journal to distinguish these outcomes.
- 2: command-line argument or preflight validation error.
- 130: KeyboardInterrupt handled during the processing block.

Exit-code behavior is defined in the code; numerical exit codes were
not separately checked during the recorded Phase 5 tests.


## Phase 6 - Local MQTT Transport

### Scope and Components

The existing acquisition and SQLite pipeline remains unchanged.

Transport tested on Raspberry Pi:

Validated JSONL file -> Python producer -> Mosquitto broker ->
Python consumer -> received JSONL file.

- Broker: Mosquitto 2.0.21.
- Command-line tools: mosquitto-clients.
- Python dependency: paho-mqtt==2.1.0 on Windows and Raspberry Pi.
- Producer: transport/mqtt_producer.py.
- Consumer: transport/mqtt_consumer.py.
- Topic: smart-mechatronic/machine_001/telemetry.
- MQTT protocol: 3.1.1.
- Publication and subscription QoS: 1.
- Retained publication: disabled.

The broker was observed listening only on 127.0.0.1:1883 and
[::1]:1883. Direct MQTT access from the PC was not configured or tested.

### Producer Behavior

The producer reads and validates the entire input file before publishing.
It reuses the existing telemetry validation rules and accepts only valid
measurements for machine_001.

Each source record becomes one MQTT message. Record values, including
session_id and received_at_utc, are preserved.

Messages are published sequentially. The producer waits for each
broker PUBACK before submitting the next message.

Counters distinguish total records, submitted publications and
broker-confirmed publications.

The producer stops on an error or disconnection. The network-loop wait
for connection acknowledgement or each PUBACK is limited to 10 seconds.
Automatic reconnection and publication recovery are not implemented.

### Consumer Behavior

The consumer subscribes before publication begins and reuses the existing
validation rules. It accepts only valid machine_001 records delivered
on the expected topic at QoS 1.

Each execution creates a new file:

data/mqtt/<execution>/received.jsonl

For each accepted message, the consumer writes the JSON record,
flushes the file and calls fsync before requesting its MQTT
acknowledgement.

Counters distinguish received messages from saved records.
The consumer stops on a rejected message, processing error or
disconnection. It does not reconnect automatically or remove duplicates.

The --limit option stops reception after the requested number of saved
records. Without it, the consumer waits until interruption or failure.

### Observed Results

- Command-line help and imports checked on Windows for both modules.
- Single-record test on Raspberry Pi: one received and saved record;
  persisted JSON content matched the first source record.
- Full-file producer test: 55 total, 55 submitted, 55 broker-confirmed;
  no reported error.
- Full-file consumer test: 55 received, 55 saved; no reported error.
- File comparison: 55 records, matching JSON content and order,
  with no duplicate (session_id, device_id, sequence) keys.
- Broker stopped while the consumer was idle: consumer exited with
  "MQTT network loop failed: 7", with 0 received and 0 saved.
- Broker restarted successfully; service active and loopback-only
  listening confirmed again.

The full-file reception output was:

data/mqtt/20261030T203815_ebed22715b4b48bab28ae566e026c8a8/received.jsonl

### Acknowledgements and Limits

A producer PUBACK confirms broker acceptance of that publication.
It does not confirm consumer reception or application file storage.

The consumer requests its own delivery acknowledgement after file
synchronization. This is not an application storage confirmation
returned to the producer.

QoS 1 permits duplicate delivery. A failure after writing but before
acknowledgement can produce duplicates. Replaying a source file can
also produce duplicates.

Both clients use clean sessions and new client IDs on each execution.
Offline subscriber delivery and recovery across restarts are not
provided by these scripts. An unacknowledged message is not guaranteed
to be recovered after the consumer exits.

The disconnection test covered an idle consumer only. Interruption
during publication, producer timeout behavior, write failures, Ctrl+C
and power-loss durability were not experimentally verified in Phase 6.

The producer loads the complete file into memory; large-file behavior
has not been evaluated.

No serial-collector integration, SQLite consumer import, remote MQTT
access, PostgreSQL, dashboard or alerting was added in this phase.
Local transport data remains excluded from Git through data/.

### Verified Raspberry Pi Commands

Run from the project root in two SSH terminals.

Start the consumer first and wait for "Ready: subscribed...":

```bash
./.venv/bin/python -m transport.mqtt_consumer --limit 55
```

Then publish the existing validated file from the second terminal:

```bash
./.venv/bin/python -m transport.mqtt_producer \
  --input data/validated/20261030T001827_479746098dbb49d9b301e2b493c0851f/valid.jsonl
```

For another file, adapt the input path and consumer limit.
These scripts connect to the broker on the machine where they run.