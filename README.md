# Smart Mechatronic Asset Monitoring & Edge Data Platform

An incremental mechatronics, IoT and data engineering project built
primarily with existing hardware.

## Objectives

- Control a DC geared motor through an Arduino and L298N.
- Collect environmental measurements and generate local alerts.
- Use a Raspberry Pi 4 as an edge gateway.
- Progressively build telemetry storage, data pipelines and dashboards.

## Current Status

Phase 1 - Arduino tests completed; L298N control preparation.

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
No motor or battery was connected; the motor supply terminal
marked +12V was left disconnected.

Motor operation remains untested pending a suitable motor power
supply and a multimeter.

## Development Environment

- Windows and PowerShell
- VS Code: main code and documentation editor
- Arduino IDE 2.3.10: sketch compilation, upload and Serial Monitor verified
- Git 2.54.0.windows.1: available
- GitHub: https://github.com/afoumalorian-cmd/smart-mechatronic-monitoring
- Current branch: feature/phase-1-l298n-motor-control

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

## Open Hardware Questions

- Select and validate a suitable motor power supply.
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
- [ ] Measure control signals and validate driver outputs.
- [ ] Validate motor operation with a suitable power supply.
- [ ] Resolve motor power supply requirements.