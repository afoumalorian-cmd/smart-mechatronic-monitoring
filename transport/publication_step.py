"""Process one RAW line and checkpoint its publication outcome."""

import base64
import copy
from pathlib import Path

from processing.pipeline_state import save_state
from transport.publication_journal import save_journal
from transport.publication_recovery import (
    restore_checkpoint,
    verify_source_identity,
)
from transport.raw_source import prefix_sha256, read_raw_line
from transport.raw_validation import classify_raw_line


def process_next(source, state, journal_path, publish, *, completed=False):
    """Process one line and return a new checkpoint, or None when waiting.

    The caller must hold the journal lock and open RAW in unbuffered
    binary mode. publish(payload) must return only after broker PUBACK
    and raise on failure or uncertain delivery.

    The input state is never modified. Any processing failure requires
    stopping this attempt and recovering from the persisted journal.
    """
    journal_path = Path(journal_path).resolve()

    if journal_path == Path(state["source_file"]).resolve():
        raise ValueError("Publication journal must not replace RAW.")

    # Reconstruct from the verified prefix for this small-data implementation.
    last_sequences = restore_checkpoint(source, state)
    start = source.tell()
    raw_line = read_raw_line(source, completed=completed)

    if raw_line is None:
        return None

    end = source.tell()
    _, category, issues = classify_raw_line(raw_line, last_sequences)

    # Verify that the line and the previous prefix still match what we read.
    source.seek(start)
    if source.read(len(raw_line)) != raw_line:
        raise ValueError("RAW line changed during processing.")

    if prefix_sha256(source, start) != state["prefix_sha256"]:
        raise ValueError("Previously processed RAW prefix changed.")

    candidate_fingerprint = prefix_sha256(source, end)
    verify_source_identity(source, state)

    if category == "valid":
        publish(raw_line)
        outcome = "broker_confirmed"
    else:
        outcome = category
        report_path = journal_path.with_name(
            journal_path.name + ".rejections"
        ) / f"{state['processed_lines'] + 1:012d}.json"

        if report_path.resolve() == Path(state["source_file"]).resolve():
            raise ValueError("Rejection report must not replace RAW.")

        # A retry replaces the same line report before advancing the cursor.
        save_state(report_path, {
            "source_file": state["source_file"],
            "source_line": state["processed_lines"] + 1,
            "start_offset": start,
            "end_offset": end,
            "outcome": outcome,
            "issues": issues,
            "raw_base64": base64.b64encode(raw_line).decode("ascii"),
        })

    # A failure here may follow a successful PUBACK. Recovery must replay.
    verify_source_identity(source, state)
    if prefix_sha256(source, end) != candidate_fingerprint:
        raise ValueError("RAW prefix changed before checkpoint save.")

    candidate = copy.deepcopy(state)
    candidate["next_offset"] = end
    candidate["processed_lines"] += 1
    candidate["prefix_sha256"] = candidate_fingerprint
    candidate["counts"][outcome] += 1

    save_journal(journal_path, candidate)
    source.seek(end)
    return candidate