# Smart Mechatronic Asset Monitoring & Edge Data Platform

An incremental mechatronics, IoT and data engineering project built
primarily with existing hardware.

## Objectives

- Control a DC geared motor through an Arduino and L298N.
- Collect environmental measurements and generate local alerts.
- Use a Raspberry Pi 4 as an edge gateway.
- Progressively build telemetry storage, data pipelines and dashboards.

## Current Status

Phase 1 - Initial Arduino tests.

USB power and board detection verified: ON LED lit, Arduino UNO
detected and selected on COM5.

Blink sketch compiled and uploaded successfully. The built-in LED
was observed blinking continuously with a programmed interval of
one second on and one second off.

Serial data exchange remains untested. Motor wiring remains
unvalidated.

## Development Environment

- Windows and PowerShell
- VS Code: main code and documentation editor
- Arduino IDE 2.3.10: Blink compilation and upload verified
- Git 2.54.0.windows.1: available
- GitHub: https://github.com/afoumalorian-cmd/smart-mechatronic-monitoring
- Current branch: feature/phase-1-arduino-tests
## Hardware Inventory
| Component | Status |
|---|---|
| KEYES Uno-compatible board / ATmega328P | USB detection, Blink upload and execution verified |
| L298N HW-095 motor driver | Visually identified; untested |
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
- [ ] Validate serial data exchange.
- [ ] Resolve motor power supply requirements.