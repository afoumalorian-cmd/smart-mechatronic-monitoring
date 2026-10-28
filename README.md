# Smart Mechatronic Asset Monitoring & Edge Data Platform

An incremental mechatronics, IoT and data engineering project built
primarily with existing hardware.

## Objectives

- Control a DC geared motor through an Arduino and a motor driver.
- Collect environmental measurements and generate local alerts.
- Use a Raspberry Pi 4 as an edge gateway.
- Progressively build telemetry storage, data pipelines and dashboards.

## Current Status

Phase 1 - Arduino tests completed; first motor rotation observed
using the KEYES L298P V1 shield.

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
- T starts a timed test; S requests a stop.
- Saved sketch settings: PWM 150 and duration 5000 ms.

Motor rotation was observed during the five-second test at PWM 150.
A higher speed was observed during an additional test at PWM 250.
The previous D9 PWM assignment did not produce motor rotation;
rotation was obtained after correcting the assignment to D6.

These observations confirm basic motor actuation with this setup.
Motor voltage, current, RPM and prolonged operation remain unverified.
PWM does not regulate the motor supply to 5 V.
Sending S during motor rotation stopped the motor before the
five-second timeout.

### Additional Experimental Sketches

- servo_test: SG90 position commands on D9; movement not validated.
- button_led_buzzer_test: button on A2, LED on A1 and buzzer on A3;
  integrated operation not yet confirmed.
- l298n_control_test: updated with a three-second automatic stop
  and support for lowercase commands; this revision remains untested.

Each sketch must be uploaded separately with its matching wiring.
The servo and L298N sketches both use D9 and require different wiring.

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
| KEYES L298P V1 shield | Motor rotation observed on A1 using D6 PWM and D2 direction |
| Six-cell AA battery holder with alkaline cells | Connected to shield BAT; 9 V nominal, voltage not measured |

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