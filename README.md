# Smart Mechatronic Asset Monitoring & Edge Data Platform

An incremental mechatronics, IoT and data engineering project built
primarily with existing hardware.

## Objectives

- Control a DC geared motor through an Arduino and L298N.
- Collect environmental measurements and generate local alerts.
- Use a Raspberry Pi 4 as an edge gateway.
- Progressively build telemetry storage, data pipelines and dashboards.

## Current Status

Phase 0 — Hardware inventory and development environment preparation.

No hardware tests or motor wiring have been validated yet.

## Development Environment

- Windows and PowerShell
- VS Code: main code and documentation editor
- Arduino IDE 2.3.10: installed and opened
- Git 2.54.0.windows.1: available
- GitHub: https://github.com/afoumalorian-cmd/smart-mechatronic-monitoring
- Current branch: chore/phase-0-project-setup
## Hardware Inventory

| Component | Status |
|---|---|
| KEYES Uno-compatible board / ATmega328P | Visually identified; untested |
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
- [ ] Validate Arduino USB communication.
- [ ] Resolve motor power supply requirements.