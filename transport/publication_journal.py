"""Persist and validate local MQTT publication checkpoints."""

import hashlib
import json
from pathlib import Path

from processing.pipeline_state import save_state
from processing.validate_telemetry import reject_constant


OUTCOMES = ("broker_confirmed", "sensor_error", "invalid")


def validate_journal(state):
    """Reject unsupported or inconsistent publication checkpoints."""
    if not isinstance(state, dict):
        raise ValueError("Publication journal must be an object.")

    if type(state.get("version")) is not int or state["version"] != 1:
        raise ValueError("Unsupported publication journal version.")

    source_file = state.get("source_file")
    if (
        not isinstance(source_file, str)
        or not source_file.strip()
        or not Path(source_file).is_absolute()
    ):
        raise ValueError("Journal source_file must be an absolute path.")

    identity = state.get("source_identity")
    if (
        not isinstance(identity, list)
        or len(identity) != 2
        or any(type(value) is not int or value < 0 for value in identity)
    ):
        raise ValueError("Invalid source device/inode identity.")

    for field in ("next_offset", "processed_lines"):
        value = state.get(field)
        if type(value) is not int or value < 0:
            raise ValueError(f"Invalid journal field: {field}")

    fingerprint = state.get("prefix_sha256")
    if (
        not isinstance(fingerprint, str)
        or len(fingerprint) != 64
        or any(character not in "0123456789abcdef" for character in fingerprint)
    ):
        raise ValueError("Invalid RAW prefix fingerprint.")

    counts = state.get("counts")
    if not isinstance(counts, dict) or set(counts) != set(OUTCOMES):
        raise ValueError("Invalid publication outcome counters.")

    if any(type(value) is not int or value < 0 for value in counts.values()):
        raise ValueError("Publication counters must be non-negative integers.")

    if sum(counts.values()) != state["processed_lines"]:
        raise ValueError("Publication counters do not match processed lines.")

    if state["processed_lines"] == 0:
        if (
            state["next_offset"] != 0
            or fingerprint != hashlib.sha256(b"").hexdigest()
        ):
            raise ValueError("Invalid empty-source checkpoint.")
    elif state["next_offset"] < state["processed_lines"]:
        raise ValueError("RAW offset is inconsistent with the line count.")


def new_journal(source_path, source):
    """Build an initial checkpoint from an already opened RAW file."""
    import os

    source_path = Path(source_path).resolve()
    opened = os.fstat(source.fileno())
    current = source_path.stat()

    if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
        raise ValueError("RAW path no longer identifies the opened file.")

    state = {
        "version": 1,
        "source_file": str(source_path),
        "source_identity": [opened.st_dev, opened.st_ino],
        "next_offset": 0,
        "processed_lines": 0,
        "prefix_sha256": hashlib.sha256(b"").hexdigest(),
        "counts": {outcome: 0 for outcome in OUTCOMES},
    }
    validate_journal(state)
    return state


def load_journal(journal_path):
    """Load a checkpoint without accepting nonstandard JSON constants."""
    with Path(journal_path).open("r", encoding="utf-8") as source:
        state = json.load(source, parse_constant=reject_constant)

    validate_journal(state)
    return state


def save_journal(journal_path, state):
    """Validate and atomically replace a checkpoint under the caller's lock."""
    validate_journal(state)

    if Path(journal_path).resolve() == Path(state["source_file"]).resolve():
        raise ValueError("Publication journal must not replace the RAW source.")

    save_state(journal_path, state)