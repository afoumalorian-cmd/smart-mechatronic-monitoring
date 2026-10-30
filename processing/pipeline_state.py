"""Track local pipeline executions without modifying source files."""

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4


def file_sha256(input_path):
    """Compute a file fingerprint while keeping memory usage bounded."""
    digest = hashlib.sha256()

    with Path(input_path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def save_state(state_path, state):
    """Replace a state file atomically using a sibling temporary file."""
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = state_path.with_name(
        f".{state_path.name}.{uuid4().hex}.tmp"
    )

    try:
        with temporary_path.open("x", encoding="utf-8") as output:
            json.dump(state, output, indent=2, allow_nan=False)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())

        os.replace(temporary_path, state_path)

    finally:
        temporary_path.unlink(missing_ok=True)


def load_state(state_path):
    """Read a pipeline execution journal and check its required fields."""
    with Path(state_path).open("r", encoding="utf-8") as source:
        state = json.load(source)

    if not isinstance(state, dict):
        raise ValueError("Pipeline state must be a JSON object.")

    for field in ("run_id", "source_file", "database", "source_sha256"):
        value = state.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing or invalid state field: {field}")

    if state.get("status") not in {
        "started", "validated", "failed", "interrupted"
    }:
        raise ValueError("Only unfinished or failed runs can be resumed.")

    return state